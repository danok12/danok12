"""Извлечение семантики из состояний и действий: раскрытие схвата, события, фазы, прогресс.

Никаких допущений о конкретном воплощении: схема state/action определяется по
meta/info.json и размерностям, ориентация канала схвата калибруется по данным
(предположение «в начале эпизода схват открыт» — типично для демонстраций
манипуляции; отключается через kinematics.gripper.auto_calibrate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .utils import get_logger

LOGGER = get_logger(__name__)

PHASE_APPROACH = "approach"
PHASE_GRASP = "grasp"
PHASE_LIFT = "lift"
PHASE_TRANSPORT = "transport"
PHASE_ALIGN = "align"
PHASE_RELEASE = "release"
PHASE_RETREAT = "retreat"
PHASE_INTERACT = "interact"
PHASE_IDLE = "idle"

PHASE_ORDER = [
    PHASE_IDLE,
    PHASE_APPROACH,
    PHASE_GRASP,
    PHASE_LIFT,
    PHASE_TRANSPORT,
    PHASE_ALIGN,
    PHASE_RELEASE,
    PHASE_RETREAT,
    PHASE_INTERACT,
]

#: Человекочитаемое описание фазы (используется в ответах и вариантах MCQ).
PHASE_GLOSS: dict[str, str] = {
    PHASE_IDLE: "the arm is still, no motion has started yet",
    PHASE_APPROACH: "the arm is moving toward the target object with an open gripper",
    PHASE_GRASP: "the gripper is closing on the object",
    PHASE_LIFT: "the object has just been grasped and is being lifted",
    PHASE_TRANSPORT: "the grasped object is being carried toward the destination",
    PHASE_ALIGN: "the arm is lowering and aligning the object over the destination",
    PHASE_RELEASE: "the gripper is opening to release the object",
    PHASE_RETREAT: "the arm is moving away after finishing the manipulation",
    PHASE_INTERACT: "the arm is in contact with the object and moving it",
}

PHASE_LABEL: dict[str, str] = {
    PHASE_IDLE: "waiting before the motion starts",
    PHASE_APPROACH: "reaching toward the object",
    PHASE_GRASP: "closing the gripper on the object",
    PHASE_LIFT: "lifting the grasped object",
    PHASE_TRANSPORT: "carrying the object to the destination",
    PHASE_ALIGN: "positioning the object over the destination",
    PHASE_RELEASE: "releasing the object",
    PHASE_RETREAT: "withdrawing the arm after the task",
    PHASE_INTERACT: "pushing or moving the object in contact",
}


@dataclass
class StateSchema:
    """Какие столбцы state/action за что отвечают."""

    state_dim: int
    action_dim: int
    pos: list[int] = field(default_factory=list)
    rot: list[int] = field(default_factory=list)
    gripper: list[int] = field(default_factory=list)
    action_pos: list[int] = field(default_factory=list)
    action_gripper: int | None = None
    height_axis: int | None = None   # индекс внутри pos, отвечающий за высоту

    @property
    def has_gripper(self) -> bool:
        return bool(self.gripper) or self.action_gripper is not None


@dataclass
class GripperCalibration:
    low: float
    high: float
    open_is_high: bool
    source: str = "state"
    #: Порог «закрыт/открыт» в нормированных единицах раскрытия (метод Оцу по
    #: распределению датасета — фиксированное значение 0.5 не годится: у разных
    #: воплощений моды распределения лежат по-разному).
    threshold: float = 0.5
    #: Центр «закрытой» моды — опора для детектора сорвавшегося захвата.
    closed_center: float = 0.0

    def aperture(self, values: np.ndarray) -> np.ndarray:
        span = max(self.high - self.low, 1e-6)
        norm = np.clip((values - self.low) / span, 0.0, 1.0)
        return norm if self.open_is_high else 1.0 - norm


@dataclass
class EpisodeKinematics:
    length: int
    progress: np.ndarray
    pos: np.ndarray | None
    speed: np.ndarray
    height: np.ndarray | None
    aperture: np.ndarray | None
    closed: np.ndarray | None
    phases: list[str]
    grasp_frames: list[int]
    release_frames: list[int]
    stalls: list[tuple[int, int]]
    slip_frames: list[int]
    has_gripper: bool

    def phase(self, idx: int) -> str:
        idx = int(np.clip(idx, 0, self.length - 1))
        return self.phases[idx]

    def gripper_word(self, idx: int) -> str:
        if self.aperture is None or self.closed is None:
            return "unknown"
        idx = int(np.clip(idx, 0, self.length - 1))
        if not bool(self.closed[idx]):
            return "open"
        after_grasp = any(g <= idx for g in self.grasp_frames)
        before_release = all(r > idx for r in self.release_frames) if self.release_frames else True
        return "closed_holding" if (after_grasp and before_release) else "closed"


# ---------------------------------------------------------------- схема state
def _names_of(feature: dict[str, Any] | None) -> list[str]:
    if not feature:
        return []
    names = feature.get("names")
    if isinstance(names, dict):
        names = list(names.values())
    if not isinstance(names, list):
        return []
    flat: list[str] = []
    for item in names:
        if isinstance(item, list):
            flat.extend(str(x).lower() for x in item)
        else:
            flat.append(str(item).lower())
    return flat


def _indices_by_names(names: Sequence[str], tokens: Sequence[str]) -> list[int]:
    return [i for i, name in enumerate(names) if any(tok in name for tok in tokens)]


def infer_schema(
    state_dim: int,
    action_dim: int,
    state_names: Sequence[str] = (),
    action_names: Sequence[str] = (),
    override: dict[str, Any] | None = None,
) -> StateSchema:
    """Схема по именам признаков, иначе — по размерности (типовые раскладки VLA-датасетов)."""
    schema = StateSchema(state_dim=state_dim, action_dim=action_dim)

    pos = _indices_by_names(state_names, ("x", "y", "z")) if state_names else []
    pos = [i for i in pos if i < 3]
    grip = _indices_by_names(state_names, ("grip", "finger", "jaw")) if state_names else []
    if pos and len(pos) >= 2:
        schema.pos = pos[:3]
        schema.gripper = grip
    elif state_dim >= 7:
        schema.pos = [0, 1, 2]
        schema.rot = [3, 4, 5]
        schema.gripper = [6, 7] if state_dim == 8 else [state_dim - 1]
    elif state_dim in (2, 3):
        schema.pos = list(range(state_dim))
    elif state_dim > 0:
        schema.pos = list(range(min(3, state_dim)))
        if state_dim > 3:
            schema.gripper = [state_dim - 1]
    if len(schema.pos) >= 3:
        schema.height_axis = 2

    if action_dim >= 7:
        schema.action_pos = [0, 1, 2]
        schema.action_gripper = 6 if action_dim == 7 else action_dim - 1
    elif action_dim in (2, 3):
        schema.action_pos = list(range(action_dim))
    elif action_dim > 0:
        schema.action_pos = list(range(min(3, action_dim)))
    grip_action = _indices_by_names(action_names, ("grip", "finger", "jaw")) if action_names else []
    if grip_action:
        schema.action_gripper = grip_action[0]

    for key, value in (override or {}).items():
        if hasattr(schema, key):
            setattr(schema, key, value)
    return schema


def calibrate_gripper(
    samples: list[np.ndarray],
    *,
    open_at_start: bool = True,
    min_frames: int = 200,
) -> GripperCalibration | None:
    """Ориентация и диапазон канала схвата по выборке эпизодов.

    samples — одномерные ряды «сырого» сигнала схвата (по эпизоду на элемент).
    Предположение: в начале эпизода манипулятор ещё не взял объект, схват открыт.
    """
    flat = np.concatenate([s.reshape(-1) for s in samples if s.size]) if samples else np.array([])
    if flat.size == 0:
        return None
    low = float(np.quantile(flat, 0.02))
    high = float(np.quantile(flat, 0.98))
    if high - low < 1e-6:
        return None
    if not open_at_start or flat.size < min_frames:
        # Без калибровки берём распространённое соглашение «больше — шире раскрыт».
        return GripperCalibration(low=low, high=high, open_is_high=True)
    starts = np.array([float(np.median(s.reshape(-1)[: max(1, min(3, s.size))])) for s in samples if s.size])
    mid = 0.5 * (low + high)
    open_is_high = bool(np.median(starts) >= mid)
    calibration = GripperCalibration(low=low, high=high, open_is_high=open_is_high)
    aperture = calibration.aperture(flat)
    calibration.threshold = _otsu(aperture)
    closed = aperture[aperture < calibration.threshold]
    calibration.closed_center = float(closed.mean()) if closed.size else 0.0
    return calibration


def _otsu(values: np.ndarray, bins: int = 64) -> float:
    """Порог между двумя модами распределения (одномерный метод Оцу)."""
    hist, edges = np.histogram(values, bins=bins, range=(0.0, 1.0))
    total = hist.sum()
    if total == 0:
        return 0.5
    weights = hist.astype(np.float64) / total
    centers = 0.5 * (edges[:-1] + edges[1:])
    omega = np.cumsum(weights)
    mu = np.cumsum(weights * centers)
    mu_total = mu[-1]
    denominator = omega * (1.0 - omega)
    with np.errstate(divide="ignore", invalid="ignore"):
        between = np.where(denominator > 1e-12, (mu_total * omega - mu) ** 2 / denominator, 0.0)
    threshold = float(centers[int(np.argmax(between))])
    return float(np.clip(threshold, 0.1, 0.9))


def raw_gripper_signal(state: np.ndarray | None, action: np.ndarray | None, schema: StateSchema) -> np.ndarray | None:
    """Сырой сигнал раскрытия: расстояние между пальцами, иначе одиночный канал, иначе команда."""
    if state is not None and len(schema.gripper) >= 2:
        a, b = schema.gripper[0], schema.gripper[1]
        if a < state.shape[1] and b < state.shape[1]:
            return np.abs(state[:, a] - state[:, b])
    if state is not None and len(schema.gripper) == 1 and schema.gripper[0] < state.shape[1]:
        return state[:, schema.gripper[0]]
    if action is not None and schema.action_gripper is not None and schema.action_gripper < action.shape[1]:
        return action[:, schema.action_gripper]
    return None


# --------------------------------------------------------------------- события
def _smooth(values: np.ndarray, window: int) -> np.ndarray:
    window = max(1, int(window))
    if window <= 1 or values.size <= window:
        return values
    kernel = np.ones(window, dtype=np.float64) / window
    return np.convolve(values, kernel, mode="same")


def _transitions(closed: np.ndarray) -> tuple[list[int], list[int]]:
    grasp: list[int] = []
    release: list[int] = []
    for i in range(1, closed.size):
        if closed[i] and not closed[i - 1]:
            grasp.append(i)
        elif not closed[i] and closed[i - 1]:
            release.append(i)
    return grasp, release


def _stall_windows(speed: np.ndarray, eps: float, window: int) -> list[tuple[int, int]]:
    quiet = speed < eps
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, flag in enumerate(quiet):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start >= window:
                out.append((start, i - 1))
            start = None
    if start is not None and quiet.size - start >= window:
        out.append((start, int(quiet.size) - 1))
    return out


def analyse_episode(
    state: np.ndarray | None,
    action: np.ndarray | None,
    schema: StateSchema,
    calibration: GripperCalibration | None,
    *,
    length: int | None = None,
    params: dict[str, Any] | None = None,
) -> EpisodeKinematics:
    """Полный набор производных сигналов эпизода."""
    params = params or {}
    eps = float(params.get("velocity_eps", 0.004))
    stall_window = int(params.get("stall_window", 10))
    lift_delta = float(params.get("lift_delta", 0.02))
    slip_window = int(params.get("slip_window", 8))
    smooth_window = int(params.get("smooth_window", 3))

    if length is None:
        length = int(state.shape[0]) if state is not None else int(action.shape[0]) if action is not None else 0
    length = max(1, int(length))
    progress = np.linspace(0.0, 1.0, num=length) if length > 1 else np.zeros(1)

    pos = None
    if state is not None and schema.pos and max(schema.pos) < state.shape[1]:
        pos = state[:length, schema.pos].astype(np.float64)
    elif action is not None and schema.action_pos and max(schema.action_pos) < action.shape[1]:
        # Позиция недоступна — интегрируем дельты действий (масштаб условный).
        pos = np.cumsum(action[:length, schema.action_pos].astype(np.float64), axis=0)

    if pos is not None and pos.shape[0] > 1:
        delta = np.diff(pos, axis=0, prepend=pos[:1])
        speed = np.linalg.norm(delta, axis=1)
    else:
        speed = np.zeros(length)
    speed = _smooth(speed, smooth_window)

    height = pos[:, schema.height_axis] if (pos is not None and schema.height_axis is not None
                                            and schema.height_axis < pos.shape[1]) else None

    aperture = None
    closed = None
    grasp_frames: list[int] = []
    release_frames: list[int] = []
    raw = raw_gripper_signal(state, action, schema)
    if raw is not None and calibration is not None:
        raw = _smooth(np.asarray(raw, dtype=np.float64)[:length], smooth_window)
        aperture = calibration.aperture(raw)
        margin = 0.08
        closed = _hysteresis(
            aperture,
            low=max(0.02, calibration.threshold - margin),
            high=min(0.98, calibration.threshold + margin),
        )
        grasp_frames, release_frames = _transitions(closed)

    stalls = _stall_windows(speed, eps, stall_window)
    slip_frames = (
        _detect_slips(
            closed,
            aperture,
            grasp_frames,
            slip_window,
            empty_level=max(0.04, 0.35 * (calibration.closed_center if calibration else 0.0)),
        )
        if closed is not None
        else []
    )

    phases = _assign_phases(
        length=length,
        speed=speed,
        height=height,
        closed=closed,
        grasp_frames=grasp_frames,
        release_frames=release_frames,
        lift_delta=lift_delta,
        eps=eps,
    )

    return EpisodeKinematics(
        length=length,
        progress=progress,
        pos=pos,
        speed=speed,
        height=height,
        aperture=aperture,
        closed=closed,
        phases=phases,
        grasp_frames=grasp_frames,
        release_frames=release_frames,
        stalls=stalls,
        slip_frames=slip_frames,
        has_gripper=closed is not None,
    )


def _hysteresis(aperture: np.ndarray, *, low: float, high: float) -> np.ndarray:
    closed = np.zeros(aperture.shape, dtype=bool)
    state = aperture[0] < low
    for i, value in enumerate(aperture):
        if state and value > high:
            state = False
        elif not state and value < low:
            state = True
        closed[i] = state
    return closed


def _detect_slips(
    closed: np.ndarray,
    aperture: np.ndarray | None,
    grasp_frames: Sequence[int],
    window: int,
    empty_level: float = 0.06,
) -> list[int]:
    """Схват сомкнулся «в пустоту»: губки сошлись плотнее, чем позволил бы объект."""
    if aperture is None:
        return []
    out: list[int] = []
    for g in grasp_frames:
        end = min(len(aperture), g + max(2, window))
        if end - g < 2:
            continue
        if float(np.median(aperture[g:end])) < empty_level:
            out.append(int(g))
    return out


def _assign_phases(
    *,
    length: int,
    speed: np.ndarray,
    height: np.ndarray | None,
    closed: np.ndarray | None,
    grasp_frames: Sequence[int],
    release_frames: Sequence[int],
    lift_delta: float,
    eps: float,
) -> list[str]:
    phases = [PHASE_APPROACH] * length
    if closed is None or not grasp_frames:
        # Задача без явного захвата (толкание, открывание, включение): контакт —
        # это участок наибольшего устойчивого движения.
        moving = speed > eps
        first = int(np.argmax(moving)) if moving.any() else 0
        last = int(length - 1 - np.argmax(moving[::-1])) if moving.any() else length - 1
        for i in range(length):
            if i < first:
                phases[i] = PHASE_IDLE
            elif i <= last:
                phases[i] = PHASE_INTERACT if speed[i] > eps else PHASE_ALIGN
            else:
                phases[i] = PHASE_RETREAT
        return phases

    grasp = int(grasp_frames[0])
    release = int(release_frames[0]) if release_frames else None
    base_height = float(height[grasp]) if height is not None else None

    for i in range(length):
        if i < grasp - 1:
            phases[i] = PHASE_IDLE if speed[i] <= eps and i < max(1, grasp // 3) else PHASE_APPROACH
        elif grasp - 1 <= i <= grasp + 1:
            phases[i] = PHASE_GRASP
        elif release is not None and abs(i - release) <= 1:
            phases[i] = PHASE_RELEASE
        elif release is not None and i > release:
            phases[i] = PHASE_RETREAT
        else:
            lifted = (
                height is not None
                and base_height is not None
                and float(height[i]) - base_height > lift_delta
            )
            if not lifted:
                phases[i] = PHASE_LIFT if i <= grasp + 3 else PHASE_TRANSPORT
            elif release is not None and i > (grasp + release) // 2 and height is not None and i > 0 and height[i] < height[i - 1]:
                phases[i] = PHASE_ALIGN
            else:
                phases[i] = PHASE_TRANSPORT if i > grasp + 3 else PHASE_LIFT
    return phases


def phase_sequence(kin: EpisodeKinematics) -> list[tuple[str, int, int]]:
    """Сжатая последовательность фаз: [(phase, start, end), ...]."""
    out: list[tuple[str, int, int]] = []
    if kin.length == 0:
        return out
    current = kin.phases[0]
    start = 0
    for i in range(1, kin.length):
        if kin.phases[i] != current:
            out.append((current, start, i - 1))
            current, start = kin.phases[i], i
    out.append((current, start, kin.length - 1))
    return out
