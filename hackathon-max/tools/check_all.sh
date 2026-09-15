#!/usr/bin/env bash
# Полная проверка решения одной командой.
#
#   bash tools/check_all.sh
#
# Поднимает все локальные компоненты в Docker (вместе со стендом-эмулятором
# Bot API MAX), дожидается готовности и прогоняет три проверки:
#   1. тесты расчётного ядра и API;
#   2. обязательные проверки API из DATA-API.yaml;
#   3. сквозной сценарий через чат-бота.
#
# SKIP_DOCKER=1 — не запускать контейнеры (сервисы уже подняты).
# KEEP_UP=1     — не останавливать контейнеры после проверки.

set -uo pipefail
cd "$(dirname "$0")/.."

API="${API_BASE_URL:-http://localhost:8080}"
COMPOSE=(docker compose --env-file .env.demo --profile demo)
PY="${PYTHON:-python3}"
fail=0

step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
ok()   { printf '\033[32m  OK\033[0m  %s\n' "$1"; }
bad()  { printf '\033[31m  СБОЙ\033[0m %s\n' "$1"; fail=1; }

if [ "${SKIP_DOCKER:-0}" != "1" ]; then
  step "1/5 Запуск контейнеров"
  command -v docker >/dev/null || { bad "Docker не установлен. Поставьте Docker Desktop и повторите."; exit 1; }
  docker info >/dev/null 2>&1 || { bad "Docker установлен, но не запущен. Откройте Docker Desktop и повторите."; exit 1; }
  "${COMPOSE[@]}" up --build -d || { bad "Сборка или запуск не удались — смотрите вывод выше"; exit 1; }
  ok "контейнеры запущены"
else
  step "1/5 Запуск контейнеров пропущен (SKIP_DOCKER=1)"
fi

step "2/5 Ожидание готовности API"
for i in $(seq 1 60); do
  if curl -fsS "$API/api/health" >/dev/null 2>&1; then ok "API отвечает на $API"; break; fi
  [ "$i" = 60 ] && { bad "API не поднялся за 60 секунд. Логи: ${COMPOSE[*]} logs api"; exit 1; }
  sleep 1
done

step "3/5 Тесты расчётного ядра и API"
if $PY -m pytest tests -q; then ok "тесты пройдены"; else bad "тесты не пройдены"; fi

step "4/5 Обязательные проверки API из DATA-API.yaml"
if $PY tools/api_contract_check.py --base "$API"; then ok "контракт API соблюдён"; else bad "контракт API нарушен"; fi

step "5/5 Сквозной сценарий через чат-бота"
INTERNAL_KEY="${INTERNAL_KEY:-demo-only-not-a-secret-1111111111}" \
REMINDER_DEMO_DELAY="${REMINDER_DEMO_DELAY:-20}" \
MOCK_BASE_URL="${MOCK_BASE_URL:-http://localhost:8081}" \
  $PY tools/scenario_check.py && ok "сценарий проходится целиком" || bad "сценарий не прошёл"

if [ "${SKIP_DOCKER:-0}" != "1" ] && [ "${KEEP_UP:-0}" != "1" ]; then
  printf '\nОстанавливаю контейнеры (KEEP_UP=1 — оставить запущенными)\n'
  "${COMPOSE[@]}" down >/dev/null 2>&1
fi

if [ "$fail" = 0 ]; then
  printf '\n\033[32mВсё сошлось: решение работает.\033[0m\n'
else
  printf '\n\033[31mЕсть сбои — смотрите строки «СБОЙ» выше.\033[0m\n'
fi
exit "$fail"
