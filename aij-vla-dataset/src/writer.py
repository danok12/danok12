"""Отбор, балансировка и запись итогового ShareGPT JSONL."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .config import Config
from .records import Sample
from .utils import get_logger, stable_hash, write_json

LOGGER = get_logger(__name__)


@dataclass
class SplitPaths:
    train: Path
    val: Path | None
    meta: Path | None
    stats: Path
    manifest: Path


def resolve_paths(output: Path, cfg: Config) -> SplitPaths:
    output = Path(output)
    stem = output.stem
    parent = output.parent
    val = parent / f"{stem}.val.jsonl" if float(cfg.get("output.val_fraction", 0.0)) > 0 else None
    meta = parent / f"{stem}.meta.jsonl" if bool(cfg.get("output.write_meta", True)) else None
    return SplitPaths(
        train=output,
        val=val,
        meta=meta,
        stats=parent / f"{stem}.stats.json",
        manifest=parent / f"{stem}.manifest.json",
    )


def deduplicate(samples: Iterable[Sample]) -> list[Sample]:
    seen: set[int] = set()
    out: list[Sample] = []
    for sample in samples:
        key = stable_hash(sample.user, sample.assistant, "|".join(sample.images))
        if key in seen:
            continue
        seen.add(key)
        out.append(sample)
    return out


def _waterfill(counts: dict[str, int], weights: dict[str, float], target: int) -> dict[str, int]:
    """Квоты по задачам: пропорционально весам, с перераспределением недобора."""
    caps: dict[str, int] = {}
    remaining = {t for t in counts if counts[t] > 0 and weights.get(t, 0.0) > 0}
    for task in counts:
        if task not in remaining:
            caps[task] = 0
    budget = int(target)
    while remaining and budget > 0:
        weight_sum = sum(weights[t] for t in remaining)
        if weight_sum <= 0:
            break
        saturated = []
        for task in sorted(remaining):
            share = int(round(budget * weights[task] / weight_sum))
            if counts[task] <= share:
                caps[task] = counts[task]
                saturated.append(task)
        if not saturated:
            for task in sorted(remaining):
                caps[task] = int(round(budget * weights[task] / weight_sum))
            break
        for task in saturated:
            remaining.discard(task)
            budget -= caps[task]
    for task in counts:
        caps.setdefault(task, 0)
    return caps


def balance(samples: Sequence[Sample], cfg: Config) -> tuple[list[Sample], dict[str, Any]]:
    """Приведение долей задач к весам конфига и ограничение доминирования шаблонов."""
    counts = Counter(s.task for s in samples)
    weights = {task: max(0.0, cfg.task_weight(task)) for task in counts}
    max_samples = int(cfg.get("budget.max_samples", 0) or 0)
    target = min(len(samples), max_samples) if max_samples > 0 else len(samples)
    caps = _waterfill(dict(counts), weights, target)

    template_share = float(cfg.get("language.max_share_per_template", 0.04))
    min_cap = int(cfg.get("language.min_template_cap", 25))
    template_cap = max(min_cap, int(template_share * max(target, 1))) if template_share > 0 else None

    ordered = sorted(samples, key=lambda s: stable_hash(cfg.seed, "select", s.task, s.user, "|".join(s.images)))
    taken: Counter[str] = Counter()
    per_template: Counter[str] = Counter()
    kept: list[Sample] = []
    dropped_template = 0
    for sample in ordered:
        if taken[sample.task] >= caps.get(sample.task, 0):
            continue
        if template_cap is not None and per_template[sample.template] >= template_cap:
            dropped_template += 1
            continue
        kept.append(sample)
        taken[sample.task] += 1
        per_template[sample.template] += 1

    report = {
        "collected": len(samples),
        "selected": len(kept),
        "target": target,
        "caps": dict(sorted(caps.items())),
        "dropped_by_template_cap": dropped_template,
        "template_cap": template_cap,
    }
    return kept, report


def split_train_val(samples: Sequence[Sample], cfg: Config) -> tuple[list[Sample], list[Sample]]:
    fraction = float(cfg.get("output.val_fraction", 0.0))
    if fraction <= 0:
        return list(samples), []
    by_episode = str(cfg.get("output.split_by", "episode")) == "episode"
    threshold = int(fraction * 10000)
    train: list[Sample] = []
    val: list[Sample] = []
    for sample in samples:
        key = sample.meta.get("episode", "") if by_episode else sample.user
        bucket = stable_hash(cfg.seed, "split", key) % 10000
        (val if bucket < threshold else train).append(sample)
    return train, val


def shuffle(samples: Sequence[Sample], cfg: Config) -> list[Sample]:
    if not bool(cfg.get("output.shuffle", True)):
        return list(samples)
    return sorted(samples, key=lambda s: stable_hash(cfg.seed, "shuffle", s.task, s.user, "|".join(s.images)))


def build_stats(train: Sequence[Sample], val: Sequence[Sample], cfg: Config, extra: dict[str, Any]) -> dict[str, Any]:
    def describe(items: Sequence[Sample]) -> dict[str, Any]:
        by_task = Counter(s.task for s in items)
        by_format = Counter(s.meta.get("format", "open") for s in items)
        by_source = Counter(str(s.meta.get("episode", "")).split("/")[0] for s in items)
        letters = Counter(
            s.meta.get("answer_letter", "?") for s in items if s.meta.get("format") == "mcq"
        )
        # Позиция верного ответа равномерна внутри групп с одинаковым числом
        # вариантов; общая гистограмма всегда смещена к первым буквам, потому что
        # в вопросах с тремя вариантами буквы D просто нет.
        by_options: dict[str, Counter[str]] = {}
        for sample in items:
            if sample.meta.get("format") != "mcq":
                continue
            group = str(sample.meta.get("answer_options", "?"))
            by_options.setdefault(group, Counter())[sample.meta.get("answer_letter", "?")] += 1
        images = Counter(len(s.images) for s in items)
        total = max(1, len(items))
        return {
            "total": len(items),
            "by_task": dict(sorted(by_task.items())),
            "task_share": {k: round(v / total, 4) for k, v in sorted(by_task.items())},
            "by_format": dict(sorted(by_format.items())),
            "by_source": dict(sorted(by_source.items())),
            "mcq_answer_letters": dict(sorted(letters.items())),
            "mcq_letters_by_options": {
                key: dict(sorted(value.items())) for key, value in sorted(by_options.items())
            },
            "images_per_sample": dict(sorted(images.items())),
            "unique_templates": len({s.template for s in items}),
            "unique_answers": len({s.assistant for s in items}),
        }

    return {
        "train": describe(train),
        "val": describe(val),
        "config_fingerprint": cfg.fingerprint,
        "seed": cfg.seed,
        **extra,
    }


def write_jsonl(path: Path, samples: Sequence[Sample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample.to_sharegpt(), ensure_ascii=False) + "\n")
    tmp.replace(path)


def write_meta(path: Path, samples: Sequence[Sample], split: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if path.exists() and split != "train" else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for index, sample in enumerate(samples):
            payload = {
                "split": split,
                "index": index,
                "task": sample.task,
                "template": sample.template,
                "images": sample.images,
                **sample.meta,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def prune_unused_frames(samples: Sequence[Sample], output: Path, cfg: Config) -> int:
    """Удаление кадров, не попавших в итоговый датасет после балансировки."""
    frames_dir = output.parent / str(cfg.get("output.frames_dirname", "images"))
    if not frames_dir.is_dir():
        return 0
    referenced: set[Path] = set()
    for sample in samples:
        for image in sample.images:
            path = Path(image)
            if not path.is_absolute():
                path = output.parent / path
            referenced.add(path.resolve())
    removed = 0
    for path in frames_dir.rglob("*"):
        if path.is_file() and path.resolve() not in referenced:
            path.unlink()
            removed += 1
    for path in sorted(frames_dir.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    if removed:
        LOGGER.info("удалено неиспользованных кадров: %d", removed)
    return removed


def write_outputs(
    samples: Sequence[Sample],
    output: Path,
    cfg: Config,
    extra: dict[str, Any],
) -> dict[str, Any]:
    paths = resolve_paths(output, cfg)
    if bool(cfg.get("output.prune_unused_frames", True)):
        extra = {**extra, "frames_pruned": prune_unused_frames(samples, output, cfg)}
    train, val = split_train_val(samples, cfg)
    train = shuffle(train, cfg)
    val = shuffle(val, cfg)

    write_jsonl(paths.train, train)
    if paths.val is not None:
        write_jsonl(paths.val, val)
    if paths.meta is not None:
        write_meta(paths.meta, train, "train")
        if val:
            write_meta(paths.meta, val, "val")

    stats = build_stats(train, val, cfg, extra)
    write_json(paths.stats, stats)
    manifest = {
        "generator": "aij-vla-dataset",
        "config_fingerprint": cfg.fingerprint,
        "seed": cfg.seed,
        "outputs": {
            "train": str(paths.train),
            "val": str(paths.val) if paths.val else None,
            "meta": str(paths.meta) if paths.meta else None,
            "stats": str(paths.stats),
        },
        "config": cfg.to_dict(),
        **extra,
    }
    write_json(paths.manifest, manifest)
    LOGGER.info("записано train=%d val=%d -> %s", len(train), len(val), paths.train)
    return stats
