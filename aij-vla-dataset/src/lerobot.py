"""Чтение датасетов LeRobot v3 (parquet + опциональные mp4) без зависимости от lerobot."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pyarrow.parquet as pq

from .utils import get_logger

LOGGER = get_logger(__name__)

IMAGE_PREFIX = "observation.images."
STATE_KEY = "observation.state"
ACTION_KEY = "action"


@dataclass
class CameraSpec:
    key: str            # observation.images.image
    name: str           # image
    kind: str           # "image" (в parquet) | "video" (в mp4)
    shape: tuple[int, ...] | None = None


@dataclass
class EpisodeMeta:
    source: str
    index: int
    length: int
    tasks: list[str]
    data_chunk: int
    data_file: int
    videos: dict[str, tuple[int, int, float]] = field(default_factory=dict)
    # videos[camera_key] = (chunk_index, file_index, from_timestamp)

    @property
    def uid(self) -> str:
        return f"{self.source}/ep{self.index:06d}"

    @property
    def instruction(self) -> str:
        return self.tasks[0] if self.tasks else ""


@dataclass
class EpisodeArrays:
    """Числовые ряды эпизода (без изображений)."""

    state: np.ndarray | None
    action: np.ndarray | None
    timestamp: np.ndarray | None
    frame_index: np.ndarray
    task_index: np.ndarray | None
    row_offset: int          # смещение первой строки эпизода внутри data-файла

    @property
    def length(self) -> int:
        return int(self.frame_index.shape[0])


def _to_numpy_2d(column: Any) -> np.ndarray | None:
    """Колонка pyarrow (fixed_size_list / list) -> массив (T, D)."""
    if column is None:
        return None
    values = column.to_pylist()
    if not values or values[0] is None:
        return None
    try:
        arr = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if arr.ndim == 1:
        arr = arr[:, None]
    return arr


class LeRobotSource:
    """Один корень LeRobot v3 (каталог с meta/info.json)."""

    def __init__(self, root: Path, name: str | None = None):
        self.root = Path(root).resolve()
        self.name = name or self.root.name
        info_path = self.root / "meta" / "info.json"
        if not info_path.is_file():
            raise FileNotFoundError(f"{self.root}: нет meta/info.json (ожидается LeRobot v3)")
        self.info: dict[str, Any] = json.loads(info_path.read_text(encoding="utf-8"))
        self.features: dict[str, Any] = self.info.get("features") or {}
        self.fps: float = float(self.info.get("fps") or 10.0)
        self.data_path_tpl: str = self.info.get("data_path") or (
            "data/chunk-{chunk_index:03d}/file-{file_index:03d}.parquet"
        )
        self.video_path_tpl: str | None = self.info.get("video_path")
        self.cameras: list[CameraSpec] = self._collect_cameras()
        self._tasks: dict[int, str] | None = None

    # ------------------------------------------------------------------ meta
    def _collect_cameras(self) -> list[CameraSpec]:
        cams: list[CameraSpec] = []
        for key, spec in sorted(self.features.items()):
            if not key.startswith(IMAGE_PREFIX):
                continue
            dtype = str((spec or {}).get("dtype", "image"))
            kind = "video" if dtype == "video" else "image"
            shape = tuple((spec or {}).get("shape") or ()) or None
            cams.append(CameraSpec(key=key, name=key[len(IMAGE_PREFIX) :], kind=kind, shape=shape))
        return cams

    @property
    def task_map(self) -> dict[int, str]:
        if self._tasks is None:
            self._tasks = {}
            path = self.root / "meta" / "tasks.parquet"
            if path.is_file():
                table = pq.read_table(path)
                names = table.column_names
                if "task" in names and "task_index" in names:
                    idx = table.column("task_index").to_pylist()
                    txt = table.column("task").to_pylist()
                    self._tasks = {int(i): str(t) for i, t in zip(idx, txt) if t is not None}
                elif "task" in names:
                    # task_index может лежать в индексе pandas — порядок строк = task_index
                    self._tasks = {i: str(t) for i, t in enumerate(table.column("task").to_pylist())}
        return self._tasks

    def _episode_files(self) -> list[Path]:
        meta_dir = self.root / "meta" / "episodes"
        if meta_dir.is_dir():
            return sorted(meta_dir.rglob("*.parquet"))
        single = self.root / "meta" / "episodes.parquet"
        return [single] if single.is_file() else []

    def episodes(self) -> list[EpisodeMeta]:
        """Список эпизодов в детерминированном порядке (по episode_index)."""
        out: list[EpisodeMeta] = []
        tasks_map = self.task_map
        for path in self._episode_files():
            table = pq.read_table(path)
            names = set(table.column_names)
            wanted = [
                c
                for c in table.column_names
                if c in {"episode_index", "tasks", "task", "task_index", "length",
                         "data/chunk_index", "data/file_index"}
                or c.startswith("videos/")
            ]
            table = table.select(wanted)
            rows = table.to_pylist()
            for row in rows:
                ep_index = int(row.get("episode_index", len(out)))
                length = int(row.get("length") or 0)
                tasks = row.get("tasks")
                if isinstance(tasks, str):
                    tasks = [tasks]
                if not tasks:
                    single = row.get("task")
                    if single:
                        tasks = [single]
                    elif row.get("task_index") is not None:
                        tasks = [tasks_map.get(int(row["task_index"]), "")]
                    else:
                        tasks = []
                tasks = [str(t) for t in tasks if t]
                videos: dict[str, tuple[int, int, float]] = {}
                for cam in self.cameras:
                    if cam.kind != "video":
                        continue
                    chunk = row.get(f"videos/{cam.key}/chunk_index")
                    file_idx = row.get(f"videos/{cam.key}/file_index")
                    from_ts = row.get(f"videos/{cam.key}/from_timestamp")
                    if chunk is None or file_idx is None:
                        chunk = row.get("data/chunk_index")
                        file_idx = row.get("data/file_index")
                    if chunk is None or file_idx is None:
                        continue
                    videos[cam.key] = (int(chunk), int(file_idx), float(from_ts or 0.0))
                out.append(
                    EpisodeMeta(
                        source=self.name,
                        index=ep_index,
                        length=length,
                        tasks=tasks,
                        data_chunk=int(row.get("data/chunk_index") or 0),
                        data_file=int(row.get("data/file_index") or 0),
                        videos=videos,
                    )
                )
        out.sort(key=lambda e: e.index)
        if not out:
            LOGGER.warning("%s: не найдено ни одного эпизода в meta/episodes", self.name)
        return out

    # ------------------------------------------------------------------ data
    def data_file(self, chunk: int, file_index: int) -> Path:
        rel = self.data_path_tpl.format(chunk_index=chunk, file_index=file_index)
        return self.root / rel

    def video_file(self, camera_key: str, chunk: int, file_index: int) -> Path | None:
        if not self.video_path_tpl:
            return None
        cam_name = camera_key[len(IMAGE_PREFIX) :] if camera_key.startswith(IMAGE_PREFIX) else camera_key
        for kwargs in (
            {"video_key": camera_key, "chunk_index": chunk, "file_index": file_index},
            {"video_key": cam_name, "chunk_index": chunk, "file_index": file_index},
        ):
            try:
                rel = self.video_path_tpl.format(**kwargs)
            except KeyError:
                continue
            candidate = self.root / rel
            if candidate.is_file():
                return candidate
        return None

    def load_arrays(self, episode: EpisodeMeta) -> EpisodeArrays | None:
        path = self.data_file(episode.data_chunk, episode.data_file)
        if not path.is_file():
            LOGGER.warning("%s: нет data-файла %s", self.name, path)
            return None
        table = _read_table(str(path), _numeric_columns(path))
        if table is None or table.num_rows == 0:
            return None
        cols = set(table.column_names)
        if "episode_index" in cols:
            ep_col = np.asarray(table.column("episode_index").to_pylist())
            mask = np.flatnonzero(ep_col == episode.index)
            if mask.size == 0:
                return None
            offset = int(mask[0])
            sl = slice(offset, int(mask[-1]) + 1)
        else:
            offset, sl = 0, slice(0, table.num_rows)

        def col(name: str) -> Any:
            return table.column(name)[sl] if name in cols else None

        frame_index = col("frame_index")
        frame_arr = (
            np.asarray(frame_index.to_pylist(), dtype=np.int64).reshape(-1)
            if frame_index is not None
            else np.arange(sl.stop - sl.start, dtype=np.int64)
        )
        ts = col("timestamp")
        ts_arr = np.asarray(ts.to_pylist(), dtype=np.float64).reshape(-1) if ts is not None else None
        task_idx = col("task_index")
        task_arr = (
            np.asarray(task_idx.to_pylist(), dtype=np.int64).reshape(-1) if task_idx is not None else None
        )
        return EpisodeArrays(
            state=_to_numpy_2d(col(STATE_KEY)),
            action=_to_numpy_2d(col(ACTION_KEY)),
            timestamp=ts_arr,
            frame_index=frame_arr,
            task_index=task_arr,
            row_offset=offset,
        )

    # ---------------------------------------------------------------- frames
    def read_frames(
        self,
        episode: EpisodeMeta,
        camera: CameraSpec,
        arrays: EpisodeArrays,
        indices: Sequence[int],
    ) -> dict[int, np.ndarray]:
        """Кадры эпизода по локальным индексам (0..length-1) в виде RGB uint8."""
        indices = [int(i) for i in sorted(set(int(i) for i in indices)) if 0 <= i < arrays.length]
        if not indices:
            return {}
        if camera.kind == "image":
            return self._read_frames_parquet(episode, camera, arrays, indices)
        return self._read_frames_video(episode, camera, arrays, indices)

    def _read_frames_parquet(
        self,
        episode: EpisodeMeta,
        camera: CameraSpec,
        arrays: EpisodeArrays,
        indices: Sequence[int],
    ) -> dict[int, np.ndarray]:
        path = self.data_file(episode.data_chunk, episode.data_file)
        table = _read_table(str(path), (camera.key,))
        if table is None or camera.key not in table.column_names:
            return {}
        column = table.column(camera.key)
        out: dict[int, np.ndarray] = {}
        for local in indices:
            row = arrays.row_offset + local
            if row >= len(column):
                continue
            value = column[row].as_py()
            frame = _decode_image_value(value, self.root)
            if frame is not None:
                out[local] = frame
        return out

    def _read_frames_video(
        self,
        episode: EpisodeMeta,
        camera: CameraSpec,
        arrays: EpisodeArrays,
        indices: Sequence[int],
    ) -> dict[int, np.ndarray]:
        spec = episode.videos.get(camera.key)
        if spec is None:
            return {}
        chunk, file_index, from_ts = spec
        path = self.video_file(camera.key, chunk, file_index)
        if path is None:
            return {}
        if arrays.timestamp is not None:
            rel_ts = arrays.timestamp - float(arrays.timestamp[0])
        else:
            rel_ts = arrays.frame_index.astype(np.float64) / max(self.fps, 1e-6)
        wanted = {local: float(from_ts + rel_ts[local]) for local in indices}
        return _decode_video_frames(path, wanted, fps=self.fps)


# --------------------------------------------------------------------- helpers
@lru_cache(maxsize=4)
def _numeric_columns(path: Path) -> tuple[str, ...]:
    schema = pq.ParquetFile(str(path)).schema_arrow
    return tuple(name for name in schema.names if not name.startswith(IMAGE_PREFIX))


# Кеш на файл: числовые колонки + по колонке на камеру, чтобы соседние эпизоды
# одного data-файла не перечитывали parquet.
@lru_cache(maxsize=4)
def _read_table_cached(path: str, columns: tuple[str, ...]):
    return pq.read_table(path, columns=list(columns))


def _read_table(path: str, columns: Iterable[str]):
    cols = tuple(c for c in columns)
    if not cols:
        return None
    try:
        return _read_table_cached(path, cols)
    except Exception as exc:  # noqa: BLE001 — битые файлы не должны валить прогон
        LOGGER.warning("не прочитан %s (%s)", path, exc)
        return None


def _decode_image_value(value: Any, root: Path) -> np.ndarray | None:
    """Значение image-колонки LeRobot: {bytes, path} | bytes | путь | HWC-массив."""
    from PIL import Image

    data: bytes | None = None
    if isinstance(value, dict):
        data = value.get("bytes")
        if not data and value.get("path"):
            candidate = Path(str(value["path"]))
            if not candidate.is_absolute():
                candidate = root / candidate
            if candidate.is_file():
                data = candidate.read_bytes()
    elif isinstance(value, (bytes, bytearray)):
        data = bytes(value)
    elif isinstance(value, str):
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.is_file():
            data = candidate.read_bytes()
    elif isinstance(value, list):
        arr = np.asarray(value)
        if arr.ndim == 3:
            if arr.dtype != np.uint8:
                arr = np.clip(arr * (255.0 if arr.max() <= 1.0 else 1.0), 0, 255).astype(np.uint8)
            return arr
        return None
    if not data:
        return None
    try:
        with Image.open(io.BytesIO(data)) as img:
            return np.asarray(img.convert("RGB"), dtype=np.uint8)
    except Exception:  # noqa: BLE001
        return None


def _decode_video_frames(path: Path, wanted: dict[int, float], fps: float) -> dict[int, np.ndarray]:
    """Последовательное декодирование mp4 с seek к первой нужной метке."""
    try:
        import av  # noqa: PLC0415 — опциональная зависимость
    except ImportError:
        LOGGER.warning("PyAV не установлен — видео-источники пропускаются")
        return {}

    order = sorted(wanted.items(), key=lambda kv: kv[1])
    out: dict[int, np.ndarray] = {}
    tolerance = 0.75 / max(fps, 1e-6)
    try:
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            time_base = float(stream.time_base) if stream.time_base else 1.0 / max(fps, 1e-6)
            start = max(0.0, order[0][1] - tolerance)
            container.seek(int(start / time_base), stream=stream, backward=True, any_frame=False)
            pending = list(order)
            for frame in container.decode(stream):
                if not pending:
                    break
                ts = float(frame.pts * time_base) if frame.pts is not None else None
                if ts is None:
                    continue
                while pending and ts >= pending[0][1] - tolerance:
                    local, target = pending[0]
                    if ts > target + tolerance and len(pending) > 1 and ts >= pending[1][1] - tolerance:
                        pending.pop(0)
                        continue
                    out[local] = frame.to_ndarray(format="rgb24")
                    pending.pop(0)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("не декодировано видео %s (%s)", path, exc)
    return out


def discover_lerobot_sources(root: Path, exclude: Sequence[str] = ()) -> list[Path]:
    """Каталоги с meta/info.json на глубине до 3 уровней от root."""
    root = Path(root)
    found: list[Path] = []
    if (root / "meta" / "info.json").is_file():
        found.append(root)
    else:
        for info in sorted(root.glob("*/meta/info.json")) + sorted(root.glob("*/*/meta/info.json")):
            found.append(info.parent.parent)
    return [p for p in found if not any(token and token in str(p) for token in exclude)]
