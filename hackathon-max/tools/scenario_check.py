#!/usr/bin/env python3
"""Сквозная проверка основного сценария «Профиль 10».

Прогоняет путь целиком: вход в чат-бота -> код класса -> исходный профиль ->
запуск мини-приложения -> выбор направлений -> расчёт -> карточка в чат ->
напоминание -> агрегат для школы. Каждый шаг проверяется утверждением.

Запуск (сервисы уже подняты через docker compose --profile demo):
    python3 tools/scenario_check.py

Переменные окружения:
    API_BASE_URL   адрес API           (по умолчанию http://localhost:8080)
    MOCK_BASE_URL  адрес стенда MAX    (по умолчанию http://localhost:8081)
    APP_SECRET / INTERNAL_KEY — как у сервисов.
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import requests

API = os.getenv("API_BASE_URL", "http://localhost:8080").rstrip("/")
MOCK = os.getenv("MOCK_BASE_URL", "http://localhost:8081").rstrip("/")
INTERNAL = os.getenv("INTERNAL_KEY", "devinternal")
CLASS = os.getenv("DEMO_CLASS", "9A-114")
CURATOR = os.getenv("DEMO_CURATOR", "KUR-114-9A")
SELECTION = ["09.00.00", "38.00.00", "40.00.00", "31.00.00", "45.00.00"]

passed = failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}" + (f"\n      {detail}" if detail else ""))


def wait_message(chat_id: str, after: int, contains: str = "", tries: int = 20) -> dict | None:
    """Ждём ответ бота в чате: опрос идёт асинхронно."""
    for _ in range(tries):
        items = requests.get(f"{MOCK}/sim/messages", params={"chat_id": chat_id, "after": after},
                             timeout=10).json()["items"]
        for m in items:
            if not contains or contains.lower() in m["text"].lower():
                return m
        time.sleep(1)
    return None


def last_seq() -> int:
    items = requests.get(f"{MOCK}/sim/messages", timeout=10).json()["items"]
    return items[-1]["seq"] if items else 0


def main() -> int:
    user = f"u{uuid.uuid4().hex[:8]}"
    chat = f"c{uuid.uuid4().hex[:8]}"
    print(f"\nСквозная проверка сценария. Пользователь {user}, чат {chat}\n")

    print("1. Сервисы отвечают")
    health = requests.get(f"{API}/api/health", timeout=10).json()
    check("API готов", health.get("status") == "ok", str(health))
    check("справочник направлений загружен", health.get("fields", 0) >= 30, str(health))
    check("стенд MAX отвечает", requests.get(f"{MOCK}/me", params={"access_token": "demo-token"},
                                             timeout=10).status_code == 200)

    print("\n2. Вход в чат-бота")
    mark = last_seq()
    requests.post(f"{MOCK}/sim/start", json={"user_id": user, "chat_id": chat}, timeout=10)
    msg = wait_message(chat, mark, "профиль 10")
    check("бот поздоровался и попросил код класса", msg is not None and "код класса" in msg["text"].lower(),
          (msg or {}).get("text", "ответа нет"))

    print("\n3. Неизвестный ввод не ломает диалог")
    mark = last_seq()
    requests.post(f"{MOCK}/sim/text", json={"user_id": user, "chat_id": chat, "text": "ааа"}, timeout=10)
    msg = wait_message(chat, mark)
    check("бот подсказал, что делать", msg is not None and "код класса" in msg["text"].lower(),
          (msg or {}).get("text", "ответа нет"))

    print("\n4. Код класса")
    mark = last_seq()
    requests.post(f"{MOCK}/sim/text", json={"user_id": user, "chat_id": chat, "text": CLASS}, timeout=10)
    msg = wait_message(chat, mark, "профили вашей школы")
    check("бот показал школу, срок и профили", msg is not None, (msg or {}).get("text", "ответа нет"))
    buttons = [b for att in (msg or {}).get("attachments", []) for row in att["payload"]["buttons"] for b in row]
    check("предложен выбор исходного профиля", any(b.get("payload", "").startswith("init:") for b in buttons))

    print("\n5. Запуск мини-приложения")
    mark = last_seq()
    requests.post(f"{MOCK}/sim/callback", json={"user_id": user, "chat_id": chat, "payload": "init:tech"},
                  timeout=10)
    msg = wait_message(chat, mark, "направления")
    buttons = [b for att in (msg or {}).get("attachments", []) for row in att["payload"]["buttons"] for b in row]
    link = next((b.get("url", "") for b in buttons if "/app/?t=" in b.get("url", "")), "")
    check("бот дал кнопку запуска мини-приложения", bool(link), str(buttons))
    if not link:
        return 1
    token = link.split("/app/?t=", 1)[1]
    sid = requests.get(f"{API}/api/internal/sessions/by-user/{user}",
                       headers={"x-internal-key": INTERNAL}, timeout=10).json()["session_id"]
    check("анкета создана и исходный профиль записан",
          requests.get(f"{API}/api/sessions/{sid}", headers={"authorization": f"Bearer {token}"},
                       timeout=10).json()["initial_profile"] == "tech")

    print("\n6. Расчёт в мини-приложении")
    res = requests.post(f"{API}/api/sessions/{sid}/match", headers={"authorization": f"Bearer {token}"},
                        json={"selected_fields": SELECTION}, timeout=10).json()
    profiles = res["profiles"]
    check("рассчитаны все профили школы", len(profiles) == 5, str(len(profiles)))
    check("результат отсортирован по покрытию",
          [p["available"] for p in profiles] == sorted((p["available"] for p in profiles), reverse=True),
          str([(p["profile_id"], p["available"]) for p in profiles]))
    tech = next(p for p in profiles if p["profile_id"] == "tech")
    check("технологический закрывает 2 из 5 (40.0%)",
          (tech["available"], tech["total"], tech["percent"]) == (2, 5, 40.0), str(tech["percent"]))
    check("показано, чего не хватает для закрытых направлений",
          all(f["gap_required"] or f["gap_options"] for f in tech["fields"] if f["status"] == "none"))
    check("есть подсказка, что добрать", tech["advice"]["add"] == ["soc", "lang"], str(tech["advice"]))
    check("происхождение данных помечено как демонстрационное", res["data"]["demo_data"] is True)

    print("\n7. Пересчёт с добранным предметом")
    res2 = requests.post(f"{API}/api/sessions/{sid}/match", headers={"authorization": f"Bearer {token}"},
                         json={"selected_fields": SELECTION, "extra_subjects": ["soc", "lang"]},
                         timeout=10).json()
    tech2 = next(p for p in res2["profiles"] if p["profile_id"] == "tech")
    check("добор двух предметов вернул направления", tech2["available"] == 4, str(tech2["available"]))

    print("\n8. Карточка решения приходит в чат")
    mark = last_seq()
    dec = requests.post(f"{API}/api/sessions/{sid}/decision", headers={"authorization": f"Bearer {token}"},
                        json={"profile_id": "tech", "remind": True}, timeout=10).json()
    check("напоминание о сроке поставлено", bool(dec.get("reminder_at")), str(dec))
    card = wait_message(chat, mark, "ваш разбор профилей")
    check("бот доставил карточку в чат", card is not None)
    if card:
        text = card["text"]
        check("в карточке есть выбранный профиль", "Технологический" in text)
        check("в карточке есть закрывающиеся направления", "Закрываются при этом профиле" in text)
        check("в карточке есть срок подачи заявления", "Срок подачи заявления" in text)
        check("в карточке есть оговорка о характере расчёта", "информационный" in text)

    print("\n9. Ошибки обрабатываются предсказуемо")
    r = requests.post(f"{API}/api/sessions/{sid}/match", headers={"authorization": "Bearer ZmFrZQ.ZmFrZQ"},
                      json={"selected_fields": SELECTION}, timeout=10)
    check("подделанный токен отклонён (401)", r.status_code == 401, str(r.status_code))
    r = requests.post(f"{API}/api/sessions/{sid}/decision", headers={"authorization": f"Bearer {token}"},
                      json={"profile_id": "нет-такого"}, timeout=10)
    check("неизвестный профиль отклонён (422)", r.status_code == 422, str(r.status_code))
    r = requests.get(f"{API}/api/classes/НЕТ", timeout=10)
    check("неизвестный код класса отклонён (404) с подсказкой",
          r.status_code == 404 and "hint" in r.json()["detail"], r.text[:120])
    r = requests.get(f"{API}/api/internal/outbox", timeout=10)
    check("служебный контур закрыт без ключа (401)", r.status_code == 401, str(r.status_code))

    print("\n10. Сценарий повторяется без перезапуска")
    mark = last_seq()
    requests.post(f"{MOCK}/sim/callback", json={"user_id": user, "chat_id": chat, "payload": "menu:open"},
                  timeout=10)
    check("бот снова открывает подбор", wait_message(chat, mark, "направления") is not None)

    print("\n11. Агрегат для школы: k-анонимность")
    auth = requests.post(f"{API}/api/school/auth", json={"curator_code": CURATOR}, timeout=10)
    check("вход куратора по коду", auth.status_code == 200, auth.text[:120])
    ctoken = auth.json()["token"]
    r = requests.get(f"{API}/api/school/{CLASS}/analytics", headers={"authorization": f"Bearer {ctoken}"},
                     timeout=10).json()
    check("порог k-анонимности объявлен", r["k_anonymity_threshold"] >= 5, str(r.get("k_anonymity_threshold")))
    if r["status"] == "insufficient_data":
        print("      (анкет меньше порога — добавляю демо-анкеты)")
        for i in range(r["k_anonymity_threshold"] - r["filled"]):
            s = requests.post(f"{API}/api/sessions", json={"max_user_id": f"{user}-peer{i}",
                                                           "chat_id": f"{chat}-peer{i}",
                                                           "class_code": CLASS}, timeout=10).json()
            requests.post(f"{API}/api/sessions/{s['session_id']}/match",
                          headers={"authorization": f"Bearer {s['token']}"},
                          json={"selected_fields": SELECTION[:3], "initial_profile": "uni"}, timeout=10)
            requests.post(f"{API}/api/sessions/{s['session_id']}/decision",
                          headers={"authorization": f"Bearer {s['token']}"},
                          json={"profile_id": "soc", "remind": False}, timeout=10)
        r = requests.get(f"{API}/api/school/{CLASS}/analytics",
                         headers={"authorization": f"Bearer {ctoken}"}, timeout=10).json()
    check("агрегат открылся после порога", r["status"] == "ok", str(r.get("message")))
    check("в агрегате нет идентификаторов пользователей", "max_user_id" not in str(r))
    check("посчитан спрос по направлениям", bool(r.get("top_fields")), str(r.get("top_fields"))[:120])
    check("посчитана доля изменивших выбор", "changed_mind" in r, str(r.get("changed_mind")))
    r2 = requests.get(f"{API}/api/school/{CLASS}/analytics", timeout=10)
    check("агрегат закрыт без токена куратора (401)", r2.status_code == 401, str(r2.status_code))

    delay = int(os.getenv("REMINDER_DEMO_DELAY", "0"))
    if delay and delay <= 60:
        print(f"\n12. Напоминание о сроке (демо-режим, {delay} с)")
        rem = wait_message(chat, mark, "напоминание", tries=delay + 20)
        check("напоминание доставлено в чат", rem is not None, "не пришло")

    print(f"\nИтог: успешно {passed}, неуспешно {failed}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
