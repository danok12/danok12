#!/usr/bin/env python3
"""Синтетический датасет LeRobot v3 для самопроверки пайплайна.

Скриптованная траектория «подъехать → захватить → поднять → перенести →
опустить → отпустить → отъехать» с согласованными state/action и отрисованными
кадрами: стационарная камера (image) и наручная (image2). Позволяет проверить,
что кинематический разбор, локализация движения и генераторы дают осмысленный
результат, не скачивая ничего из сети.

    python tests/make_fixture.py --output /tmp/fixture --episodes 6
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

H = W = 256
TASKS = [
    ("pick up the red block and place it in the blue bowl", (210, 60, 60), (60, 90, 200)),
    ("put the green can on the wooden tray", (70, 170, 80), (150, 110, 60)),
    ("pick up the yellow cup and place it in the grey box", (225, 200, 60), (130, 130, 130)),
]
OPEN_WIDTH = 0.085          # схват раскрыт
HELD_WIDTH = 0.038          # схват сомкнут на объекте (ограничен его толщиной)
EMPTY_WIDTH = 0.012         # схват сомкнут вхолостую — захват не удался
#: Сценарии эпизодов: успешный, сорвавшийся захват и застой на подлёте.
MODES = ("success", "success", "failed_grasp", "success", "stall", "success")


def _episode_script(rng: np.random.Generator, length: int, mode: str = "success") -> dict[str, np.ndarray]:
    """Опорные точки траектории в нормированных координатах кадра."""
    start = np.array([0.15 + 0.1 * rng.random(), 0.25 + 0.1 * rng.random()])
    obj = np.array([0.35 + 0.2 * rng.random(), 0.62 + 0.1 * rng.random()])
    dst = np.array([0.70 + 0.12 * rng.random(), 0.35 + 0.15 * rng.random()])

    closed_width = EMPTY_WIDTH if mode == "failed_grasp" else HELD_WIDTH
    stall_len = int(length * 0.22) if mode == "stall" else 0

    phases = {
        "approach": int(length * 0.28) - stall_len // 2,
        "stall": stall_len,
        "grasp": int(length * 0.10),
        "lift": int(length * 0.12),
        "transport": int(length * 0.24) - stall_len // 2,
        "align": int(length * 0.10),
        "release": int(length * 0.06),
    }
    phases["retreat"] = length - sum(phases.values())

    xy: list[np.ndarray] = []
    z: list[float] = []
    width: list[float] = []

    def leg(n: int, a: np.ndarray, b: np.ndarray, za: float, zb: float, wa: float, wb: float) -> None:
        for i in range(max(0, n)):
            t = (i + 1) / max(1, n)
            xy.append(a + (b - a) * t)
            z.append(za + (zb - za) * t)
            width.append(wa + (wb - wa) * t)

    leg(phases["approach"], start, obj, 0.22, 0.05, OPEN_WIDTH, OPEN_WIDTH)
    # застой: рука зависла над объектом и не двигается
    leg(phases["stall"], obj, obj, 0.05, 0.05, OPEN_WIDTH, OPEN_WIDTH)
    leg(phases["grasp"], obj, obj, 0.05, 0.03, OPEN_WIDTH, closed_width)
    leg(phases["lift"], obj, obj, 0.03, 0.20, closed_width, closed_width)
    leg(phases["transport"], obj, dst, 0.20, 0.19, closed_width, closed_width)
    leg(phases["align"], dst, dst, 0.19, 0.05, closed_width, closed_width)
    leg(phases["release"], dst, dst, 0.05, 0.06, closed_width, OPEN_WIDTH)
    leg(phases["retreat"], dst, dst + np.array([0.05, -0.12]), 0.06, 0.24, OPEN_WIDTH, OPEN_WIDTH)

    xy_arr = np.asarray(xy[:length], dtype=np.float64)
    z_arr = np.asarray(z[:length], dtype=np.float64)
    w_arr = np.asarray(width[:length], dtype=np.float64)
    grasp_at = phases["approach"] + phases["stall"] + phases["grasp"] - 1
    release_at = length - phases["retreat"] - 1
    return {
        "xy": xy_arr,
        "z": z_arr,
        "width": w_arr,
        "grasp": grasp_at,
        "release": release_at,
        "obj": obj,
        "dst": dst,
        "mode": mode,
    }


def _render(
    gripper_xy: np.ndarray,
    gripper_z: float,
    width: float,
    obj_xy: np.ndarray,
    dst_xy: np.ndarray,
    obj_color: tuple[int, int, int],
    dst_color: tuple[int, int, int],
    wrist: bool,
) -> np.ndarray:
    canvas = np.zeros((H, W, 3), dtype=np.uint8)
    canvas[:, :] = (205, 198, 185)
    canvas[: int(H * 0.30)] = (150, 152, 158)          # задняя стенка
    canvas[int(H * 0.86) :] = (120, 104, 84)           # край стола

    def box(cx: float, cy: float, half_w: int, half_h: int, color: tuple[int, int, int]) -> None:
        x = int(cx * W)
        y = int(cy * H)
        canvas[
            max(0, y - half_h) : min(H, y + half_h),
            max(0, x - half_w) : min(W, x + half_w),
        ] = color

    box(dst_xy[0], dst_xy[1], 26, 16, dst_color)
    box(obj_xy[0], obj_xy[1], 14, 14, obj_color)
    # манипулятор: вертикальная штанга + две «губки» схвата
    x = int(gripper_xy[0] * W)
    y = int(gripper_xy[1] * H)
    canvas[max(0, y - 90) : max(0, y - 10), max(0, x - 5) : min(W, x + 5)] = (60, 60, 70)
    finger = max(3, int(width * 180))
    canvas[max(0, y - 14) : min(H, y + 10), max(0, x - finger - 4) : max(0, x - finger)] = (35, 35, 45)
    canvas[max(0, y - 14) : min(H, y + 10), min(W, x + finger) : min(W, x + finger + 4)] = (35, 35, 45)
    shade = int(np.clip(40 * gripper_z, 0, 60))
    canvas = np.clip(canvas.astype(np.int16) + shade, 0, 255).astype(np.uint8)

    if wrist:
        half = 60
        y0 = int(np.clip(y - half, 0, H - 2 * half))
        x0 = int(np.clip(x - half, 0, W - 2 * half))
        crop = canvas[y0 : y0 + 2 * half, x0 : x0 + 2 * half]
        return np.asarray(Image.fromarray(crop).resize((W, H), Image.BILINEAR), dtype=np.uint8)
    return canvas


def _png(image: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


def build(
    output: Path,
    episodes: int = 6,
    length: int = 48,
    seed: int = 0,
    video_backed: bool = False,
) -> Path:
    """Собрать фикстур. video_backed=True — кадры в mp4 (так хранятся Bridge и Fractal)."""
    output = Path(output)
    (output / "data" / "chunk-000").mkdir(parents=True, exist_ok=True)
    (output / "meta" / "episodes" / "chunk-000").mkdir(parents=True, exist_ok=True)

    video_frames: dict[str, list[np.ndarray]] = {"image": [], "image2": []}
    rows: dict[str, list] = {
        "observation.images.image": [],
        "observation.images.image2": [],
        "observation.state": [],
        "action": [],
        "timestamp": [],
        "frame_index": [],
        "episode_index": [],
        "index": [],
        "task_index": [],
    }
    episode_rows: list[dict] = []
    global_index = 0

    for episode in range(episodes):
        rng = np.random.default_rng(seed + episode)
        task_index = episode % len(TASKS)
        instruction, obj_color, dst_color = TASKS[task_index]
        mode = MODES[episode % len(MODES)]
        script = _episode_script(rng, length, mode=mode)
        obj_xy = script["obj"]
        dst_xy = script["dst"]
        grasped = False

        for t in range(length):
            xy = script["xy"][t]
            z = float(script["z"][t])
            width = float(script["width"][t])
            if t >= script["grasp"] and mode != "failed_grasp":
                grasped = True
            if t > script["release"]:
                grasped = False
            current_obj = xy.copy() if grasped else obj_xy
            if t > script["release"] and mode != "failed_grasp":
                current_obj = dst_xy.copy()
                current_obj[1] += 0.02

            third = _render(xy, z, width, current_obj, dst_xy, obj_color, dst_color, False)
            wrist = _render(xy, z, width, current_obj, dst_xy, obj_color, dst_color, True)
            if video_backed:
                video_frames["image"].append(third)
                video_frames["image2"].append(wrist)
            else:
                rows["observation.images.image"].append({"bytes": _png(third), "path": None})
                rows["observation.images.image2"].append({"bytes": _png(wrist), "path": None})
            finger = width / 2.0
            state = [float(xy[0]), float(-xy[1]), z, 0.0, 0.0, 0.0, finger, -finger]
            nxt = script["xy"][min(t + 1, length - 1)]
            action = [
                float(nxt[0] - xy[0]),
                float(-(nxt[1] - xy[1])),
                float(script["z"][min(t + 1, length - 1)] - z),
                0.0,
                0.0,
                0.0,
                1.0 if width < (OPEN_WIDTH + HELD_WIDTH) / 2 else -1.0,
            ]
            rows["observation.state"].append(state)
            rows["action"].append(action)
            rows["timestamp"].append(float(t) / 10.0)
            rows["frame_index"].append(t)
            rows["episode_index"].append(episode)
            rows["index"].append(global_index)
            rows["task_index"].append(task_index)
            global_index += 1

        episode_row = {
                "episode_index": episode,
                "tasks": [instruction],
                "length": length,
                "data/chunk_index": 0,
                "data/file_index": 0,
                "dataset_from_index": episode * length,
                "dataset_to_index": (episode + 1) * length,
                "meta/episodes/chunk_index": 0,
                "meta/episodes/file_index": 0,
        }
        if video_backed:
            for camera in ("image", "image2"):
                key = f"observation.images.{camera}"
                episode_row[f"videos/{key}/chunk_index"] = 0
                episode_row[f"videos/{key}/file_index"] = 0
                episode_row[f"videos/{key}/from_timestamp"] = episode * length / 10.0
                episode_row[f"videos/{key}/to_timestamp"] = (episode + 1) * length / 10.0
        episode_rows.append(episode_row)

    image_fields = [
        ("observation.images.image", pa.struct([("bytes", pa.binary()), ("path", pa.string())])),
        ("observation.images.image2", pa.struct([("bytes", pa.binary()), ("path", pa.string())])),
    ]
    if video_backed:
        for key in ("observation.images.image", "observation.images.image2"):
            rows.pop(key, None)
        image_fields = []
        _write_videos(output, video_frames)
    schema = pa.schema(
        [
            *image_fields,
            ("observation.state", pa.list_(pa.float32(), 8)),
            ("action", pa.list_(pa.float32(), 7)),
            ("timestamp", pa.float32()),
            ("frame_index", pa.int64()),
            ("episode_index", pa.int64()),
            ("index", pa.int64()),
            ("task_index", pa.int64()),
        ]
    )
    pq.write_table(pa.Table.from_pydict(rows, schema=schema), output / "data" / "chunk-000" / "file-000.parquet")
    pq.write_table(pa.Table.from_pylist(episode_rows), output / "meta" / "episodes" / "chunk-000" / "file-000.parquet")
    pq.write_table(
        pa.table({"task_index": list(range(len(TASKS))), "task": [t[0] for t in TASKS]}),
        output / "meta" / "tasks.parquet",
    )

    info = {
        "codebase_version": "v3.0",
        "robot_type": "panda",
        "total_episodes": episodes,
        "total_frames": episodes * length,
        "total_tasks": len(TASKS),
        "chunks_size": 1000,
        "fps": 10,
        "splits": {"train": f"0:{episodes}"},
        "data_path": "data/chunk-{chunk_index:03d}/file-{file_index:03d}.parquet",
        "video_path": (
            "videos/{video_key}/chunk-{chunk_index:03d}/file-{file_index:03d}.mp4" if video_backed else None
        ),
        "features": {
            "observation.images.image": {
                "dtype": "video" if video_backed else "image",
                "shape": [H, W, 3],
                "names": ["height", "width", "channel"],
            },
            "observation.images.image2": {
                "dtype": "video" if video_backed else "image",
                "shape": [H, W, 3],
                "names": ["height", "width", "channel"],
            },
            "observation.state": {"dtype": "float32", "shape": [8], "names": ["state"]},
            "action": {"dtype": "float32", "shape": [7], "names": ["actions"]},
            "timestamp": {"dtype": "float32", "shape": [1], "names": None},
            "frame_index": {"dtype": "int64", "shape": [1], "names": None},
            "episode_index": {"dtype": "int64", "shape": [1], "names": None},
            "index": {"dtype": "int64", "shape": [1], "names": None},
            "task_index": {"dtype": "int64", "shape": [1], "names": None},
        },
    }
    (output / "meta" / "info.json").write_text(json.dumps(info, indent=4), encoding="utf-8")
    return output


def _write_videos(output: Path, video_frames: dict[str, list[np.ndarray]], fps: int = 10) -> None:
    """Все эпизоды камеры — в один mp4, как в LeRobot v3."""
    import av

    for camera, frames in video_frames.items():
        path = output / "videos" / f"observation.images.{camera}" / "chunk-000" / "file-000.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        with av.open(str(path), "w") as container:
            stream = container.add_stream("libx264", rate=fps)
            stream.width, stream.height, stream.pix_fmt = W, H, "yuv420p"
            stream.options = {"crf": "18"}
            for frame in frames:
                for packet in stream.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=6)
    parser.add_argument("--length", type=int, default=48)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--video", action="store_true", help="кадры в mp4 вместо parquet")
    args = parser.parse_args()
    path = build(
        args.output,
        episodes=args.episodes,
        length=args.length,
        seed=args.seed,
        video_backed=args.video,
    )
    print(f"фикстур собран: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
