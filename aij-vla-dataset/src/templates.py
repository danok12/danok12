"""Текстовые шаблоны вопросов/ответов и сборка примеров с множественным выбором.

Формулировки намеренно разнообразны: один шаблон не должен доминировать, иначе
VLM переобучается на форму, а не на содержание (см. language.max_share_per_template).
Директивы ответа для MCQ повторяют формулировки оценочных наборов (MMMU/BLINK),
чтобы модель училась отвечать в ожидаемом формате.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Sequence

from .utils import stable_hash

LETTERS = "ABCDEFGH"

#: Строгие директивы требуют ответа одной буквой (как в MMMU/BLINK),
#: «мягкая» допускает букву с коротким пояснением.
MCQ_DIRECTIVES: list[str] = [
    "Answer with the option's letter from the given choices directly.",
    "Answer with the letter of the correct option.",
    "Select the correct option and reply with its letter only.",
]
MCQ_SOFT_DIRECTIVE = "Choose the correct option and explain your choice in one short phrase."

#: Пулы формулировок вопросов. Ключ — идентификатор шаблона (учитывается в квоте).
QUESTION_POOLS: dict[str, list[str]] = {
    "gripper_state": [
        "Look at the robot gripper. Is it open or closed?",
        "What is the state of the robot's gripper in this frame?",
        "Is the robot currently holding anything in its gripper?",
    ],
    "phase": [
        "Which stage of the task is the robot in right now?",
        "What is the robot doing at this moment?",
        "Describe the current stage of the manipulation.",
    ],
    "progress": [
        "How far along is the robot in completing the instruction?",
        "Estimate how much of the task has been completed.",
        "What fraction of the task is already done?",
    ],
    "subtask": [
        "What subtask is the robot currently performing?",
        "Which step of the instruction is being executed in this frame?",
        "Name the immediate subgoal the robot is working on.",
    ],
    "next_subtask": [
        "What should the robot do next?",
        "Which step comes right after what you see in the image?",
        "State the next subtask the robot has to perform.",
    ],
    "instruction_decomp": [
        "Break the instruction into the sequence of steps the robot must perform.",
        "List the subtasks needed to carry out the instruction.",
        "Decompose the task into ordered steps.",
    ],
    "instruction_check": [
        "Is the robot in this image executing the instruction below?",
        "Does the scene match the given instruction?",
        "Judge whether the image belongs to an episode with this instruction.",
    ],
    "object_role": [
        "Which object is the robot manipulating?",
        "What is the target object of the instruction?",
        "Where is the robot supposed to put the object?",
    ],
    "spatial_relation": [
        "In which part of the image is the moving robot arm?",
        "Where in the workspace is the robot arm right now?",
        "Describe the position of the robot arm inside the frame.",
    ],
    "grounding_box": [
        "Locate the moving part of the robot arm in this frame.",
        "Return the bounding box of the region where the manipulation happens.",
        "Give the bounding box of the robot arm.",
    ],
    "grounding_point": [
        "Point at the place where the robot is acting.",
        "Give the image coordinates of the robot arm.",
        "Mark the manipulation point with a single coordinate.",
    ],
    "temporal_order": [
        "Which of the two frames was recorded earlier?",
        "Put the two frames in chronological order.",
        "Did the first image come before or after the second one?",
    ],
    "progress_compare": [
        "Which frame is closer to the completion of the task?",
        "In which of the two images has the robot made more progress?",
    ],
    "frame_transition": [
        "What changed between the first and the second frame?",
        "Describe what the robot did between these two moments.",
        "Compare the two frames and explain the robot's action.",
    ],
    "multiview_match": [
        "Do these two images show the same scene at the same moment?",
        "Are both views captured at the same instant of the same episode?",
    ],
    "view_role": [
        "Which of the two images comes from the camera mounted on the robot's wrist?",
        "One image is a fixed third-person view and one is a wrist view. Which is which?",
    ],
    "episode_summary": [
        "Summarize what the robot does across these frames.",
        "Describe the trajectory shown by this sequence of frames.",
    ],
    "failure_diagnosis": [
        "The robot is not making progress here. What is going wrong?",
        "Diagnose the problem visible in this frame.",
        "Why has the task execution stalled?",
    ],
    "recovery_instruction": [
        "What should the robot do to recover and continue the task?",
        "Give a corrective instruction for the robot.",
        "Propose a recovery action for the situation in the image.",
    ],
    "scene_caption": [
        "Describe the scene and what the robot is doing.",
        "Give a short description of this robot workspace.",
        "What do you see in this image?",
    ],
    "ego_transition": [
        "What changed between these two moments of the video?",
        "Describe the action performed between the two frames.",
    ],
    "ego_temporal_order": [
        "Which frame comes first in the video?",
        "Order these two frames in time.",
    ],
}

PROGRESS_BUCKETS: list[tuple[float, str]] = [
    (0.10, "the task has just started"),
    (0.30, "roughly a quarter of the task is done"),
    (0.55, "about half of the task is done"),
    (0.80, "roughly three quarters of the task is done"),
    (0.95, "the task is nearly finished"),
    (1.01, "the task is finished"),
]

PROGRESS_OPTIONS: list[str] = [bucket for _, bucket in PROGRESS_BUCKETS]

GRIPPER_ANSWERS: dict[str, str] = {
    "open": "The gripper is open and is not holding anything.",
    "closed": "The gripper is closed.",
    "closed_holding": "The gripper is closed and is holding the object.",
    "unknown": "The gripper state cannot be determined from this view.",
}

GRIPPER_OPTIONS: list[str] = [
    "open, holding nothing",
    "closed on an object it is holding",
    "closed but empty",
    "opening to release an object",
]


@dataclass
class MCQ:
    stem: str
    options: list[str]
    answer_index: int
    directive: str

    @property
    def letter(self) -> str:
        return LETTERS[self.answer_index]

    def user_text(self) -> str:
        lines = [self.stem, ""]
        lines += [f"{LETTERS[i]}. {opt}" for i, opt in enumerate(self.options)]
        lines.append(self.directive)
        return "\n".join(lines)


@dataclass
class Phrasebook:
    """Детерминированный выбор формулировок с учётом ключа примера."""

    seed: int
    mcq_min_options: int = 3
    mcq_max_options: int = 4
    answer_prefix: str = "Answer: "
    balance_letters: bool = True
    used_templates: dict[str, int] = field(default_factory=dict)

    def question(self, pool: str, key: str) -> tuple[str, str]:
        """Вопрос и идентификатор шаблона (pool#idx) для учёта квот."""
        variants = QUESTION_POOLS[pool]
        idx = stable_hash(self.seed, pool, key) % len(variants)
        return variants[idx], f"{pool}#{idx}"

    def choice(self, options: Sequence[str], key: str) -> str:
        return options[stable_hash(self.seed, key) % len(options)]

    def build_mcq(
        self,
        stem: str,
        correct: str,
        distractors: Sequence[str],
        key: str,
        *,
        max_options: int | None = None,
    ) -> MCQ | None:
        pool = [d for d in dict.fromkeys(distractors) if d and d != correct]
        if not pool:
            return None
        rng = random.Random(stable_hash(self.seed, "mcq", key))
        rng.shuffle(pool)
        limit = max_options or self.mcq_max_options
        n_options = min(limit, len(pool) + 1)
        if n_options < self.mcq_min_options:
            if len(pool) + 1 < 2:
                return None
            n_options = min(len(pool) + 1, limit)
        chosen = pool[: n_options - 1]
        if self.balance_letters:
            answer_index = stable_hash(self.seed, "letter", key) % n_options
        else:
            answer_index = rng.randrange(n_options)
        options = list(chosen)
        options.insert(answer_index, correct)
        if stable_hash(self.seed, "verbose", key) % 5 == 0:
            directive = MCQ_SOFT_DIRECTIVE
        else:
            directive = MCQ_DIRECTIVES[stable_hash(self.seed, "directive", key) % len(MCQ_DIRECTIVES)]
        return MCQ(stem=stem, options=options, answer_index=answer_index, directive=directive)

    def mcq_answer(self, mcq: MCQ, key: str) -> str:
        """Формат ответа согласован с директивой в вопросе."""
        if mcq.directive == MCQ_SOFT_DIRECTIVE:
            return f"{self.answer_prefix}{mcq.letter}. {mcq.options[mcq.answer_index]}"
        return mcq.letter


def progress_bucket(progress: float) -> str:
    for threshold, label in PROGRESS_BUCKETS:
        if progress < threshold:
            return label
    return PROGRESS_BUCKETS[-1][1]


def progress_percent(progress: float) -> int:
    return int(round(max(0.0, min(1.0, float(progress))) * 100 / 5.0) * 5)
