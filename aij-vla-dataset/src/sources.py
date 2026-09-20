"""Обнаружение источников данных и обработка одного эпизода до списка примеров."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .config import Config
from .frames import (
    build_frame_assets,
    detect_wrist_camera,
    order_cameras,
    select_frame_indices,
    stable_subsample,
)
from .kinematics import (
    EpisodeKinematics,
    GripperCalibration,
    StateSchema,
    analyse_episode,
    calibrate_gripper,
    infer_schema,
    raw_gripper_signal,
)
from .language import ParsedInstruction, object_mentions, parse_instruction
from .lerobot import EpisodeMeta, LeRobotSource, discover_lerobot_sources
from .records import EpisodeContext, Sample
from .tasks import run_generators
from .templates import Phrasebook
from .utils import get_logger, stable_hash
from .vision import resize_long_side, to_gray

LOGGER = get_logger(__name__)


@dataclass
class SourceSpec:
    name: str
    kind: str          # lerobot | video_folder
    path: Path
    weight: float = 1.0
    options: dict[str, Any] = field(default_factory=dict)


def resolve_sources(input_root: Path, cfg: Config) -> list[SourceSpec]:
    """Явный список из конфига или автообнаружение в --input."""
    explicit = cfg.get("input.sources") or []
    exclude = [str(x) for x in (cfg.get("input.exclude") or [])]
    specs: list[SourceSpec] = []
    if explicit:
        for item in explicit:
            path = Path(str(item["path"]))
            if not path.is_absolute():
                path = input_root / path
            specs.append(
                SourceSpec(
                    name=str(item.get("name") or path.name),
                    kind=str(item.get("type") or "lerobot"),
                    path=path,
                    weight=float(item.get("weight", 1.0)),
                    options=dict(item.get("options") or {}),
                )
            )
        return specs

    if not bool(cfg.get("input.discover", True)):
        return specs

    for root in discover_lerobot_sources(input_root, exclude=exclude):
        specs.append(SourceSpec(name=root.name, kind="lerobot", path=root))

    known = {spec.path for spec in specs}
    extensions = tuple(str(x).lower() for x in (cfg.get("input.video_extensions") or []))
    if extensions and input_root.is_dir():
        candidates = [p for p in sorted(input_root.iterdir()) if p.is_dir()] + [input_root]
        for candidate in candidates:
            if candidate in known or any(token and token in str(candidate) for token in exclude):
                continue
            if (candidate / "meta" / "info.json").is_file():
                continue
            if _has_own_videos(candidate, extensions, known):
                specs.append(SourceSpec(name=candidate.name, kind="video_folder", path=candidate))
                known.add(candidate)
    return specs


def _has_own_videos(root: Path, extensions: tuple[str, ...], known: set[Path]) -> bool:
    """Есть ли в каталоге видео, не принадлежащие уже найденному LeRobot-датасету."""
    for path in _iter_videos(root, extensions):
        if any(owner == path or owner in path.parents for owner in known):
            continue
        return True
    return False


def _iter_videos(root: Path, extensions: tuple[str, ...], limit: int | None = None) -> Iterable[Path]:
    count = 0
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path
            count += 1
            if limit is not None and count >= limit:
                return


# --------------------------------------------------------------- LeRobot
@dataclass
class SourceState:
    """Общие для источника артефакты: схема, калибровка схвата, пул инструкций."""

    schema: StateSchema
    calibration: GripperCalibration | None
    instructions: list[str]
    objects: list[str]


def prepare_lerobot_source(source: LeRobotSource, cfg: Config, sample_episodes: int = 24) -> SourceState:
    episodes = source.episodes()
    state_feature = source.features.get("observation.state") or {}
    action_feature = source.features.get("action") or {}
    state_dim = int((state_feature.get("shape") or [0])[0])
    action_dim = int((action_feature.get("shape") or [0])[0])
    from .kinematics import _names_of  # noqa: PLC0415 — вспомогательная функция модуля

    override = (cfg.get("kinematics.profiles") or {}).get(source.name) or {}
    schema = infer_schema(
        state_dim=state_dim,
        action_dim=action_dim,
        state_names=_names_of(state_feature),
        action_names=_names_of(action_feature),
        override=override,
    )

    raw_samples: list[np.ndarray] = []
    for episode in stable_subsample(episodes, sample_episodes, cfg.seed, f"{source.name}:calib"):
        arrays = source.load_arrays(episode)
        if arrays is None:
            continue
        raw = raw_gripper_signal(arrays.state, arrays.action, schema)
        if raw is not None and raw.size:
            raw_samples.append(np.asarray(raw, dtype=np.float64))
    calibration = None
    if raw_samples:
        calibration = calibrate_gripper(
            raw_samples,
            open_at_start=bool(cfg.get("kinematics.gripper.auto_calibrate", True)),
            min_frames=int(cfg.get("kinematics.gripper.min_calibration_frames", 200)),
        )
        if calibration is not None:
            LOGGER.info(
                "%s: калибровка схвата low=%.4f high=%.4f open_is_high=%s",
                source.name, calibration.low, calibration.high, calibration.open_is_high,
            )

    instructions: list[str] = []
    for text in source.task_map.values():
        if text and text not in instructions:
            instructions.append(text)
    if not instructions:
        for episode in episodes[:2000]:
            if episode.instruction and episode.instruction not in instructions:
                instructions.append(episode.instruction)
    instructions = sorted(instructions)[:512]

    objects: list[str] = []
    for text in instructions:
        for mention in object_mentions(parse_instruction(text)):
            if mention and mention not in objects:
                objects.append(mention)
    objects = sorted(objects)[:512]

    return SourceState(schema=schema, calibration=calibration, instructions=instructions, objects=objects)


def process_lerobot_episode(
    source: LeRobotSource,
    state: SourceState,
    episode: EpisodeMeta,
    cfg: Config,
    out_root: Path,
    dry_run: bool = False,
) -> list[Sample]:
    arrays = source.load_arrays(episode)
    if arrays is None or arrays.length < 3:
        return []

    kin = analyse_episode(
        arrays.state,
        arrays.action,
        state.schema,
        state.calibration,
        length=arrays.length,
        params={
            **(cfg.get("kinematics.events") or {}),
            "smooth_window": int(cfg.get("kinematics.gripper.smooth_window", 3)),
        },
    )
    indices = select_frame_indices(kin, cfg)
    if not indices:
        return []

    cameras = list(source.cameras)
    requested = cfg.get("cameras.keys", "auto")
    if isinstance(requested, list) and requested:
        wanted = {str(x) for x in requested}
        cameras = [c for c in cameras if c.key in wanted or c.name in wanted]
    order = order_cameras([c.name for c in cameras])
    cameras = sorted(cameras, key=lambda c: order.index(c.name))
    cameras = cameras[: int(cfg.get("cameras.max_per_episode", 2))]
    if not cameras:
        return []

    track_window = max(1, int(cfg.get("grounding.track_window", 2)))
    reference_indices = [max(0, i - track_window) for i in indices]

    frames_by_camera: dict[str, dict[int, np.ndarray]] = {}
    references: dict[str, dict[int, np.ndarray]] = {}
    for camera in cameras:
        decoded = source.read_frames(episode, camera, arrays, sorted(set(indices + reference_indices)))
        if not decoded:
            continue
        frames_by_camera[camera.name] = {i: decoded[i] for i in indices if i in decoded}
        references[camera.name] = {
            i: decoded[max(0, i - track_window)]
            for i in indices
            if max(0, i - track_window) in decoded and max(0, i - track_window) != i
        }
    if not frames_by_camera:
        return []

    wrist = detect_wrist_camera(
        frames_by_camera,
        enabled=bool(cfg.get("cameras.detect_wrist", True)),
        ratio_threshold=float(cfg.get("cameras.wrist_motion_ratio", 0.45)),
    )
    episode_key = f"{episode.index:06d}"
    frames_dirname = str(cfg.get("output.frames_dirname", "images"))
    rel_prefix = f"{frames_dirname}/{source.name}"
    out_dir = out_root / frames_dirname / source.name

    assets = build_frame_assets(
        frames_by_camera=frames_by_camera,
        references=references,
        wrist_camera=wrist,
        out_dir=out_dir,
        rel_prefix=rel_prefix,
        episode_key=episode_key,
        cfg=cfg,
        dry_run=dry_run,
    )
    if not assets:
        return []

    primary = next((a.camera for a in assets if not a.is_wrist), assets[0].camera)
    parsed = parse_instruction(episode.instruction)
    ctx = EpisodeContext(
        source=source.name,
        uid=episode.uid,
        instruction=episode.instruction,
        parsed=parsed,
        kin=kin,
        frames=assets,
        primary_camera=primary,
        wrist_camera=wrist,
        phrasebook=_phrasebook(cfg),
        seed=cfg.seed,
        config=cfg,
        other_instructions=[t for t in state.instructions if t != episode.instruction][:64],
        other_objects=[o for o in state.objects if o != parsed.obj_short][:64],
        fps=source.fps,
        kind="robot",
    )
    return _cap_episode(run_generators(ctx), cfg, episode.uid)


# ----------------------------------------------------------- видео-источник
def process_video_episode(
    video_path: Path,
    source_name: str,
    cfg: Config,
    out_root: Path,
    dry_run: bool = False,
) -> list[Sample]:
    """Эгоцентрическое видео: кадры + проверяемые сигналы (порядок, смещение обзора)."""
    try:
        import av  # noqa: PLC0415
    except ImportError:
        return []

    max_frames = int(cfg.get("budget.max_frames_per_episode", 12))
    long_side = int(cfg.get("output.frame_long_side", 512))
    picked: list[np.ndarray] = []
    try:
        with av.open(str(video_path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            total = stream.frames or 0
            stride = max(1, total // max(1, max_frames)) if total else 24
            for i, frame in enumerate(container.decode(stream)):
                if i % stride:
                    continue
                picked.append(resize_long_side(frame.to_ndarray(format="rgb24"), long_side))
                if len(picked) >= max_frames:
                    break
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("видео %s не прочитано (%s)", video_path, exc)
        return []
    if len(picked) < 2:
        return []

    episode_key = f"{stable_hash(video_path.name) % 10**8:08d}"
    frames_by_camera = {"ego": {i: img for i, img in enumerate(picked)}}
    frames_dirname = str(cfg.get("output.frames_dirname", "images"))
    assets = build_frame_assets(
        frames_by_camera=frames_by_camera,
        references={},
        wrist_camera="ego",
        out_dir=out_root / frames_dirname / source_name,
        rel_prefix=f"{frames_dirname}/{source_name}",
        episode_key=episode_key,
        cfg=cfg,
        dry_run=dry_run,
    )
    if len(assets) < 2:
        return []

    shifts: dict[tuple[int, int], tuple[float, float]] = {}
    for a, b in zip(assets[:-1], assets[1:]):
        img_a = picked[a.local_index]
        img_b = picked[b.local_index]
        shifts[(a.local_index, b.local_index)] = _global_shift(img_a, img_b)

    kin = EpisodeKinematics(
        length=len(picked),
        progress=np.linspace(0.0, 1.0, num=len(picked)),
        pos=None,
        speed=np.zeros(len(picked)),
        height=None,
        aperture=None,
        closed=None,
        phases=["interact"] * len(picked),
        grasp_frames=[],
        release_frames=[],
        stalls=[],
        slip_frames=[],
        has_gripper=False,
    )
    ctx = EpisodeContext(
        source=source_name,
        uid=f"{source_name}/{episode_key}",
        instruction="",
        parsed=ParsedInstruction(text=""),
        kin=kin,
        frames=assets,
        primary_camera="ego",
        wrist_camera=None,
        phrasebook=_phrasebook(cfg),
        seed=cfg.seed,
        config=cfg,
        fps=10.0,
        kind="ego",
        extra={"shifts": shifts},
    )
    return _cap_episode(run_generators(ctx), cfg, ctx.uid)


def _global_shift(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Смещение точки обзора между кадрами (фазовая корреляция)."""
    try:
        import cv2
    except ImportError:
        return (0.0, 0.0)
    if a.shape[:2] != b.shape[:2]:
        return (0.0, 0.0)
    ga = to_gray(a).astype(np.float32)
    gb = to_gray(b).astype(np.float32)
    try:
        (dx, dy), _response = cv2.phaseCorrelate(ga, gb)
    except Exception:  # noqa: BLE001
        return (0.0, 0.0)
    return (float(-dx), float(-dy))


