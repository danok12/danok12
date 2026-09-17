#!/usr/bin/env python3
"""Проверка annotations.jsonl перед отправкой решения.

    python scripts/validate_annotations.py --input /output/annotations.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.validate import validate_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, nargs="+")
    parser.add_argument("--media-dir", type=Path, default=None)
    parser.add_argument("--skip-images", action="store_true", help="не проверять наличие файлов")
    args = parser.parse_args()

    ok = True
    for path in args.input:
        report = validate_file(path, media_dir=args.media_dir, check_images=not args.skip_images)
        print(report.render())
        ok = ok and report.ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
