"""Загрузка и валидация конфигурации пайплайна."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from .utils import config_fingerprint

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "seed": 42,
    "input": {
        "discover": True,
        "sources": [],
        "video_extensions": [".mp4", ".webm", ".mov", ".mkv"],
        "exclude": [],
    },
    "output": {
        "path_mode": "relative",
        "frames_dirname": "images",
        "frame_format": "jpg",
        "frame_quality": 92,
        "frame_long_side": 512,
        "val_fraction": 0.02,
        "split_by": "episode",
        "shuffle": True,
        "write_meta": True,
        "prune_unused_frames": True,
    },
    "budget": {
        "max_samples": 400000,
        "max_samples_per_source": None,
        "max_episodes_per_source": None,
        "max_samples_per_episode": 24,
        "max_frames_per_episode": 12,
    },
    "frames": {
        "strategy": "mixed",
        "uniform_stride": 0,
        "min_gap_frames": 3,
        "skip_head_frames": 1,
        "skip_tail_frames": 0,
        "quality": {
            "enabled": True,
            "min_laplacian_var": 8.0,
            "min_mean_luma": 10.0,
            "max_mean_luma": 248.0,
        },
        "dedup": {"enabled": True, "phash_hamming": 4},
    },
    "cameras": {
        "keys": "auto",
        "max_per_episode": 2,
        "detect_wrist": True,
        "wrist_motion_ratio": 0.10,
    },
    "kinematics": {
        "profiles": {},
        "gripper": {
            "auto_calibrate": True,
            "smooth_window": 3,
            "min_calibration_frames": 200,
        },
        "events": {
            "velocity_eps": 0.004,
            "stall_window": 10,
            "lift_delta": 0.02,
            "slip_window": 8,
        },
    },
    "grounding": {
        "enabled": True,
        "min_confidence": 0.45,
        "min_box_area_frac": 0.004,
        "max_box_area_frac": 0.45,
        "diff_percentile": 98.0,
        "morph_kernel": 5,
        "track_window": 2,
        "static_camera_only": True,
    },
    "language": {
        "locale": "en",
        "max_share_per_template": 0.04,
        "min_template_cap": 25,
        "mcq_share": 0.4,
        "mcq_answer_prefix": "Answer: ",
        "mcq_balance_letters": True,
        "mcq_min_options": 3,
        "mcq_max_options": 4,
    },
    "tasks": {},
    "captioner": {
        "enabled": False,
        "base_url": "",
        "model": "",
        "api_token": "",
        "timeout_s": 60,
        "workers": 8,
        "max_samples": 0,
        "retries": 2,
    },
    "runtime": {
        "num_workers": 0,
        "chunk_episodes": 8,
        "log_level": "INFO",
        "progress": True,
    },
}

#: Генераторы обучающих сигналов и их веса по умолчанию.
DEFAULT_TASKS: dict[str, dict[str, Any]] = {
    "gripper_state": {"enabled": True, "weight": 0.8},
    "phase": {"enabled": True, "weight": 1.0},
    "progress": {"enabled": True, "weight": 0.9},
    "subtask": {"enabled": True, "weight": 1.2},
    "instruction_decomp": {"enabled": True, "weight": 0.5},
    "instruction_check": {"enabled": True, "weight": 0.7},
    "object_role": {"enabled": True, "weight": 0.6},
    "spatial_relation": {"enabled": True, "weight": 0.9},
    "grounding_box": {"enabled": True, "weight": 0.5},
    "grounding_point": {"enabled": True, "weight": 0.4},
    "temporal_order": {"enabled": True, "weight": 0.8},
    "progress_compare": {"enabled": True, "weight": 0.5},
    "frame_transition": {"enabled": True, "weight": 0.8},
    "multiview_match": {"enabled": True, "weight": 0.5},
    "view_role": {"enabled": True, "weight": 0.3},
    "episode_summary": {"enabled": True, "weight": 0.6},
    "failure_diagnosis": {"enabled": True, "weight": 0.7},
    "recovery_instruction": {"enabled": True, "weight": 0.6},
    "scene_caption": {"enabled": True, "weight": 0.7},
    "ego_temporal_order": {"enabled": True, "weight": 0.4},
    "ego_transition": {"enabled": True, "weight": 0.4},
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


class Config:
    """Обёртка над словарём конфига с точечным доступом и валидацией."""

    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.fingerprint = config_fingerprint(data)

    # -- доступ ------------------------------------------------------------
    def get(self, path: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def section(self, name: str) -> dict[str, Any]:
        value = self.data.get(name) or {}
        return value if isinstance(value, dict) else {}

    def task_enabled(self, name: str) -> bool:
        task = self.section("tasks").get(name) or {}
        return bool(task.get("enabled", False))

    def task_weight(self, name: str) -> float:
        task = self.section("tasks").get(name) or {}
        return float(task.get("weight", 0.0))

    @property
    def seed(self) -> int:
        return int(self.data.get("seed", 42))

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.data)

    # -- конструкторы ------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path | None, overrides: dict[str, Any] | None = None) -> "Config":
        raw: dict[str, Any] = {}
        if path is not None:
            text = Path(path).read_text(encoding="utf-8")
            loaded = yaml.safe_load(text) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"Конфиг {path} должен быть YAML-словарём")
            raw = loaded
        data = _deep_merge(DEFAULTS, raw)
        tasks = _deep_merge(DEFAULT_TASKS, raw.get("tasks") or {})
        data["tasks"] = tasks
        if overrides:
            data = _deep_merge(data, overrides)
        cfg = cls(data)
        cfg.validate()
        return cfg

    def validate(self) -> None:
        out_mode = self.get("output.path_mode")
        if out_mode not in {"relative", "absolute"}:
            raise ValueError("output.path_mode должен быть 'relative' или 'absolute'")
        if self.get("output.frame_format") not in {"jpg", "jpeg", "png"}:
            raise ValueError("output.frame_format должен быть jpg/jpeg/png")
        if self.get("frames.strategy") not in {"keyframes", "uniform", "mixed"}:
            raise ValueError("frames.strategy должен быть keyframes/uniform/mixed")
        if not 0.0 <= float(self.get("output.val_fraction", 0.0)) < 0.5:
            raise ValueError("output.val_fraction должен быть в [0, 0.5)")
        if not 0.0 <= float(self.get("language.mcq_share", 0.0)) <= 1.0:
            raise ValueError("language.mcq_share должен быть в [0, 1]")
        if int(self.get("budget.max_samples_per_episode", 1)) < 1:
            raise ValueError("budget.max_samples_per_episode должен быть >= 1")
        if not any(self.task_enabled(name) for name in self.section("tasks")):
            raise ValueError("Все генераторы выключены — датасет будет пустым")