# ------------------------------------------------------------------ прочее
def _phrasebook(cfg: Config) -> Phrasebook:
    return Phrasebook(
        seed=cfg.seed,
        mcq_min_options=int(cfg.get("language.mcq_min_options", 3)),
        mcq_max_options=int(cfg.get("language.mcq_max_options", 4)),
        answer_prefix=str(cfg.get("language.mcq_answer_prefix", "Answer: ")),
        balance_letters=bool(cfg.get("language.mcq_balance_letters", True)),
    )


def _cap_episode(samples: list[Sample], cfg: Config, uid: str) -> list[Sample]:
    """Ограничение числа примеров на эпизод с сохранением разнообразия задач."""
    limit = int(cfg.get("budget.max_samples_per_episode", 24))
    if len(samples) <= limit:
        return samples
    ordered = sorted(samples, key=lambda s: (stable_hash(cfg.seed, uid, s.task, s.user) % 10**9))
    by_task: dict[str, list[Sample]] = {}
    for sample in ordered:
        by_task.setdefault(sample.task, []).append(sample)
    out: list[Sample] = []
    round_index = 0
    while len(out) < limit:
        added = False
        for task in sorted(by_task):
            bucket = by_task[task]
            if round_index < len(bucket):
                out.append(bucket[round_index])
                added = True
                if len(out) >= limit:
                    break
        if not added:
            break
        round_index += 1
    return out
