"""Генераторы обучающих сигналов.

Каждый генератор получает контекст эпизода (кадры + кинематика + разобранная
инструкция) и возвращает список примеров. Все ответы выводятся из фактических
данных траектории: проприоцепции, событий схвата, порядка кадров и разностной
локализации движения. Ни один ответ не придумывается моделью.

Важно: датасет остаётся vision-language. Ни один пример не просит модель
предсказать «сырой» или дискретизированный вектор действия — речь только о
понимании сцены, состояния, прогресса и подзадач на естественном языке.
"""

from __future__ import annotations

from typing import Callable, Iterable

from .kinematics import (
    PHASE_ALIGN,
    PHASE_APPROACH,
    PHASE_GLOSS,
    PHASE_IDLE,
    PHASE_LABEL,
    PHASE_RELEASE,
    PHASE_RETREAT,
)
from .language import decompose, next_subtask_for_phase, subtask_for_phase
from .records import EpisodeContext, FrameAsset, Sample
from .templates import (
    GRIPPER_ANSWERS,
    GRIPPER_OPTIONS,
    PROGRESS_OPTIONS,
    progress_bucket,
    progress_percent,
)
from .utils import stable_hash
from .vision import direction_word, grid_cell

Generator = Callable[[EpisodeContext], list[Sample]]
#: имя -> (функция, поддерживаемые типы источника)
REGISTRY: dict[str, tuple[Generator, tuple[str, ...]]] = {}


def generator(name: str, kinds: tuple[str, ...] = ("robot",)) -> Callable[[Generator], Generator]:
    """Регистрация генератора. kinds ограничивает типы источников (robot | ego)."""

    def decorator(func: Generator) -> Generator:
        REGISTRY[name] = (func, kinds)
        return func

    return decorator


# ------------------------------------------------------------------ утилиты
def _img(user_text: str, n_images: int = 1) -> str:
    if n_images == 1:
        return f"<image>\n{user_text}"
    header = "\n".join(f"Image {i + 1}: <image>" for i in range(n_images))
    return f"{header}\n{user_text}"


def _with_instruction(text: str, instruction: str) -> str:
    return f"{text}\nInstruction: {instruction}" if instruction else text


def _pick(items: list[FrameAsset], count: int, key: str, seed: int) -> list[FrameAsset]:
    """Детерминированная выборка кадров, равномерно распределённая по эпизоду."""
    if not items or count <= 0:
        return []
    if len(items) <= count:
        return list(items)
    step = len(items) / float(count)
    offset = (stable_hash(seed, key) % 1000) / 1000.0
    picked: list[FrameAsset] = []
    for i in range(count):
        idx = int(min(len(items) - 1, (i + offset) * step))
        if picked and picked[-1] is items[idx]:
            idx = min(len(items) - 1, idx + 1)
        picked.append(items[idx])
    return list(dict.fromkeys(picked))


def _mcq_sample(
    ctx: EpisodeContext,
    *,
    task: str,
    pool: str,
    stem_extra: str,
    correct: str,
    distractors: Iterable[str],
    key: str,
    images: list[str],
    n_images: int = 1,
    meta: dict | None = None,
) -> Sample | None:
    question, template = ctx.phrasebook.question(pool, key)
    stem = f"{question}\n{stem_extra}".strip() if stem_extra else question
    mcq = ctx.phrasebook.build_mcq(stem, correct, list(distractors), key)
    if mcq is None:
        return None
    return Sample(
        task=task,
        template=f"{template}|mcq",
        user=_img(mcq.user_text(), n_images),
        assistant=ctx.phrasebook.mcq_answer(mcq, key),
        images=images,
        meta={
            "format": "mcq",
            "episode": ctx.uid,
            "answer_letter": mcq.letter,
            "answer_options": len(mcq.options),
            **(meta or {}),
        },
    )


def _open_sample(
    ctx: EpisodeContext,
    *,
    task: str,
    pool: str,
    stem_extra: str,
    answer: str,
    key: str,
    images: list[str],
    n_images: int = 1,
    meta: dict | None = None,
) -> Sample:
    question, template = ctx.phrasebook.question(pool, key)
    stem = f"{question}\n{stem_extra}".strip() if stem_extra else question
    return Sample(
        task=task,
        template=f"{template}|open",
        user=_img(stem, n_images),
        assistant=answer,
        images=images,
        meta={"format": "open", "episode": ctx.uid, **(meta or {})},
    )


def _use_mcq(ctx: EpisodeContext, key: str) -> bool:
    share = float(ctx.config.get("language.mcq_share", 0.4))
    return (stable_hash(ctx.seed, "fmt", key) % 1000) < int(share * 1000)


