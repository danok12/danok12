"""Служебный контур: очередь исходящих сообщений для бота.

Бот не открывает входящий порт — он забирает задания из очереди и
подтверждает доставку. Так API остаётся единственным владельцем состояния,
а перезапуск бота не теряет сообщения.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Header, HTTPException

from .. import db
from ..config import get_settings

router = APIRouter(prefix="/api/internal", tags=["Служебное (бот -> API)"], include_in_schema=False)


def _auth(key: str | None) -> None:
    expected = get_settings().internal_key
    if not key or key != expected:
        raise HTTPException(status_code=401, detail={"error": "bad_internal_key",
                                                     "message": "Неверный служебный ключ."})


@router.get("/outbox")
def take_outbox(limit: int = 20, x_internal_key: str | None = Header(None)) -> dict:
    _auth(x_internal_key)
    items = db.pending_outbox(limit)
    return {"items": [
        {"id": i["id"], "chat_id": i["chat_id"], "kind": i["kind"], "payload": json.loads(i["payload"])}
        for i in items
    ]}


@router.post("/outbox/{item_id}/ack")
def ack(item_id: int, ok: bool = True, x_internal_key: str | None = Header(None)) -> dict:
    _auth(x_internal_key)
    db.ack_outbox(item_id, ok)
    return {"ok": True}


@router.post("/events")
def track(body: dict, x_internal_key: str | None = Header(None)) -> dict:
    """Бот сообщает о своих событиях (старт диалога, нажатия) для метрик пилота."""
    _auth(x_internal_key)
    db.log_event(body.get("session_id"), str(body.get("type", "bot_event"))[:64], body.get("payload") or {})
    return {"ok": True}


@router.get("/sessions/by-user/{max_user_id}")
def session_by_user(max_user_id: str, x_internal_key: str | None = Header(None)) -> dict:
    """Последняя анкета пользователя — чтобы бот восстанавливал диалог после перезапуска."""
    _auth(x_internal_key)
    row = db.connect().execute(
        "SELECT * FROM sessions WHERE max_user_id=? ORDER BY updated_at DESC LIMIT 1", (max_user_id,)
    ).fetchone()
    if not row:
        return {"found": False}
    return {
        "found": True,
        "session_id": row["id"],
        "class_code": row["class_code"],
        "school_id": row["school_id"],
        "initial_profile": row["initial_profile"],
        "selected_fields": json.loads(row["selected_fields"]),
        "chosen_profile": row["chosen_profile"],
    }


@router.post("/reminders/cancel")
def cancel_reminder(body: dict, x_internal_key: str | None = Header(None)) -> dict:
    """Отключить ещё не отправленное напоминание (пользователь нажал «не напоминать»)."""
    _auth(x_internal_key)
    removed = db.cancel_outbox(str(body.get("chat_id", "")), "reminder")
    return {"ok": True, "removed": removed}
