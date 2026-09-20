"""Выбор и подготовка кадров эпизода."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .kinematics import EpisodeKinematics
from .records import FrameAsset
from .utils import stable_hash
from .vision import (
    dhash,
    frame_is_usable,
    global_motion_ratio,
    hamming,
    motion_region,
    resize_long_side,
    save_frame,
)

#: Имена, по которым камеру можно опознать как наручную без анализа кадров.
WRIST_NAME_TOKENS = ("wrist", "hand", "gripper", "ego", "eye_in_hand")


def select_frame_indices(kin: EpisodeKinematics, cfg: Any) -> list[int]:
    """Кадры-кандидаты: ключевые события + равномерная сетка."""
    length = kin.length
    head = int(cfg.get("frames.skip_head_frames", 1))
    tail = int(cfg.get("frames.skip_tail_frames", 0))
    lo, hi = head, max(head, length - 1 - tail)
    if hi <= lo:
        lo, hi = 0, max(0, length - 1)
    strategy = str(cfg.get("frames.strategy", "mixed"))
    max_frames = int(cfg.get("budget.max_frames_per_episode", 12))
    min_gap = int(cfg.get("frames.min_gap_frames", 3))

    keyframes: list[int] = []
    for g in kin.grasp_frames[:2]:
        keyframes += [g - 2, g, g + 2]
    for r in kin.release_frames[:2]:
        keyframes += [r - 2, r, r + 2]
    keyframes += list(kin.slip_frames[:2])
    for start, end in kin.stalls[:2]:
        keyframes.append((start + end) // 2)
    if kin.height is not None and kin.length > 2:
        keyframes.append(int(np.argmax(kin.height)))
    keyframes += [lo, (lo + hi) // 2, hi]

    uniform_count = max(2, max_frames if strategy != "mixed" else max(3, max_frames // 2))
    uniform = [int(round(x)) for x in np.linspace(lo, hi, num=min(uniform_count, max(2, hi - lo + 1)))]

    if strategy == "keyframes":
        pool = keyframes
    elif strategy == "uniform":
        pool = uniform
    else:
        pool = keyframes + uniform

    candidates = sorted({int(np.clip(i, lo, hi)) for i in pool})
    kept: list[int] = []
    for idx in candidates:
        if not kept or idx - kept[-1] >= min_gap:
            kept.append(idx)
    if len(kept) > max_frames:
        # Оставляем равномерно распределённое подмножество — так эпизод покрыт целиком.
        step = len(kept) / float(max_frames)
        kept = [kept[int(min(len(kept) - 1, round(i * step)))] for i in range(max_frames)]
        kept = sorted(dict.fromkeys(kept))
    return kept


def detect_wrist_camera(
    frames_by_camera: dict[str, dict[int, np.ndarray]],
    *,
    enabled: bool,
    ratio_threshold: float,
) -> str | None:
    """Наручная камера: по имени, иначе по доле глобально меняющихся пикселей."""
    for name in frames_by_camera:
        if any(token in name.lower() for token in WRIST_NAME_TOKENS):
            return name
    if not enabled or len(frames_by_camera) < 2:
        return None
    ratios: dict[str, float] = {}
    for name, frames in frames_by_camera.items():
        ordered = [frames[i] for i in sorted(frames)]
        ratios[name] = global_motion_ratio(ordered)
    if not ratios:
        return None
    best = max(ratios, key=lambda k: ratios[k])
    others = [v for k, v in ratios.items() if k != best]
    if ratios[best] >= ratio_threshold and ratios[best] > 1.8 * (max(others) if others else 0.0):
        return best
    return None


def build_frame_assets(
    *,
    frames_by_camera: dict[str, dict[int, np.ndarray]],
    references: dict[str, dict[int, np.ndarray]],
    wrist_camera: str | None,
    out_dir: Path,
    rel_prefix: str,
    episode_key: str,
    cfg: Any,
    dry_run: bool = False,
) -> list[FrameAsset]:
    """Фильтрация по качеству, дедупликация, запись на диск, локализация движения."""
    quality = cfg.section("frames").get("quality", {})
    dedup = cfg.section("frames").get("dedup", {})
    long_side = int(cfg.get("output.frame_long_side", 512))
    fmt = str(cfg.get("output.frame_format", "jpg"))
    jpeg_quality = int(cfg.get("output.frame_quality", 92))
    grounding_on = bool(cfg.get("grounding.enabled", True))
    static_only = bool(cfg.get("grounding.static_camera_only", True))

    assets: list[FrameAsset] = []
    for camera in sorted(frames_by_camera):
        hashes: list[int] = []
        for local_index in sorted(frames_by_camera[camera]):
            image = frames_by_camera[camera][local_index]
            if image is None or image.ndim != 3:
                continue
            image = resize_long_side(image, long_side)
            if bool(quality.get("enabled", True)) and not frame_is_usable(
                image,
                min_laplacian_var=float(quality.get("min_laplacian_var", 8.0)),
                min_mean_luma=float(quality.get("min_mean_luma", 10.0)),
                max_mean_luma=float(quality.get("max_mean_luma", 248.0)),
            ):
                continue
            if bool(dedup.get("enabled", True)):
                digest = dhash(image)
                if any(hamming(digest, prev) <= int(dedup.get("phash_hamming", 4)) for prev in hashes):
                    continue
                hashes.append(digest)

            name = f"{episode_key}_{camera}_{local_index:05d}.{fmt}"
            rel_path = f"{rel_prefix}/{name}" if rel_prefix else name
            abs_path = out_dir / name
            if not dry_run:
                save_frame(image, abs_path, quality=jpeg_quality)

            is_wrist = camera == wrist_camera
            region = None
            if grounding_on and not (static_only and is_wrist):
                reference = references.get(camera, {}).get(local_index)
                if reference is not None:
                    reference = resize_long_side(reference, long_side)
                    region = motion_region(
                        image,
                        reference,
                        diff_percentile=float(cfg.get("grounding.diff_percentile", 98.0)),
                        morph_kernel=int(cfg.get("grounding.morph_kernel", 5)),
                        min_area_frac=float(cfg.get("grounding.min_box_area_frac", 0.004)),
                        max_area_frac=float(cfg.get("grounding.max_box_area_frac", 0.45)),
                    )
            assets.append(
                FrameAsset(
                    local_index=local_index,
                    camera=camera,
                    is_wrist=is_wrist,
                    path=rel_path if cfg.get("output.path_mode") == "relative" else str(abs_path),
                    width=int(image.shape[1]),
                    height=int(image.shape[0]),
                    image=None,
                    motion=region,
                )
            )
    return assets


def order_cameras(names: Sequence[str]) -> list[str]:
    """Стационарная камера первой, наручная второй — чтобы обрезание по
    cameras.max_per_episode не выкинуло наручный вид у многокамерных датасетов."""
    wrist = [n for n in names if any(token in str(n).lower() for token in WRIST_NAME_TOKENS)]
    rest = [n for n in names if n not in wrist]
    return rest[:1] + wrist[:1] + rest[1:] + wrist[1:]


def stable_subsample(items: Sequence[Any], limit: int | None, seed: int, key: str) -> list[Any]:
    """Детерминированное подмножество, равномерно покрывающее исходный список."""
    if limit is None or limit <= 0 or len(items) <= limit:
        return list(items)
    offset = (stable_hash(seed, key) % 1000) / 1000.0
    step = len(items) / float(limit)
    picked = [items[int(min(len(items) - 1, (i + offset) * step))] for i in range(limit)]
    seen: set[int] = set()
    out = []
    for item in picked:
        if id(item) not in seen:
            seen.add(id(item))
            out.append(item)
    return out
