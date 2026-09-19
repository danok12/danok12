"""Структуры данных, которыми обмениваются чтение датасета, генераторы и writer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .kinematics import EpisodeKinematics
from .language import ParsedInstruction
from .templates import Phrasebook
from .vision import MotionRegion


@dataclass(eq=False)
class FrameAsset:
    """Сохранённый на диск кадр эпизода."""

    local_index: int
    camera: str
    is_wrist: bool
    path: str                  # путь, попадающий в JSONL
    width: int
    height: int
    image: np.ndarray | None = None
    motion: MotionRegion | None = None

    @property
    def key(self) -> str:
        return f"{self.camera}:{self.local_index}"


@dataclass
class EpisodeContext:
    source: str
    uid: str
    instruction: str
    parsed: ParsedInstruction
    kin: EpisodeKinematics
    frames: list[FrameAsset]
    primary_camera: str
    wrist_camera: str | None
    phrasebook: Phrasebook
    seed: int
    config: Any
    other_instructions: list[str] = field(default_factory=list)
    other_objects: list[str] = field(default_factory=list)
    fps: float = 10.0
    kind: str = "robot"        # robot | ego
    extra: dict[str, Any] = field(default_factory=dict)

    def frames_of(self, camera: str) -> list[FrameAsset]:
        return [f for f in self.frames if f.camera == camera]

    def frame_at(self, camera: str, local_index: int) -> FrameAsset | None:
        for frame in self.frames:
            if frame.camera == camera and frame.local_index == local_index:
                return frame
        return None

    def primary_frames(self) -> list[FrameAsset]:
        return self.frames_of(self.primary_camera)


@dataclass
class Sample:
    """Один обучающий пример до сериализации в ShareGPT."""

    task: str
    template: str
    user: str
    assistant: str
    images: list[str]
    meta: dict[str, Any] = field(default_factory=dict)

    def to_sharegpt(self) -> dict[str, Any]:
        return {
            "messages": [
                {"role": "user", "content": self.user},
                {"role": "assistant", "content": self.assistant},
            ],
            "images": list(self.images),
        }

    @property
    def n_placeholders(self) -> int:
        return self.user.count("<image>")