def _third_person_frames(ctx: EpisodeContext) -> list[FrameAsset]:
    frames = [f for f in ctx.primary_frames() if not f.is_wrist]
    return frames or ctx.primary_frames()


# ------------------------------------------------------- состояние и фазы
@generator("gripper_state")
def gen_gripper_state(ctx: EpisodeContext) -> list[Sample]:
    if not ctx.kin.has_gripper or ctx.kin.aperture is None:
        return []
    out: list[Sample] = []
    for frame in _pick(_third_person_frames(ctx), 2, "gripper", ctx.seed):
        idx = frame.local_index
        aperture = float(ctx.kin.aperture[min(idx, ctx.kin.length - 1)])
        if 0.25 < aperture < 0.7:          # неоднозначное положение — пропускаем
            continue
        word = ctx.kin.gripper_word(idx)
        key = f"{ctx.uid}:grip:{frame.key}"
        correct = {
            "open": "open, holding nothing",
            "closed_holding": "closed on an object it is holding",
            "closed": "closed but empty",
        }.get(word)
        if correct is None:
            continue
        if _use_mcq(ctx, key):
            sample = _mcq_sample(
                ctx,
                task="gripper_state",
                pool="gripper_state",
                stem_extra="",
                correct=correct,
                distractors=[o for o in GRIPPER_OPTIONS if o != correct],
                key=key,
                images=[frame.path],
                meta={"frame": idx, "gripper": word},
            )
        else:
            sample = _open_sample(
                ctx,
                task="gripper_state",
                pool="gripper_state",
                stem_extra="",
                answer=GRIPPER_ANSWERS[word],
                key=key,
                images=[frame.path],
                meta={"frame": idx, "gripper": word},
            )
        if sample is not None:
            out.append(sample)
    return out


@generator("phase")
def gen_phase(ctx: EpisodeContext) -> list[Sample]:
    out: list[Sample] = []
    seen: set[str] = set()
    for frame in _pick(_third_person_frames(ctx), 3, "phase", ctx.seed):
        phase = ctx.kin.phase(frame.local_index)
        if phase in seen:
            continue
        seen.add(phase)
        key = f"{ctx.uid}:phase:{frame.key}"
        correct = PHASE_LABEL[phase]
        distractors = [label for name, label in PHASE_LABEL.items() if name != phase]
        if _use_mcq(ctx, key):
            sample = _mcq_sample(
                ctx,
                task="phase",
                pool="phase",
                stem_extra=f"Instruction: {ctx.instruction}" if ctx.instruction else "",
                correct=correct,
                distractors=distractors,
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "phase": phase},
            )
        else:
            answer = f"The robot is {correct}: {PHASE_GLOSS[phase]}."
            sample = _open_sample(
                ctx,
                task="phase",
                pool="phase",
                stem_extra=f"Instruction: {ctx.instruction}" if ctx.instruction else "",
                answer=answer,
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "phase": phase},
            )
        if sample is not None:
            out.append(sample)
    return out


@generator("progress")
def gen_progress(ctx: EpisodeContext) -> list[Sample]:
    out: list[Sample] = []
    for frame in _pick(_third_person_frames(ctx), 2, "progress", ctx.seed):
        idx = frame.local_index
        progress = float(ctx.kin.progress[min(idx, ctx.kin.length - 1)])
        phase = ctx.kin.phase(idx)
        bucket = progress_bucket(progress)
        percent = progress_percent(progress)
        if bucket == PROGRESS_OPTIONS[-1] and phase not in {PHASE_RELEASE, PHASE_RETREAT, PHASE_IDLE}:
            # Последний кадр эпизода ещё не означает завершения: рука может быть
            # в контакте с объектом. Не утверждаем то, чего кадр не подтверждает.
            bucket = PROGRESS_OPTIONS[-2]
            percent = min(percent, 95)
        key = f"{ctx.uid}:progress:{frame.key}"
        if _use_mcq(ctx, key):
            sample = _mcq_sample(
                ctx,
                task="progress",
                pool="progress",
                stem_extra=f"Instruction: {ctx.instruction}" if ctx.instruction else "",
                correct=bucket,
                distractors=[o for o in PROGRESS_OPTIONS if o != bucket],
                key=key,
                images=[frame.path],
                meta={"frame": idx, "progress": round(progress, 3), "phase": phase},
            )
        else:
            answer = (
                f"About {percent}% of the task is complete — {bucket}. "
                f"The robot is {PHASE_LABEL[phase]}."
            )
            sample = _open_sample(
                ctx,
                task="progress",
                pool="progress",
                stem_extra=f"Instruction: {ctx.instruction}" if ctx.instruction else "",
                answer=answer,
                key=key,
                images=[frame.path],
                meta={"frame": idx, "progress": round(progress, 3), "phase": phase},
            )
        if sample is not None:
            out.append(sample)
    return out


