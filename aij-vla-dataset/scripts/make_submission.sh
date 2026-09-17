#!/usr/bin/env bash
# Сборка submission.zip в требуемой структуре.
#
#   ./scripts/make_submission.sh \
#       --annotations /output/annotations.jsonl \
#       --smolvlm2 runs/<run>/submission/smolvlm2 \
#       --action-expert runs/<run>/submission/action_expert \
#       --output submission.zip
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANNOTATIONS=""; SMOLVLM2=""; ACTION_EXPERT=""; OUTPUT="submission.zip"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --annotations) ANNOTATIONS="$2"; shift 2 ;;
        --smolvlm2) SMOLVLM2="$2"; shift 2 ;;
        --action-expert) ACTION_EXPERT="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
    esac
done

for var in ANNOTATIONS SMOLVLM2 ACTION_EXPERT; do
    if [[ -z "${!var}" ]]; then echo "не задан --${var,,}" >&2; exit 2; fi
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cp "$ROOT/README.md" "$ROOT/requirements.txt" "$ROOT/generate_dataset.py" "$ROOT/config.yaml" "$STAGE/"
cp -r "$ROOT/src" "$STAGE/src"
cp -r "$ROOT/scripts" "$STAGE/scripts"
cp -r "$ROOT/tests" "$STAGE/tests"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
cp "$ANNOTATIONS" "$STAGE/annotations.jsonl"
cp -r "$SMOLVLM2" "$STAGE/smolvlm2"
cp -r "$ACTION_EXPERT" "$STAGE/action_expert"

python3 "$ROOT/scripts/validate_annotations.py" --input "$STAGE/annotations.jsonl" --skip-images

for required in smolvlm2/config.json smolvlm2/model.safetensors action_expert/config.json \
                action_expert/model.safetensors; do
    if [[ ! -f "$STAGE/$required" ]]; then echo "ВНИМАНИЕ: отсутствует $required" >&2; fi
done

OUTPUT_ABS="$(cd "$(dirname "$OUTPUT")" && pwd)/$(basename "$OUTPUT")"
rm -f "$OUTPUT_ABS"
(cd "$STAGE" && zip -qr "$OUTPUT_ABS" .)
echo "собрано: $OUTPUT_ABS"
unzip -l "$OUTPUT_ABS" | tail -n 5
