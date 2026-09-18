#!/usr/bin/env bash
# Полный цикл решения одной командой: данные -> датасет -> обучение -> архив.
#
# Запускать на машине с GPU и доступом к Hugging Face. Скрипт идемпотентен:
# каждая стадия пропускается, если её результат уже на месте (--force отключает).
#
#   ./src/tools/run_all.sh --participant /path/to/aij_robotics
#
# Основные параметры:
#   --participant PATH   распакованный participant.zip (обязательно)
#   --data-root PATH     куда качать исходные датасеты      (по умолчанию /data/raw)
#   --work PATH          куда класть датасет и логи          (по умолчанию /data/vlm)
#   --vla-dataset PATH   HuggingFaceVLA/libero @ v3.0        (по умолчанию /data/vla)
#   --run-name NAME      имя прогона обучения                (по умолчанию aij_run)
#   --stage NAME         data|dataset|train|package|all      (по умолчанию all)
#   --pilot N            пилот: N эпизодов на источник и частичная выгрузка данных
#   --force              переделать стадию, даже если результат уже есть
#   --dry-run            только показать команды
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARTICIPANT=""; DATA_ROOT="/data/raw"; WORK="/data/vlm"; VLA_DATASET="/data/vla"
RUN_NAME="aij_run"; STAGE="all"; PILOT=0; FORCE=0; DRY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --participant) PARTICIPANT="$2"; shift 2 ;;
        --data-root) DATA_ROOT="$2"; shift 2 ;;
        --work) WORK="$2"; shift 2 ;;
        --vla-dataset) VLA_DATASET="$2"; shift 2 ;;
        --run-name) RUN_NAME="$2"; shift 2 ;;
        --stage) STAGE="$2"; shift 2 ;;
        --pilot) PILOT="$2"; shift 2 ;;
        --force) FORCE=1; shift ;;
        --dry-run) DRY=1; shift ;;
        -h|--help) sed -n '2,25p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
    esac
done

LOG_DIR="$WORK/logs"
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
run() {
    if [[ "$DRY" == "1" ]]; then printf '   $ %s\n' "$*"; else "$@"; fi
}

# --------------------------------------------------------------- проверки
need() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    fi
    if [[ "$DRY" == "1" ]]; then
        note "(dry-run) нет команды $1 — $2"
        return 0
    fi
    echo "нет команды $1 — $2" >&2
    exit 3
}

if [[ "$STAGE" == "all" || "$STAGE" == "train" || "$STAGE" == "package" ]]; then
    if [[ -z "$PARTICIPANT" ]]; then
        echo "не задан --participant: путь к распакованному participant.zip" >&2
        exit 2
    fi
    [[ -f "$PARTICIPANT/scripts/run_pipeline.sh" ]] || {
        echo "в $PARTICIPANT нет scripts/run_pipeline.sh" >&2; exit 2; }
fi
need python3 "нужен Python 3.10+"
[[ "$DRY" == "1" ]] || mkdir -p "$LOG_DIR"

# ------------------------------------------------------------- 1. данные
#   репозиторий:коммит:каталог
DATASETS=(
    "nvidia/BridgeData2_LeRobot_v3:b96f7216e3cff58007884656a81584c857c185ae:BridgeData2_LeRobot_v3"
    "BrunoM42/fractal20220817_data_lerobot:fc006b5dc812220645a2e6dd0b68a0a03bd0ac6c:fractal20220817_data_lerobot"
    "tailong-wu/language_table_lerobot_v30:d54542e0eebf8084edb10e2c67ef5b94bd41fcc4:language_table_lerobot_v30"
    "builddotai/Egocentric-100K:fae604b751b25337d6fd8c4c53e595910c28f68f:Egocentric-100K"
)

stage_data() {
    say "1/4 Датасеты -> $DATA_ROOT"
    need huggingface-cli "установите: pip install huggingface_hub[cli]"
    run mkdir -p "$DATA_ROOT"
    for entry in "${DATASETS[@]}"; do
        IFS=':' read -r repo revision dirname <<< "$entry"
        local target="$DATA_ROOT/$dirname"
        if [[ -f "$target/meta/info.json" && "$FORCE" != "1" ]]; then
            note "$dirname уже скачан, пропускаю"
            continue
        fi
        note "$repo @ ${revision:0:8}"
        if [[ "$PILOT" -gt 0 && "$dirname" != "Egocentric-100K" ]]; then
            # Пилот: метаданные целиком плюс первые шарды данных и видео.
            run huggingface-cli download "$repo" --repo-type dataset --revision "$revision" \
                --local-dir "$target" \
                --include "meta/*" "data/chunk-000/file-000*" "data/chunk-000/file-001*" \
                          "videos/*/chunk-000/file-000*" "videos/*/chunk-000/file-001*"
        elif [[ "$PILOT" -gt 0 ]]; then
            run huggingface-cli download "$repo" --repo-type dataset --revision "$revision" \
                --local-dir "$target" --include "*.mp4" --max-workers 4
        else
            run huggingface-cli download "$repo" --repo-type dataset --revision "$revision" \
                --local-dir "$target"
        fi
    done
    note "занято: $(du -sh "$DATA_ROOT" 2>/dev/null | cut -f1 || echo '?')"
}