# --------------------------------------------------------------- подзадачи
@generator("subtask")
def gen_subtask(ctx: EpisodeContext) -> list[Sample]:
    if not ctx.parsed.is_valid:
        return []
    steps = decompose(ctx.parsed)
    out: list[Sample] = []
    for frame in _pick(_third_person_frames(ctx), 3, "subtask", ctx.seed):
        phase = ctx.kin.phase(frame.local_index)
        current = subtask_for_phase(ctx.parsed, phase)
        key = f"{ctx.uid}:sub:{frame.key}"
        if _use_mcq(ctx, key):
            sample = _mcq_sample(
                ctx,
                task="subtask",
                pool="subtask",
                stem_extra=f"Instruction: {ctx.instruction}",
                correct=current,
                distractors=[s for s in steps if s != current],
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "phase": phase},
            )
        else:
            sample = _open_sample(
                ctx,
                task="subtask",
                pool="subtask",
                stem_extra=f"Instruction: {ctx.instruction}",
                answer=f"The robot is working on this subtask: {current}.",
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "phase": phase},
            )
        if sample is not None:
            out.append(sample)

        nxt = next_subtask_for_phase(ctx.parsed, phase)
        nkey = f"{ctx.uid}:next:{frame.key}"
        out.append(
            _open_sample(
                ctx,
                task="subtask",
                pool="next_subtask",
                stem_extra=f"Instruction: {ctx.instruction}",
                answer=f"Next it has to {nxt}." if not nxt.startswith("the task") else nxt.capitalize() + ".",
                key=nkey,
                images=[frame.path],
                meta={"frame": frame.local_index, "phase": phase, "kind": "next"},
            )
        )
    return out


@generator("instruction_decomp")
def gen_instruction_decomp(ctx: EpisodeContext) -> list[Sample]:
    if not ctx.parsed.is_valid:
        return []
    frames = _pick(_third_person_frames(ctx), 1, "decomp", ctx.seed)
    if not frames:
        return []
    steps = decompose(ctx.parsed)
    listing = "\n".join(f"{i + 1}. {step.capitalize()}." for i, step in enumerate(steps))
    key = f"{ctx.uid}:decomp"
    return [
        _open_sample(
            ctx,
            task="instruction_decomp",
            pool="instruction_decomp",
            stem_extra=f"Instruction: {ctx.instruction}",
            answer=listing,
            key=key,
            images=[frames[0].path],
            meta={"frame": frames[0].local_index, "steps": len(steps)},
        )
    ]


@generator("instruction_check")
def gen_instruction_check(ctx: EpisodeContext) -> list[Sample]:
    if not ctx.instruction:
        return []
    out: list[Sample] = []
    frames = _pick(_third_person_frames(ctx), 2, "check", ctx.seed)
    for position, frame in enumerate(frames):
        key = f"{ctx.uid}:check:{frame.key}"
        positive = (stable_hash(ctx.seed, "pos", key) % 2) == 0 or not ctx.other_instructions
        if positive:
            candidate = ctx.instruction
            answer = (
                f"Yes. The robot is executing \"{ctx.instruction}\"; right now it is "
                f"{PHASE_LABEL[ctx.kin.phase(frame.local_index)]}."
            )
        else:
            pick = stable_hash(ctx.seed, "neg", key) % len(ctx.other_instructions)
            candidate = ctx.other_instructions[pick]
            if candidate.strip().lower() == ctx.instruction.strip().lower():
                continue
            answer = (
                f"No. The scene does not match that instruction — the robot is executing "
                f"\"{ctx.instruction}\"."
            )
        out.append(
            _open_sample(
                ctx,
                task="instruction_check",
                pool="instruction_check",
                stem_extra=f"Instruction: {candidate}\nAnswer yes or no and justify in one sentence.",
                answer=answer,
                key=key + str(position),
                images=[frame.path],
                meta={"frame": frame.local_index, "positive": positive},
            )
        )
    return out


