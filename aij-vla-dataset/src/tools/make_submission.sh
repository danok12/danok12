#!/usr/bin/env bash
# Сборка submission.zip в структуре, заданной организатором:
#
#   submission.zip
#   ├── README.md
#   ├── requirements.txt
#   ├── generate_dataset.py
#   ├── config.yaml
#   ├── annotations.jsonl
#   ├── src/            (весь исходный код, включая src/tools и src/tests)
#   ├── smolvlm2/       (чекпойнт дообученной VLM)
#   └── action_expert/  (чекпойнт action-эксперта)
#
#   ./src/tools/make_submission.sh \
#       --annotations /output/annotations.jsonl \
#       --smolvlm2 runs/<run>/submission/smolvlm2 \
#       --action-expert runs/<run>/submission/action_expert \
#       --output submission.zip
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ANNOTATIONS=""; SMOLVLM2=""; ACTION_EXPERT=""; OUTPUT="submission.zip"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --annotations) ANNOTATIONS="$2"; shift 2 ;;
        --smolvlm2) SMOLVLM2="$2"; shift 2 ;;
        --action-expert) ACTION_EXPERT="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
    esac
done

for name in ANNOTATIONS SMOLVLM2 ACTION_EXPERT; do
    if [[ -z "${!name}" ]]; then
        echo "не задан --${name,,}" >&2
        exit 2
    fi
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cp "$ROOT/README.md" "$ROOT/requirements.txt" "$ROOT/generate_dataset.py" "$ROOT/config.yaml" "$STAGE/"
cp -r "$ROOT/src" "$STAGE/src"
cp "$ANNOTATIONS" "$STAGE/annotations.jsonl"
cp -r "$SMOLVLM2" "$STAGE/smolvlm2"
cp -r "$ACTION_EXPERT" "$STAGE/action_expert"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '.pytest_cache' -type d -prune -exec rm -rf {} +

python3 "$ROOT/src/tools/validate_annotations.py" --input "$STAGE/annotations.jsonl" --skip-images

# Файлы, без которых архив не примут (см. описание задачи).
MISSING=0
for required in smolvlm2/config.json smolvlm2/model.safetensors smolvlm2/generation_config.json \
                smolvlm2/processor_config.json smolvlm2/tokenizer_config.json smolvlm2/tokenizer.json \
                smolvlm2/chat_template.jinja action_expert/config.json action_expert/model.safetensors \
                action_expert/train_config.json action_expert/policy_preprocessor.json \
                action_expert/policy_postprocessor.json; do
    if [[ ! -f "$STAGE/$required" ]]; then
        echo "ВНИМАНИЕ: в архиве нет $required" >&2
        MISSING=$((MISSING + 1))
    fi
done
for pattern in 'action_expert/policy_preprocessor_step_*.safetensors' 'action_expert/policy_postprocessor_step_*.safetensors'; do
    # shellcheck disable=SC2086
    if ! compgen -G "$STAGE/$pattern" >/dev/null; then
        echo "ВНИМАНИЕ: в архиве нет $pattern" >&2
        MISSING=$((MISSING + 1))
    fi
done

OUTPUT_ABS="$(cd "$(dirname "$OUTPUT")" && pwd)/$(basename "$OUTPUT")"
rm -f "$OUTPUT_ABS"
# Явный список вместо "zip -r .": в корне архива должны лежать ровно эти элементы.
(cd "$STAGE" && zip -qr "$OUTPUT_ABS" \
    README.md requirements.txt generate_dataset.py config.yaml annotations.jsonl \
    src smolvlm2 action_expert)

echo
echo "собрано: $OUTPUT_ABS ($(du -h "$OUTPUT_ABS" | cut -f1))"
echo "корень архива:"
unzip -l "$OUTPUT_ABS" | awk 'NR>3 && $4 !~ /\// {print "  " $4} NR>3 && $4 ~ /^[^\/]+\// {split($4,a,"/"); print "  " a[1] "/"}' | sort -u | head -20
if [[ "$MISSING" -gt 0 ]]; then
    echo "предупреждений о недостающих файлах: $MISSING" >&2
fi