# ------------------------------------------------------------ 2. датасет
stage_dataset() {
    say "2/4 Датасет -> $WORK/train.jsonl"
    run python3 -m pip install --quiet -r "$ROOT/requirements.txt"
    if [[ "$FORCE" == "1" || ! -f "$WORK/train.jsonl" ]]; then
        note "самопроверка генератора"
        run bash "$ROOT/src/tools/run_smoke.sh" "$WORK/smoke"
        local args=(--input "$DATA_ROOT" --output "$WORK/train.jsonl" --config "$ROOT/config.yaml")
        [[ "$PILOT" -gt 0 ]] && args+=(--limit-episodes "$PILOT")
        if [[ "$PILOT" -gt 0 ]]; then
            note "генерация (пилот: $PILOT эпизодов на источник)"
        else
            note "генерация (полный прогон)"
        fi
        run python3 "$ROOT/generate_dataset.py" "${args[@]}"
    else
        note "$WORK/train.jsonl уже есть, пропускаю (--force чтобы пересобрать)"
    fi
    run python3 "$ROOT/src/tools/validate_annotations.py" --input "$WORK/train.jsonl"
    if [[ "$DRY" != "1" && -f "$WORK/train.stats.json" ]]; then
        python3 - "$WORK/train.stats.json" <<'PY'
import json, sys
stats = json.load(open(sys.argv[1]))
train = stats["train"]
print(f"   примеров: {train['total']}, типов заданий: {len(train['by_task'])}")
print(f"   по источникам: {train['by_source']}")
for name, info in (stats.get("sources") or {}).items():
    if info.get("kind") == "lerobot" and not info.get("gripper_calibrated"):
        print(f"   ВНИМАНИЕ: {name} — калибровка схвата не сошлась, "
              f"задания про схват для источника не строятся")
print(f"   время генерации: {stats.get('elapsed_sec')} c (лимит задачи — 12600 c)")
PY
    fi
}

# ----------------------------------------------------------- 3. обучение
stage_train() {
    say "3/4 Обучение VLM и action-эксперта"
    [[ -d "$VLA_DATASET/meta" ]] || note "ВНИМАНИЕ: в $VLA_DATASET нет meta/ — нужен HuggingFaceVLA/libero @ v3.0"
    local config="$PARTICIPANT/configs/participant_generated.yaml"
    if [[ "$DRY" == "1" ]]; then
        printf '   $ cat > %s <<EOF ... EOF\n' "$config"
    else
        cat > "$config" <<EOF
# Сгенерировано src/tools/run_all.sh
run_name: $RUN_NAME
vlm:
  data_path: $WORK/train.jsonl
  eval_data_path: $WORK/train.val.jsonl
  media_dir: $WORK
vla:
  suite: libero
  dataset_dir: $VLA_DATASET
runtime:
  gpu_indices: [0]
  output_root: $PARTICIPANT/runs
EOF
        note "конфиг: $config"
    fi
    note "запуск пайплайна участника (долго)"
    run bash -c "cd '$PARTICIPANT' && ./scripts/run_pipeline.sh configs/participant_generated.yaml 2>&1 | tee '$LOG_DIR/train.log'"
    note "проверка весов"
    run bash -c "cd '$PARTICIPANT' && ./scripts/validate_submission.sh runs/$RUN_NAME/submission"
    cat <<'TXT'

   Контрольная точка: прежде чем считать решение готовым, прогоните 8 VLM-бенчей
   на полученном smolvlm2/ и сравните с исходным SmolVLM2-500M-Video-Instruct.
   Если VLM просела — датасет вредит, и VLA-часть этого не компенсирует:
   правьте config.yaml (budget.max_samples, language.mcq_share, веса задач)
   и повторяйте со стадии dataset.

       ./scripts/setup_score_selfcheck.sh
       ./scripts/run_score_selfcheck.sh --submission runs/<run>/submission \
           --config configs/selfcheck_score.example.yaml
TXT
}

# -------------------------------------------------------------- 4. архив
stage_package() {
    say "4/4 Сборка submission.zip"
    local submission="$PARTICIPANT/runs/$RUN_NAME/submission"
    run bash "$ROOT/src/tools/make_submission.sh" \
        --annotations "$WORK/train.jsonl" \
        --smolvlm2 "$submission/smolvlm2" \
        --action-expert "$submission/action_expert" \
        --output "$WORK/submission.zip"
    cat <<TXT

   Осталось вручную:
   - загрузить $WORK/submission.zip на платформу (одна попытка в сутки);
   - до 20.10.2026 отметить 3 итоговых решения.
TXT
}

case "$STAGE" in
    data) stage_data ;;
    dataset) stage_dataset ;;
    train) stage_train ;;
    package) stage_package ;;
    all) stage_data; stage_dataset; stage_train; stage_package ;;
    *) echo "неизвестная стадия: $STAGE" >&2; exit 2 ;;
esac

say "готово"