@generator("object_role")
def gen_object_role(ctx: EpisodeContext) -> list[Sample]:
    if not ctx.parsed.is_valid or not ctx.parsed.obj_short:
        return []
    frames = _pick(_third_person_frames(ctx), 1, "objrole", ctx.seed)
    if not frames:
        return []
    frame = frames[0]
    out: list[Sample] = []
    key = f"{ctx.uid}:obj"
    distractors = [o for o in ctx.other_objects if o and o != ctx.parsed.obj_short]
    stem_extra = f"Instruction: {ctx.instruction}"
    if distractors and _use_mcq(ctx, key):
        sample = _mcq_sample(
            ctx,
            task="object_role",
            pool="object_role",
            stem_extra=stem_extra,
            correct=f"the {ctx.parsed.obj_short}",
            distractors=[f"the {d}" for d in distractors],
            key=key,
            images=[frame.path],
            meta={"frame": frame.local_index},
        )
        if sample is not None:
            out.append(sample)
    else:
        answer = f"The robot manipulates the {ctx.parsed.obj_short}."
        if ctx.parsed.target_short:
            answer += f" It has to end up {ctx.parsed.prep} the {ctx.parsed.target_short}."
        out.append(
            _open_sample(
                ctx,
                task="object_role",
                pool="object_role",
                stem_extra=stem_extra,
                answer=answer,
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index},
            )
        )
    return out


# ------------------------------------------------------------ пространство
@generator("spatial_relation")
def gen_spatial_relation(ctx: EpisodeContext) -> list[Sample]:
    if not bool(ctx.config.get("grounding.enabled", True)):
        return []
    min_conf = float(ctx.config.get("grounding.min_confidence", 0.45))
    out: list[Sample] = []
    candidates = [
        f for f in _third_person_frames(ctx) if f.motion is not None and f.motion.confidence >= min_conf
    ]
    for frame in _pick(candidates, 2, "spatial", ctx.seed):
        region = frame.motion
        assert region is not None
        cx, cy = region.centroid
        cell = grid_cell(cx, cy, frame.width, frame.height)
        key = f"{ctx.uid}:spatial:{frame.key}"
        options = [
            "top-left", "top-center", "top-right",
            "middle-left", "center", "middle-right",
            "bottom-left", "bottom-center", "bottom-right",
        ]
        if _use_mcq(ctx, key):
            sample = _mcq_sample(
                ctx,
                task="spatial_relation",
                pool="spatial_relation",
                stem_extra="Answer with the region of the image.",
                correct=cell,
                distractors=[o for o in options if o != cell],
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "cell": cell, "conf": round(region.confidence, 3)},
            )
        else:
            answer = (
                f"The moving part of the robot arm is in the {cell} region of the image."
                if cell == "center"
                else f"The moving part of the robot arm is in the {cell} region of the image, "
                f"i.e. in the {cell.replace('-', ' ')} part of the workspace."
            )
            sample = _open_sample(
                ctx,
                task="spatial_relation",
                pool="spatial_relation",
                stem_extra="",
                answer=answer,
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "cell": cell, "conf": round(region.confidence, 3)},
            )
        if sample is not None:
            out.append(sample)
    return out


@generator("grounding_box")
def gen_grounding_box(ctx: EpisodeContext) -> list[Sample]:
    if not bool(ctx.config.get("grounding.enabled", True)):
        return []
    min_conf = float(ctx.config.get("grounding.min_confidence", 0.45))
    candidates = [
        f for f in _third_person_frames(ctx)
        if f.motion is not None and f.motion.confidence >= max(min_conf, 0.55)
    ]
    out: list[Sample] = []
    for frame in _pick(candidates, 1, "box", ctx.seed):
        region = frame.motion
        assert region is not None
        x1, y1, x2, y2 = region.box
        label = "the moving part of the robot arm"
        answer = f'[{{"bbox_2d": [{x1}, {y1}, {x2}, {y2}], "label": "{label}"}}]'
        key = f"{ctx.uid}:box:{frame.key}"
        question, template = ctx.phrasebook.question("grounding_box", key)
        stem = (
            f"{question}\nThe image is {frame.width}x{frame.height} pixels. "
            "Return the answer as JSON with a \"bbox_2d\" field in pixel coordinates "
            "[x1, y1, x2, y2]."
        )
        out.append(
            Sample(
                task="grounding_box",
                template=f"{template}|box",
                user=_img(stem),
                assistant=answer,
                images=[frame.path],
                meta={
                    "format": "json",
                    "episode": ctx.uid,
                    "frame": frame.local_index,
                    "conf": round(region.confidence, 3),
                },
            )
        )
    return out


