#!/usr/bin/env bash
# Развёртывание решения на чистом арендованном GPU-сервере (Ubuntu 22.04+).
#
# Один запуск ставит зависимости, распаковывает репозиторий участника,
# скачивает датасеты, строит обучающую выборку и — если окружение обучения
# готово — проводит обе стадии обучения и собирает submission.zip.
#
#   ./bootstrap_cloud.sh --participant-zip ~/participant.zip
#
#   --participant-zip PATH|URL   архив participant.zip (обязательно)
#   --root PATH                  рабочий каталог           (по умолчанию /data)
#   --pilot N                    пилот: N эпизодов и частичная выгрузка данных
#   --preset single-gpu|default  конфиг генератора         (по умолчанию default)
#   --skip-train                 только данные и датасет, без обучения
set -euo pipefail

PARTICIPANT_ZIP=""; ROOT="/data"; PILOT=0; PRESET="default"; SKIP_TRAIN=0
REPO_URL="https://github.com/danok12/danok12.git"
REPO_BRANCH="claude/hopeful-gauss-kni4i7"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --participant-zip) PARTICIPANT_ZIP="$2"; shift 2 ;;
        --root) ROOT="$2"; shift 2 ;;
        --pilot) PILOT="$2"; shift 2 ;;
        --preset) PRESET="$2"; shift 2 ;;
        --skip-train) SKIP_TRAIN=1; shift ;;
        --repo) REPO_URL="$2"; shift 2 ;;
        --branch) REPO_BRANCH="$2"; shift 2 ;;
        -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
    esac
done

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }

if [[ -z "$PARTICIPANT_ZIP" ]]; then
    echo "не задан --participant-zip: архив участника нельзя скачать автоматически," >&2
    echo "его нужно взять с платформы конкурса и положить на сервер." >&2
    exit 2
fi

SUDO=""
[[ "$(id -u)" -ne 0 ]] && SUDO="sudo"

say "1/6 Системные пакеты"
$SUDO apt-get update -qq
$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    git unzip tmux curl python3-venv python3-pip ffmpeg
note "ок"

say "2/6 Видеокарта"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | sed 's/^/   /'
else
    note "ВНИМАНИЕ: nvidia-smi не найден — обучение работать не будет"
fi

say "3/6 Код решения и репозиторий участника"
mkdir -p "$ROOT"
if [[ ! -d "$ROOT/solution" ]]; then
    git clone --quiet --branch "$REPO_BRANCH" "$REPO_URL" "$ROOT/repo"
    cp -r "$ROOT/repo/aij-vla-dataset" "$ROOT/solution"
else
    note "$ROOT/solution уже есть"
fi

if [[ ! -d "$ROOT/aij_robotics" ]]; then
    if [[ "$PARTICIPANT_ZIP" =~ ^https?:// ]]; then
        curl -fsSL "$PARTICIPANT_ZIP" -o "$ROOT/participant.zip"
        PARTICIPANT_ZIP="$ROOT/participant.zip"
    fi
    unzip -q "$PARTICIPANT_ZIP" -d "$ROOT/tmp_participant"
    # архив распаковывается в каталог вида aij_robotics-main
    inner="$(find "$ROOT/tmp_participant" -maxdepth 1 -mindepth 1 -type d | head -1)"
    mv "$inner" "$ROOT/aij_robotics"
    rm -rf "$ROOT/tmp_participant"
    chmod +x "$ROOT/aij_robotics/scripts/"*.sh 2>/dev/null || true
fi
note "решение: $ROOT/solution, участник: $ROOT/aij_robotics"

say "4/6 Python-окружение"
python3 -m venv "$ROOT/venv"
# shellcheck disable=SC1091
source "$ROOT/venv/bin/activate"
pip install --quiet -U pip
pip install --quiet -r "$ROOT/solution/requirements.txt" "huggingface_hub[cli]"
python -c "import numpy, pyarrow, cv2, av, yaml, PIL" && note "зависимости на месте"

say "5/6 Самопроверка генератора"
bash "$ROOT/solution/src/tools/run_smoke.sh" "$ROOT/smoke" >/dev/null
note "генератор работает, результат воспроизводим"

say "6/6 Данные, датасет и обучение"
CONFIG="$ROOT/solution/config.yaml"
[[ "$PRESET" == "single-gpu" ]] && CONFIG="$ROOT/solution/src/presets/config.single-gpu.yaml"
ARGS=(--data-root "$ROOT/raw" --work "$ROOT/vlm" --vla-dataset "$ROOT/vla" --participant "$ROOT/aij_robotics")
[[ "$PILOT" -gt 0 ]] && ARGS+=(--pilot "$PILOT")

cd "$ROOT/solution"
if [[ "$SKIP_TRAIN" == "1" ]]; then
    ./src/tools/run_all.sh --stage data "${ARGS[@]}"
    ./src/tools/run_all.sh --stage dataset "${ARGS[@]}"
    cat <<TXT

   Данные и датасет готовы: $ROOT/vlm/train.jsonl
   Обучение запускается отдельно:
       cd $ROOT/solution && ./src/tools/run_all.sh --stage train --stage package ${ARGS[*]}
TXT
else
    ./src/tools/run_all.sh --stage all "${ARGS[@]}"
    cat <<TXT

   Готово. Архив решения: $ROOT/vlm/submission.zip
   Забрать к себе:  scp $(whoami)@<адрес_сервера>:$ROOT/vlm/submission.zip .
TXT
fi
