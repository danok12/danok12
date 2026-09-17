#!/usr/bin/env python3
"""Построение vision-language датасета (ShareGPT JSONL) из робототехнических эпизодов.

    python generate_dataset.py \
        --input /data/raw \
        --output /output/annotations.jsonl \
        --config config.yaml

Скрипт работает офлайн, не требует ручной разметки и при фиксированных входных
данных, конфиге и сиде даёт побитово одинаковый результат.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import Config  # noqa: E402
from src.pipeline import run  # noqa: E402
from src.utils import setup_logging  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Генератор vision-language датасета из робототехнических траекторий",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", required=True, type=Path, help="корень с исходными датасетами")
    parser.add_argument("--output", required=True, type=Path, help="путь к annotations.jsonl")
    parser.add_argument("--config", type=Path, default=None, help="YAML-конфигурация пайплайна")
    parser.add_argument("--seed", type=int, default=None, help="переопределить seed из конфига")
    parser.add_argument("--num-workers", type=int, default=None, help="число процессов (0 — авто)")
    parser.add_argument(
        "--limit-episodes",
        type=int,
        default=None,
        help="ограничить число эпизодов на источник (отладка)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="переопределить budget.max_samples",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="посчитать статистику без записи кадров и JSONL",
    )
    parser.add_argument("--log-level", default=None, help="DEBUG/INFO/WARNING/ERROR")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    overrides: dict = {}
    if args.seed is not None:
        overrides["seed"] = args.seed
    if args.max_samples is not None:
        overrides.setdefault("budget", {})["max_samples"] = args.max_samples
    if args.log_level:
        overrides.setdefault("runtime", {})["log_level"] = args.log_level

    config_path = args.config
    if config_path is None:
        default_config = Path(__file__).resolve().parent / "config.yaml"
        config_path = default_config if default_config.is_file() else None
    cfg = Config.load(config_path, overrides=overrides)
    setup_logging(str(cfg.get("runtime.log_level", "INFO")))

    stats = run(
        input_root=args.input,
        output=args.output,
        cfg=cfg,
        limit_episodes=args.limit_episodes,
        dry_run=args.dry_run,
        num_workers=args.num_workers,
    )
    summary = {
        "train": stats["train"]["total"],
        "val": stats["val"]["total"],
        "tasks": len(stats["train"]["by_task"]),
        "config_fingerprint": stats["config_fingerprint"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