@generator("grounding_point")
def gen_grounding_point(ctx: EpisodeContext) -> list[Sample]:
    if not bool(ctx.config.get("grounding.enabled", True)):
        return []
    min_conf = float(ctx.config.get("grounding.min_confidence", 0.45))
    candidates = [
        f for f in _third_person_frames(ctx)
        if f.motion is not None and f.motion.confidence >= max(min_conf, 0.55)
    ]
    out: list[Sample] = []
    for frame in _pick(candidates, 1, "point", ctx.seed):
        region = frame.motion
        assert region is not None
        cx, cy = region.centroid
        key = f"{ctx.uid}:point:{frame.key}"
        question, template = ctx.phrasebook.question("grounding_point", key)
        stem = (
            f"{question}\nThe image is {frame.width}x{frame.height} pixels. "
            "Return the answer as JSON with a \"point_2d\" field in pixel coordinates [x, y]."
        )
        out.append(
            Sample(
                task="grounding_point",
                template=f"{template}|point",
                user=_img(stem),
                assistant=f'[{{"point_2d": [{cx}, {cy}], "label": "the moving robot arm"}}]',
                images=[frame.path],
                meta={
                    "format": "json",
                    "episode": ctx.uid,
                    "frame": frame.local_index,
                    "conf": round(region.confidence, 3),
                },
            )
        )
    return out


# ------------------------------------------------------------------ время
def _frame_pair(ctx: EpisodeContext, key: str, min_gap: int = 3) -> tuple[FrameAsset, FrameAsset] | None:
    frames = sorted(_third_person_frames(ctx), key=lambda f: f.local_index)
    if len(frames) < 2:
        return None
    pairs = [
        (a, b)
        for i, a in enumerate(frames)
        for b in frames[i + 1 :]
        if b.local_index - a.local_index >= min_gap
    ]
    if not pairs:
        pairs = [(frames[0], frames[-1])]
    return pairs[stable_hash(ctx.seed, key) % len(pairs)]


@generator("temporal_order")
def gen_temporal_order(ctx: EpisodeContext) -> list[Sample]:
    pair = _frame_pair(ctx, f"{ctx.uid}:order")
    if pair is None:
        return []
    early, late = pair
    key = f"{ctx.uid}:order:{early.key}:{late.key}"
    swap = (stable_hash(ctx.seed, "swap", key) % 2) == 1
    first, second = (late, early) if swap else (early, late)
    correct = "the second image" if swap else "the first image"
    question, template = ctx.phrasebook.question("temporal_order", key)
    stem = (
        f"{question}\nBoth frames come from the same episode of a robot performing: "
        f"{ctx.instruction}." if ctx.instruction else question
    )
    mcq = ctx.phrasebook.build_mcq(
        stem, correct, ["the first image", "the second image", "they are simultaneous"], key
    )
    if mcq is None:
        return []
    return [
        Sample(
            task="temporal_order",
            template=f"{template}|mcq",
            user=_img(mcq.user_text(), 2),
            assistant=ctx.phrasebook.mcq_answer(mcq, key),
            images=[first.path, second.path],
            meta={
                "format": "mcq",
                "episode": ctx.uid,
                "answer_letter": mcq.letter,
                "answer_options": len(mcq.options),
                "frames": [first.local_index, second.local_index],
            },
        )
    ]


@generator("progress_compare")
def gen_progress_compare(ctx: EpisodeContext) -> list[Sample]:
    pair = _frame_pair(ctx, f"{ctx.uid}:cmp", min_gap=4)
    if pair is None:
        return []
    early, late = pair
    key = f"{ctx.uid}:cmp:{early.key}:{late.key}"
    swap = (stable_hash(ctx.seed, "cmpswap", key) % 2) == 1
    first, second = (late, early) if swap else (early, late)
    correct = "the first image" if swap else "the second image"
    question, template = ctx.phrasebook.question("progress_compare", key)
    stem = _with_instruction(question, ctx.instruction)
    mcq = ctx.phrasebook.build_mcq(
        stem, correct, ["the first image", "the second image", "both show the same progress"], key
    )
    if mcq is None:
        return []
    return [
        Sample(
            task="progress_compare",
            template=f"{template}|mcq",
            user=_img(mcq.user_text(), 2),
            assistant=ctx.phrasebook.mcq_answer(mcq, key),
            images=[first.path, second.path],
            meta={
                "format": "mcq",
                "episode": ctx.uid,
                "answer_letter": mcq.letter,
                "answer_options": len(mcq.options),
                "frames": [first.local_index, second.local_index],
            },
        )
    ]


