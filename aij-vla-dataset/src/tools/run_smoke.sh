#!/usr/bin/env bash
# Полная самопроверка без внешних данных: синтетический эпизод -> датасет -> валидация.
#
#   ./src/tools/run_smoke.sh [рабочий_каталог]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${1:-${TMPDIR:-/tmp}/aij-vla-smoke}"
RAW="$WORK/raw"
OUT="$WORK/out"

rm -rf "$WORK"
mkdir -p "$RAW" "$OUT"

echo "[1/4] синтетический LeRobot v3 фикстур -> $RAW/robot_demo"
python3 "$ROOT/src/tests/make_fixture.py" --output "$RAW/robot_demo" --episodes 6 --length 48

echo "[2/4] генерация датасета"
python3 "$ROOT/generate_dataset.py" \
    --input "$RAW" \
    --output "$OUT/annotations.jsonl" \
    --config "$ROOT/config.yaml"

echo "[3/4] валидация формата ShareGPT"
python3 "$ROOT/src/tools/validate_annotations.py" --input "$OUT/annotations.jsonl"

echo "[4/4] проверка воспроизводимости (1 воркер против 4)"
python3 "$ROOT/generate_dataset.py" --input "$RAW" --output "$OUT/repeat/annotations.jsonl" \
    --config "$ROOT/config.yaml" --num-workers 4 >/dev/null
if cmp -s "$OUT/annotations.jsonl" "$OUT/repeat/annotations.jsonl"; then
    echo "OK: результат побитово совпадает"
else
    echo "FAIL: прогоны разошлись" >&2
    exit 1
fi

echo "готово: $OUT"
