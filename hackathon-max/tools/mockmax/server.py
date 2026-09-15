"""СТЕНД для локальной проверки — эмулятор Bot API MAX.

Это НЕ часть продукта и НЕ имитация интеграции в презентационном смысле:
стенд нужен только для того, чтобы сквозной сценарий чат-бота можно было
прогнать без доступа к платформе (в закрытом контуре, в CI, на ревью).
В рабочем контуре бот ходит в настоящий https://botapi.max.ru по токену,
выданному организатором; переключение — переменной MAX_API_BASE.

Реализовано ровно то, что вызывает bot/bot/max_api.py:
  GET  /me        GET  /updates    POST /messages    POST /answers
плюс служебные /sim/* для подачи действий пользователя и чтения ответов.
"""

from __future__ import annotations

import itertools
import threading
import time
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Стенд-эмулятор MAX Bot API", version="1.0.0")

_lock = threading.Lock()
_seq = itertools.count(1)
_updates: list[dict] = []      # очередь обновлений для бота
_delivered = 0                 # сколько обновлений уже отдано (marker)
_messages: list[dict] = []     # что бот отправил в чаты
TOKEN_REQUIRED = "demo-token"


def _need_token(token: str | None) -> JSONResponse | None:
    if token != TOKEN_REQUIRED:
        return JSONResponse(status_code=401, content={"code": "verify.token", "message": "invalid access_token"})
    return None


def _push(update: dict) -> dict:
    with _lock:
        update["timestamp"] = int(time.time() * 1000)
        _updates.append(update)
    return update


# --- методы, которые вызывает бот ---------------------------------------
@app.get("/me")
def me(access_token: str | None = None):
    if err := _need_token(access_token):
        return err
    return {"user_id": 777, "name": "Профиль 10 (стенд)", "username": "profil10_stand", "is_bot": True}


@app.get("/updates")
def updates(access_token: str | None = None, marker: int | None = None,
            timeout: int = Query(30, ge=0, le=90), limit: int = 50):
    if err := _need_token(access_token):
        return err
    deadline = time.time() + min(timeout, 5)   # на стенде не ждём по 30 секунд
    while True:
        with _lock:
            # После /sim/reset очередь пуста, а у бота остаётся прежний marker.
            # Ограничиваем позицию длиной очереди, иначе бот «ослепнет».
            start = min(marker, len(_updates)) if marker is not None else 0
            batch = _updates[start:start + limit]
            if batch:
                return {"updates": batch, "marker": start + len(batch)}
        if time.time() >= deadline:
            with _lock:
                return {"updates": [], "marker": marker if marker is not None else len(_updates)}
        time.sleep(0.1)


@app.post("/messages")
async def messages(request: Request, access_token: str | None = None, chat_id: str | None = None):
    if err := _need_token(access_token):
        return err
    body: dict[str, Any] = await request.json()
    with _lock:
        _messages.append({"seq": next(_seq), "chat_id": str(chat_id), "text": body.get("text", ""),
                          "attachments": body.get("attachments", []), "via": "messages"})
    return {"message": {"body": {"mid": f"mid{len(_messages)}", "text": body.get("text", "")}}}


@app.post("/answers")
async def answers(request: Request, access_token: str | None = None, callback_id: str | None = None):
    if err := _need_token(access_token):
        return err
    body: dict[str, Any] = await request.json()
    msg = body.get("message") or {}
    chat_id = (callback_id or "").split(":", 1)[0]
    with _lock:
        _messages.append({"seq": next(_seq), "chat_id": chat_id, "text": msg.get("text", ""),
                          "attachments": msg.get("attachments", []), "via": "answers"})
    return {"success": True}


# --- управление стендом --------------------------------------------------
@app.post("/sim/start")
def sim_start(body: dict):
    return _push({"update_type": "bot_started", "chat_id": body["chat_id"],
                  "user": {"user_id": body["user_id"]}})


@app.post("/sim/text")
def sim_text(body: dict):
    return _push({"update_type": "message_created", "message": {
        "sender": {"user_id": body["user_id"]},
        "recipient": {"chat_id": body["chat_id"], "chat_type": "dialog"},
        "body": {"mid": f"in{len(_updates)}", "seq": len(_updates), "text": body["text"]}}})


@app.post("/sim/callback")
def sim_callback(body: dict):
    return _push({"update_type": "message_callback",
                  "callback": {"callback_id": f"{body['chat_id']}:cb{len(_updates)}",
                               "payload": body["payload"], "user": {"user_id": body["user_id"]}},
                  "message": {"recipient": {"chat_id": body["chat_id"], "chat_type": "dialog"}}})


@app.get("/sim/messages")
def sim_messages(chat_id: str | None = None, after: int = 0):
    with _lock:
        items = [m for m in _messages if (chat_id is None or m["chat_id"] == str(chat_id)) and m["seq"] > after]
    return {"items": items}


@app.post("/sim/reset")
def sim_reset(with_updates: bool = False):
    """Очистить отправленные сообщения.

    Очередь обновлений по умолчанию НЕ трогаем: бот хранит позицию чтения
    (marker), и обнуление очереди под ним заставило бы его пропускать
    сообщения. Очистка очереди осмысленна только вместе с перезапуском бота.
    """
    with _lock:
        _messages.clear()
        if with_updates:
            _updates.clear()
    return {"ok": True, "updates_cleared": with_updates}