@generator("frame_transition")
def gen_frame_transition(ctx: EpisodeContext) -> list[Sample]:
    pair = _frame_pair(ctx, f"{ctx.uid}:trans", min_gap=2)
    if pair is None:
        return []
    early, late = pair
    key = f"{ctx.uid}:trans:{early.key}:{late.key}"
    parts: list[str] = []
    kin = ctx.kin
    i0, i1 = early.local_index, late.local_index

    if kin.has_gripper and kin.closed is not None:
        was = bool(kin.closed[min(i0, kin.length - 1)])
        now = bool(kin.closed[min(i1, kin.length - 1)])
        obj = ctx.parsed.obj_short or "the object"
        if not was and now:
            parts.append(f"the gripper closed on the {obj}")
        elif was and not now:
            parts.append(f"the gripper opened and released the {obj}")
        elif was and now:
            parts.append(f"the gripper stayed closed around the {obj}")
        else:
            parts.append("the gripper stayed open")

    if kin.height is not None and kin.length > max(i0, i1):
        dz = float(kin.height[i1] - kin.height[i0])
        if abs(dz) > 0.015:
            parts.append("the arm moved upward" if dz > 0 else "the arm moved downward")

    if early.motion is not None and late.motion is not None:
        dx = late.motion.centroid[0] - early.motion.centroid[0]
        dy = late.motion.centroid[1] - early.motion.centroid[1]
        word = direction_word(dx, dy, tolerance=max(6.0, 0.02 * early.width))
        if word != "barely":
            parts.append(f"the end effector shifted {word} in the image")

    phase_a, phase_b = kin.phase(i0), kin.phase(i1)
    if phase_a != phase_b:
        parts.append(f"the robot went from {PHASE_LABEL[phase_a]} to {PHASE_LABEL[phase_b]}")
    if not parts:
        return []

    answer = "Between the two frames " + ", ".join(parts) + "."
    if ctx.instruction:
        answer += f" The overall task is: {ctx.instruction}."
    question, template = ctx.phrasebook.question("frame_transition", key)
    return [
        Sample(
            task="frame_transition",
            template=f"{template}|open",
            user=_img(_with_instruction(question, ctx.instruction), 2),
            assistant=answer,
            images=[early.path, late.path],
            meta={"format": "open", "episode": ctx.uid, "frames": [i0, i1]},
        )
    ]


