"""Мелкие утилиты: детерминированные seed'ы, хеши, безопасный ввод-вывод."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Iterator, Sequence, TypeVar

T = TypeVar("T")

LOGGER_NAME = "aij_vla_dataset"


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, str(level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def stable_hash(*parts: Any) -> int:
    """Детерминированный 64-битный хеш (в отличие от hash() не зависит от PYTHONHASHSEED)."""
    blob = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(blob, digest_size=8).digest(), "big")


def rng_for(seed: int, *parts: Any) -> random.Random:
    """RNG, зависящий только от seed и ключа — порядок обработки эпизодов не влияет."""
    return random.Random(stable_hash(seed, *parts))


def config_fingerprint(config: Any) -> str:
    blob = json.dumps(config, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def chunked(items: Sequence[T], size: int) -> Iterator[list[T]]:
    size = max(1, int(size))
    for start in range(0, len(items), size):
        yield list(items[start : start + size])
