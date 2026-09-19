"""Работа с кадрами: подготовка, фильтры качества, дедупликация, локализация движения.

Никаких нейросетевых детекторов: подвижная область (манипулятор и переносимый
объект) выделяется разностью кадров — это работает офлайн, детерминировано и
не требует сторонних весов.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from .utils import get_logger

LOGGER = get_logger(__name__)

try:  # pragma: no cover — окружение без OpenCV деградирует мягко
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]


GRID_ROWS = ("top", "middle", "bottom")
GRID_COLS = ("left", "center", "right")


@dataclass
class MotionRegion:
    box: tuple[int, int, int, int]      # x1, y1, x2, y2 в пикселях кадра
    centroid: tuple[int, int]
    confidence: float
    area_frac: float

    def normalized(self, width: int, height: int) -> tuple[float, float, float, float]:
        x1, y1, x2, y2 = self.box
        return (x1 / width, y1 / height, x2 / width, y2 / height)


# ----------------------------------------------------------------- подготовка
def resize_long_side(image: np.ndarray, long_side: int) -> np.ndarray:
    if long_side <= 0:
        return image
    h, w = image.shape[:2]
    scale = long_side / float(max(h, w))
    if scale >= 1.0:
        return image
    new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    if cv2 is not None:
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    from PIL import Image

    return np.asarray(Image.fromarray(image).resize(new_size, Image.BILINEAR), dtype=np.uint8)


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if cv2 is not None:
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return (0.299 * image[..., 0] + 0.587 * image[..., 1] + 0.114 * image[..., 2]).astype(np.uint8)


def save_frame(image: np.ndarray, path: Path, *, quality: int = 92) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    img = Image.fromarray(image)
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        img.save(path, format="JPEG", quality=int(quality), optimize=True)
    else:
        img.save(path)


# ------------------------------------------------------------------- качество
def laplacian_variance(gray: np.ndarray) -> float:
    if cv2 is not None:
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    arr = gray.astype(np.float64)
    lap = (
        -4 * arr
        + np.roll(arr, 1, 0)
        + np.roll(arr, -1, 0)
        + np.roll(arr, 1, 1)
        + np.roll(arr, -1, 1)
    )
    return float(lap[1:-1, 1:-1].var())


def frame_is_usable(
    image: np.ndarray,
    *,
    min_laplacian_var: float,
    min_mean_luma: float,
    max_mean_luma: float,
) -> bool:
    gray = to_gray(image)
    luma = float(gray.mean())
    if luma < min_mean_luma or luma > max_mean_luma:
        return False
    return laplacian_variance(gray) >= min_laplacian_var


def dhash(image: np.ndarray, size: int = 8) -> int:
    """Перцептивный хеш по градиенту (для отсева почти одинаковых кадров)."""
    gray = to_gray(image)
    if cv2 is not None:
        small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    else:
        from PIL import Image

        small = np.asarray(Image.fromarray(gray).resize((size + 1, size), Image.BILINEAR))
    diff = small[:, 1:] > small[:, :-1]
    bits = 0
    for bit in diff.reshape(-1):
        bits = (bits << 1) | int(bit)
    return bits


def hamming(a: int, b: int) -> int:
    return int(bin(a ^ b).count("1"))


# ------------------------------------------------------------------- движение
def motion_region(
    current: np.ndarray,
    reference: np.ndarray,
    *,
    diff_percentile: float = 98.0,
    morph_kernel: int = 5,
    min_area_frac: float = 0.004,
    max_area_frac: float = 0.45,
) -> MotionRegion | None:
    """Крупнейшая область, изменившаяся между кадрами."""
    if cv2 is None or current.shape[:2] != reference.shape[:2]:
        return None
    cur = to_gray(current).astype(np.int16)
    ref = to_gray(reference).astype(np.int16)
    diff = np.abs(cur - ref).astype(np.uint8)
    if float(diff.max()) < 8:
        return None
    threshold = max(10.0, float(np.percentile(diff, diff_percentile)) * 0.5)
    mask = (diff >= threshold).astype(np.uint8)
    k = max(3, int(morph_kernel) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    num, _labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num <= 1:
        return None
    areas = stats[1:, cv2.CC_STAT_AREA]
    order = np.argsort(areas)[::-1]
    best = int(order[0]) + 1
    total = float(mask.shape[0] * mask.shape[1])
    area = float(stats[best, cv2.CC_STAT_AREA])
    area_frac = area / total
    if area_frac < min_area_frac or area_frac > max_area_frac:
        return None
    x = int(stats[best, cv2.CC_STAT_LEFT])
    y = int(stats[best, cv2.CC_STAT_TOP])
    w = int(stats[best, cv2.CC_STAT_WIDTH])
    h = int(stats[best, cv2.CC_STAT_HEIGHT])
    box_area = float(max(1, w * h))
    fill = area / box_area
    second = float(areas[order[1]]) if order.size > 1 else 0.0
    dominance = area / max(area + second, 1e-6)
    aspect = min(w, h) / float(max(w, h, 1))
    confidence = float(np.clip(0.45 * fill + 0.4 * dominance + 0.15 * aspect, 0.0, 1.0))
    cx, cy = centroids[best]
    return MotionRegion(
        box=(x, y, x + w, y + h),
        centroid=(int(round(cx)), int(round(cy))),
        confidence=confidence,
        area_frac=area_frac,
    )


def global_motion_ratio(frames: Sequence[np.ndarray]) -> float:
    """Доля пикселей, меняющихся между соседними кадрами (высокая ⇒ камера движется)."""
    if len(frames) < 2:
        return 0.0
    ratios: list[float] = []
    for prev, cur in zip(frames[:-1], frames[1:]):
        if prev.shape[:2] != cur.shape[:2]:
            continue
        diff = np.abs(to_gray(cur).astype(np.int16) - to_gray(prev).astype(np.int16))
        ratios.append(float((diff > 16).mean()))
    return float(np.median(ratios)) if ratios else 0.0


# ------------------------------------------------------------ пространственное
def grid_cell(x: float, y: float, width: int, height: int) -> str:
    col = GRID_COLS[min(2, max(0, int(3 * x / max(width, 1))))]
    row = GRID_ROWS[min(2, max(0, int(3 * y / max(height, 1))))]
    if row == "middle" and col == "center":
        return "center"
    return f"{row}-{col}" if col != "center" else f"{row}-center"


def horizontal_half(x: float, width: int) -> str:
    return "left" if x < width / 2 else "right"


def vertical_half(y: float, height: int) -> str:
    return "upper" if y < height / 2 else "lower"


def relation_between(a: tuple[int, int], b: tuple[int, int], *, tolerance: int = 12) -> str:
    """Отношение точки a к точке b в системе координат изображения."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    if abs(dx) <= tolerance and abs(dy) <= tolerance:
        return "at the same place as"
    if abs(dx) >= abs(dy):
        return "to the right of" if dx > 0 else "to the left of"
    return "below" if dy > 0 else "above"


def direction_word(dx: float, dy: float, *, tolerance: float = 4.0) -> str:
    """Направление смещения в кадре (для описаний «что изменилось»)."""
    horizontal = "right" if dx > tolerance else "left" if dx < -tolerance else ""
    vertical = "down" if dy > tolerance else "up" if dy < -tolerance else ""
    if horizontal and vertical:
        return f"{vertical} and to the {horizontal}"
    if horizontal:
        return f"to the {horizontal}"
    if vertical:
        return vertical
    return "barely"