# ------------------------------------------------------------------- виды
@generator("multiview_match")
def gen_multiview_match(ctx: EpisodeContext) -> list[Sample]:
    if ctx.wrist_camera is None:
        return []
    primary = sorted(_third_person_frames(ctx), key=lambda f: f.local_index)
    wrist = sorted(ctx.frames_of(ctx.wrist_camera), key=lambda f: f.local_index)
    if not primary or not wrist:
        return []
    key = f"{ctx.uid}:mv"
    aligned = (stable_hash(ctx.seed, "mv", key) % 2) == 0
    anchor = primary[stable_hash(ctx.seed, "mvidx", key) % len(primary)]
    if aligned:
        partner = min(wrist, key=lambda f: abs(f.local_index - anchor.local_index))
        if abs(partner.local_index - anchor.local_index) > 1:
            return []
        answer = (
            "Yes. Both images are captured at the same moment: the fixed camera and the "
            "wrist camera show the same configuration of the arm and the workspace."
        )
    else:
        far = [f for f in wrist if abs(f.local_index - anchor.local_index) >= max(3, ctx.kin.length // 3)]
        if not far:
            return []
        partner = far[stable_hash(ctx.seed, "mvfar", key) % len(far)]
        answer = (
            "No. The two views are taken at different moments of the episode — the arm is at a "
            "different stage of the task in each of them."
        )
    question, template = ctx.phrasebook.question("multiview_match", key)
    return [
        Sample(
            task="multiview_match",
            template=f"{template}|open",
            user=_img(f"{question}\nAnswer yes or no and explain in one sentence.", 2),
            assistant=answer,
            images=[anchor.path, partner.path],
            meta={
                "format": "open",
                "episode": ctx.uid,
                "aligned": aligned,
                "frames": [anchor.local_index, partner.local_index],
            },
        )
    ]


@generator("view_role")
def gen_view_role(ctx: EpisodeContext) -> list[Sample]:
    if ctx.wrist_camera is None:
        return []
    primary = sorted(_third_person_frames(ctx), key=lambda f: f.local_index)
    wrist = sorted(ctx.frames_of(ctx.wrist_camera), key=lambda f: f.local_index)
    if not primary or not wrist:
        return []
    key = f"{ctx.uid}:view"
    anchor = primary[stable_hash(ctx.seed, "viewidx", key) % len(primary)]
    partner = min(wrist, key=lambda f: abs(f.local_index - anchor.local_index))
    swap = (stable_hash(ctx.seed, "viewswap", key) % 2) == 1
    images = [partner.path, anchor.path] if swap else [anchor.path, partner.path]
    correct = "the first image" if swap else "the second image"
    question, template = ctx.phrasebook.question("view_role", key)
    mcq = ctx.phrasebook.build_mcq(
        question, correct, ["the first image", "the second image", "both images"], key
    )
    if mcq is None:
        return []
    return [
        Sample(
            task="view_role",
            template=f"{template}|mcq",
            user=_img(mcq.user_text(), 2),
            assistant=ctx.phrasebook.mcq_answer(mcq, key),
            images=images,
            meta={
                "format": "mcq",
                "episode": ctx.uid,
                "answer_letter": mcq.letter,
                "answer_options": len(mcq.options),
            },
        )
    ]


@generator("episode_summary")
def gen_episode_summary(ctx: EpisodeContext) -> list[Sample]:
    frames = sorted(_third_person_frames(ctx), key=lambda f: f.local_index)
    if len(frames) < 3:
        return []
    picked = _pick(frames, 3, "summary", ctx.seed)
    picked = sorted(picked, key=lambda f: f.local_index)
    if len(picked) < 3:
        return []
    phases = [PHASE_LABEL[ctx.kin.phase(f.local_index)] for f in picked]
    story = "; then ".join(dict.fromkeys(phases))
    answer = (
        f"The frames follow one episode in chronological order. The robot is {story}. "
        f"The instruction being carried out is: {ctx.instruction}."
        if ctx.instruction
        else f"The frames follow one episode in chronological order: the robot is {story}."
    )
    key = f"{ctx.uid}:summary"
    question, template = ctx.phrasebook.question("episode_summary", key)
    return [
        Sample(
            task="episode_summary",
            template=f"{template}|open",
            user=_img(question, len(picked)),
            assistant=answer,
            images=[f.path for f in picked],
            meta={"format": "open", "episode": ctx.uid, "frames": [f.local_index for f in picked]},
        )
    ]


# ---------------------------------------------------- ошибки и восстановление
def _failure_frames(ctx: EpisodeContext) -> list[tuple[FrameAsset, str]]:
    """Кадры, где выполнение застопорилось или захват не удался."""
    out: list[tuple[FrameAsset, str]] = []
    kin = ctx.kin
    frames = _third_person_frames(ctx)
    for frame in frames:
        idx = frame.local_index
        if idx in kin.slip_frames or any(abs(idx - s) <= 1 for s in kin.slip_frames):
            out.append((frame, "slip"))
            continue
        for start, end in kin.stalls:
            if start <= idx <= end and kin.phase(idx) in {PHASE_APPROACH, PHASE_ALIGN, PHASE_IDLE}:
                out.append((frame, "stall"))
                break
    return out


@generator("failure_diagnosis")
def gen_failure_diagnosis(ctx: EpisodeContext) -> list[Sample]:
    out: list[Sample] = []
    obj = ctx.parsed.obj_short or "the object"
    for frame, reason in _failure_frames(ctx)[:2]:
        key = f"{ctx.uid}:fail:{frame.key}"
        if reason == "slip":
            answer = (
                f"The gripper closed completely without holding anything: the fingers are fully shut, "
                f"so the {obj} was not picked up. The grasp missed the object."
            )
        else:
            answer = (
                f"The arm has stopped moving while the task is not finished — it is still "
                f"{PHASE_LABEL[ctx.kin.phase(frame.local_index)]} and the {obj} has not been "
                "handled yet. The execution is stuck at this step."
            )
        out.append(
            _open_sample(
                ctx,
                task="failure_diagnosis",
                pool="failure_diagnosis",
                stem_extra=f"Instruction: {ctx.instruction}" if ctx.instruction else "",
                answer=answer,
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "reason": reason},
            )
        )
    return out


@generator("recovery_instruction")
def gen_recovery_instruction(ctx: EpisodeContext) -> list[Sample]:
    out: list[Sample] = []
    obj = ctx.parsed.obj_short or "the object"
    for frame, reason in _failure_frames(ctx)[:2]:
        key = f"{ctx.uid}:recover:{frame.key}"
        if reason == "slip":
            answer = (
                f"Open the gripper, lift it a few centimetres, move it back over the {obj}, "
                "re-align the fingers with the object and close the gripper again."
            )
        else:
            nxt = next_subtask_for_phase(ctx.parsed, ctx.kin.phase(frame.local_index))
            answer = f"Resume the motion: {nxt}."
        out.append(
            _open_sample(
                ctx,
                task="recovery_instruction",
                pool="recovery_instruction",
                stem_extra=f"Instruction: {ctx.instruction}" if ctx.instruction else "",
                answer=answer,
                key=key,
                images=[frame.path],
                meta={"frame": frame.local_index, "reason": reason},
            )
        )
    return out


# ----------------------------------------------------------------- описание
@generator("scene_caption")
def gen_scene_caption(ctx: EpisodeContext) -> list[Sample]:
    out: list[Sample] = []
    for frame in _pick(_third_person_frames(ctx), 2, "caption", ctx.seed):
        idx = frame.local_index
        pieces: list[str] = []
        view = "wrist-mounted camera" if frame.is_wrist else "fixed camera"
        pieces.append(f"A robot arm is at work in the scene, seen from a {view}.")
        if ctx.parsed.is_valid and ctx.parsed.obj_short:
            target = (
                f" {ctx.parsed.prep} the {ctx.parsed.target_short}" if ctx.parsed.target_short else ""
            )
            pieces.append(
                f"The commanded task is to {ctx.parsed.clauses[0].verb or 'handle'} the "
                f"{ctx.parsed.obj_short}{target}."
            )
        if frame.motion is not None and frame.motion.confidence >= float(
            ctx.config.get("grounding.min_confidence", 0.45)
        ):
            cell = grid_cell(*frame.motion.centroid, frame.width, frame.height)
            pieces.append(f"The arm is currently in the {cell} region of the image.")
        word = ctx.kin.gripper_word(idx)
        if word != "unknown":
            pieces.append(GRIPPER_ANSWERS[word])
        phase = ctx.kin.phase(idx)
        pieces.append(
            f"The robot is {PHASE_LABEL[phase]}; about {progress_percent(float(ctx.kin.progress[min(idx, ctx.kin.length - 1)]))}% "
            "of the episode has elapsed."
        )
        answer = " ".join(pieces)
        out.append(
            _open_sample(
                ctx,
                task="scene_caption",
                pool="scene_caption",
                stem_extra="",
                answer=answer,
                key=f"{ctx.uid}:cap:{frame.key}",
                images=[frame.path],
                meta={"frame": idx, "phase": phase},
            )
        )
    return out


# ------------------------------------------------------- эгоцентрическое видео
@generator("ego_temporal_order", kinds=("ego",))
def gen_ego_temporal_order(ctx: EpisodeContext) -> list[Sample]:
    frames = sorted(ctx.frames, key=lambda f: f.local_index)
    if len(frames) < 2:
        return []
    key = f"{ctx.uid}:egoorder"
    i = stable_hash(ctx.seed, "egopair", key) % (len(frames) - 1)
    early, late = frames[i], frames[i + 1]
    swap = (stable_hash(ctx.seed, "egoswap", key) % 2) == 1
    first, second = (late, early) if swap else (early, late)
    correct = "the second image" if swap else "the first image"
    question, template = ctx.phrasebook.question("ego_temporal_order", key)
    mcq = ctx.phrasebook.build_mcq(
        question, correct, ["the first image", "the second image", "they are simultaneous"], key
    )
    if mcq is None:
        return []
    return [
        Sample(
            task="ego_temporal_order",
            template=f"{template}|mcq",
            user=_img(mcq.user_text(), 2),
            assistant=ctx.phrasebook.mcq_answer(mcq, key),
            images=[first.path, second.path],
            meta={
                "format": "mcq",
                "episode": ctx.uid,
                "answer_letter": mcq.letter,
                "answer_options": len(mcq.options),
            },
        )
    ]


@generator("ego_transition", kinds=("ego",))
def gen_ego_transition(ctx: EpisodeContext) -> list[Sample]:
    frames = sorted(ctx.frames, key=lambda f: f.local_index)
    if len(frames) < 2:
        return []
    out: list[Sample] = []
    shifts = ctx.extra.get("shifts") or {}
    for early, late in zip(frames[:-1], frames[1:]):
        shift = shifts.get((early.local_index, late.local_index))
        if shift is None:
            continue
        dx, dy = shift
        word = direction_word(dx, dy, tolerance=max(4.0, 0.015 * early.width))
        if word == "barely":
            answer = "The viewpoint barely changed between the two frames; the camera stayed almost still."
        else:
            answer = (
                f"The camera viewpoint shifted {word}: the whole scene moved in the frame, which means "
                "the person wearing the camera turned or moved rather than only the objects changing."
            )
        key = f"{ctx.uid}:egotrans:{early.local_index}"
        question, template = ctx.phrasebook.question("ego_transition", key)
        out.append(
            Sample(
                task="ego_transition",
                template=f"{template}|open",
                user=_img(question, 2),
                assistant=answer,
                images=[early.path, late.path],
                meta={"format": "open", "episode": ctx.uid},
            )
        )
        if len(out) >= 2:
            break
    return out


def run_generators(ctx: EpisodeContext) -> list[Sample]:
    """Все включённые генераторы в детерминированном порядке."""
    out: list[Sample] = []
    for name in sorted(REGISTRY):
        func, kinds = REGISTRY[name]
        if ctx.kind not in kinds or not ctx.config.task_enabled(name):
            continue
        try:
            out.extend(func(ctx))
        except Exception as exc:  # noqa: BLE001 — один сбойный генератор не рушит прогон
            from .utils import get_logger

            get_logger(__name__).warning("генератор %s упал на %s: %s", name, ctx.uid, exc)
    return out
