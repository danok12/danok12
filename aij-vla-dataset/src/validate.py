"""Проверка итогового ShareGPT JSONL: структура, изображения, статистика."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROLES = ("user", "assistant")


@dataclass
class Report:
    path: Path
    lines: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    images_total: int = 0
    images_missing: int = 0
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        head = f"{self.path}: строк {self.lines}, изображений {self.images_total}"
        body = [head]
        if self.stats:
            body.append("  " + json.dumps(self.stats, ensure_ascii=False))
        for item in self.warnings[:20]:
            body.append(f"  ! {item}")
        for item in self.errors[:20]:
            body.append(f"  ✗ {item}")
        if len(self.errors) > 20:
            body.append(f"  ... и ещё {len(self.errors) - 20} ошибок")
        body.append("  ✓ формат корректен" if self.ok else "  ✗ есть ошибки")
        return "\n".join(body)


def validate_file(path: Path, *, media_dir: Path | None = None, check_images: bool = True) -> Report:
    path = Path(path)
    media_dir = media_dir or path.parent
    report = Report(path=path)
    lengths: Counter[int] = Counter()
    seen: set[str] = set()

    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            report.lines += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                report.errors.append(f"строка {number}: не JSON ({exc})")
                continue
            messages = row.get("messages")
            images = row.get("images") or []
            if not isinstance(messages, list) or len(messages) < 2:
                report.errors.append(f"строка {number}: messages должен быть списком из >= 2 реплик")
                continue
            if messages[0].get("role") != "user" or messages[-1].get("role") != "assistant":
                report.errors.append(f"строка {number}: диалог должен начинаться с user и кончаться assistant")
            for message in messages:
                if message.get("role") not in ROLES:
                    report.errors.append(f"строка {number}: недопустимая роль {message.get('role')!r}")
                if not str(message.get("content", "")).strip():
                    report.errors.append(f"строка {number}: пустое сообщение")
            placeholders = sum(str(m.get("content", "")).count("<image>") for m in messages)
            if placeholders != len(images):
                report.errors.append(
                    f"строка {number}: <image> x{placeholders}, а в images {len(images)} путей"
                )
            report.images_total += len(images)
            lengths[len(images)] += 1
            fingerprint = json.dumps(row, sort_keys=True, ensure_ascii=False)
            if fingerprint in seen:
                report.warnings.append(f"строка {number}: полный дубликат примера")
            seen.add(fingerprint)
            if check_images:
                for image in images:
                    candidate = Path(image)
                    if not candidate.is_absolute():
                        candidate = media_dir / candidate
                    if not candidate.is_file():
                        report.images_missing += 1
                        if report.images_missing <= 5:
                            report.errors.append(f"строка {number}: нет файла {candidate}")

    report.stats = {
        "images_per_sample": dict(sorted(lengths.items())),
        "images_missing": report.images_missing,
        "unique_samples": len(seen),
    }
    return report
