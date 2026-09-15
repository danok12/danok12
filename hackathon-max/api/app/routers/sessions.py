"""Анкета ученика: создание сессии, выбор направлений, расчёт, решение."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Path

from .. import cards, db
from ..catalog import get_catalog
from ..config import get_settings
from ..engine import match_profiles
from ..schemas import Decision, MatchRequest, SessionCreate, SessionCreated, SessionPatch
from ..security import TokenError, issue_token, read_token

router = APIRouter(prefix="/api", tags=["Анкета ученика"])


def _fail(status: int, error: str, message: str, hint: str | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": error, "message": message, "hint": hint})


def _auth(session_id: str, authorization: str | None, roles: tuple[str, ...] = ("student",)) -> dict:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise _fail(401, "no_token", "Не передан токен доступа.", "Откройте мини-приложение из чат-бота заново.")
    try:
        payload = read_token(token)
    except TokenError as exc:
        raise _fail(401, "bad_token", f"Токен недействителен: {exc}.", "Вернитесь в чат-бота и откройте подбор заново.")
    if payload["sid"] != session_id:
        raise _fail(403, "foreign_session", "Токен выдан для другой анкеты.")
    if payload.get("role") not in roles:
        raise _fail(403, "wrong_role", "У этой роли нет доступа к операции.")
    return payload


def _class_or_404(class_code: str):
    found = get_catalog().find_class(class_code)
    if not found:
        raise _fail(404, "class_not_found", f"Код класса «{class_code}» не найден.",
                    "Демо-коды: 9A-114, 9B-114, 9A-ALM7.")
    return found


def _validate_fields(codes: list[str]) -> list[str]:
    cat, s = get_catalog(), get_settings()
    unknown = [c for c in codes if c not in cat.fields_by_code]
    if unknown:
        raise _fail(422, "unknown_field", "Неизвестные коды направлений: " + ", ".join(unknown),
                    "Список доступен в GET /api/catalog/fields.")
    uniq = list(dict.fromkeys(codes))
    if not uniq:
        raise _fail(422, "empty_selection", "Не выбрано ни одного направления.",
                    "Отметьте от 1 до %d направлений." % s.max_fields)
    if len(uniq) > s.max_fields:
        raise _fail(422, "too_many_fields", f"Выбрано {len(uniq)} направлений, максимум {s.max_fields}.",
                    "Оставьте самые важные — сравнение станет нагляднее.")
    return uniq


def _validate_subjects(ids: list[str]) -> list[str]:
    cat = get_catalog()
    unknown = [i for i in ids if i not in cat.subject_names]
    if unknown:
        raise _fail(422, "unknown_subject", "Неизвестные предметы: " + ", ".join(unknown))
    return list(dict.fromkeys(ids))


def _compute(class_code: str, field_codes: list[str], extra: list[str]) -> dict:
    cat = get_catalog()
    school_id, klass = _class_or_404(class_code)
    school = cat.schools[school_id]
    results = match_profiles(
        cat.profiles(school_id), cat.specs(field_codes), cat.subject_order, extra_subjects=extra
    )
    return {
        "school": {k: school[k] for k in ("id", "name", "city", "region")},
        "class": {"code": klass["code"], "title": klass["title"]},
        "admission": school["admission"],
        "selected_fields": field_codes,
        "extra_subjects": extra,
        "subjects": [
            {"id": i, "name": cat.subject_names[i], "short": cat.subject_short[i]} for i in cat.subject_order
        ],
        "profiles": results,
        "data": cat.data_versions(),
    }


@router.post("/sessions", response_model=SessionCreated, status_code=201, summary="Начать анкету")
def create_session(body: SessionCreate) -> dict:
    cat = get_catalog()
    school_id, klass = _class_or_404(body.class_code)
    row = db.create_or_get_session(body.max_user_id, body.chat_id, school_id, klass["code"])
    if body.chat_id and row["chat_id"] != body.chat_id:
        db.update_session(row["id"], chat_id=body.chat_id)
    school = cat.schools[school_id]
    token = issue_token(row["id"], "student")
    return {
        "session_id": row["id"],
        "token": token,
        "miniapp_url": f"{get_settings().public_base_url}/app/?t={token}",
        "school": {k: school[k] for k in ("id", "name", "city", "region")},
        "profiles": school["profiles"],
        "admission": school["admission"],
    }


@router.get("/sessions/{session_id}", summary="Состояние анкеты")
def read_session(session_id: str = Path(..., min_length=8), authorization: str | None = Header(None)) -> dict:
    _auth(session_id, authorization)
    row = db.get_session(session_id)
    if not row:
        raise _fail(404, "session_not_found", "Анкета не найдена.")
    cat = get_catalog()
    school = cat.schools[row["school_id"]]
    return {
        "session_id": row["id"],
        "class_code": row["class_code"],
        "initial_profile": row["initial_profile"],
        "selected_fields": json.loads(row["selected_fields"]),
        "extra_subjects": json.loads(row["extra_subjects"]),
        "chosen_profile": row["chosen_profile"],
        "school": {k: school[k] for k in ("id", "name", "city", "region")},
        "admission": school["admission"],
        "profiles": school["profiles"],
    }


@router.patch("/sessions/{session_id}", summary="Сохранить выбор ученика")
def patch_session(body: SessionPatch, session_id: str = Path(..., min_length=8),
                  authorization: str | None = Header(None)) -> dict:
    _auth(session_id, authorization)
    row = db.get_session(session_id)
    if not row:
        raise _fail(404, "session_not_found", "Анкета не найдена.")
    patch: dict = {}
    if body.selected_fields is not None:
        patch["selected_fields"] = _validate_fields(body.selected_fields)
    if body.extra_subjects is not None:
        patch["extra_subjects"] = _validate_subjects(body.extra_subjects)
    if body.initial_profile is not None:
        patch["initial_profile"] = body.initial_profile
    db.update_session(session_id, **patch)
    return {"ok": True, "updated": sorted(patch)}


@router.post("/sessions/{session_id}/match", summary="Рассчитать сравнение профилей")
def match_for_session(body: SessionPatch, session_id: str = Path(..., min_length=8),
                      authorization: str | None = Header(None)) -> dict:
    _auth(session_id, authorization)
    row = db.get_session(session_id)
    if not row:
        raise _fail(404, "session_not_found", "Анкета не найдена.")
    codes = _validate_fields(body.selected_fields if body.selected_fields is not None
                             else json.loads(row["selected_fields"]))
    extra = _validate_subjects(body.extra_subjects if body.extra_subjects is not None
                               else json.loads(row["extra_subjects"]))
    db.update_session(session_id, selected_fields=codes, extra_subjects=extra,
                      **({"initial_profile": body.initial_profile} if body.initial_profile else {}))
    result = _compute(row["class_code"], codes, extra)
    db.log_event(session_id, "match_computed", {"fields": len(codes), "extra": len(extra)})
    return result


@router.post("/match", summary="Расчёт без анкеты (для проверки и отладки)")
def match_stateless(body: MatchRequest) -> dict:
    codes = _validate_fields(body.fields)
    extra = _validate_subjects(body.extra_subjects)
    return _compute(body.class_code, codes, extra)


@router.post("/sessions/{session_id}/decision", summary="Зафиксировать профиль и получить карточку в чат")
def decide(body: Decision, session_id: str = Path(..., min_length=8),
           authorization: str | None = Header(None)) -> dict:
    _auth(session_id, authorization)
    row = db.get_session(session_id)
    if not row:
        raise _fail(404, "session_not_found", "Анкета не найдена.")
    codes = json.loads(row["selected_fields"])
    if not codes:
        raise _fail(409, "nothing_selected", "Сначала нужно выбрать направления и рассчитать сравнение.",
                    "Откройте подбор и отметьте направления.")
    result = _compute(row["class_code"], codes, json.loads(row["extra_subjects"]))
    chosen = next((p for p in result["profiles"] if p["profile_id"] == body.profile_id), None)
    if chosen is None:
        raise _fail(422, "unknown_profile", f"Профиль «{body.profile_id}» отсутствует в этой школе.",
                    "Допустимые: " + ", ".join(p["profile_id"] for p in result["profiles"]))

    db.update_session(session_id, chosen_profile=body.profile_id, finished_at=db.now())
    db.log_event(session_id, "decision_made", {
        "profile": body.profile_id,
        "initial_profile": row["initial_profile"],
        "changed_mind": bool(row["initial_profile"]) and row["initial_profile"] != body.profile_id,
    })

    chat_id = row["chat_id"] or row["max_user_id"]
    card = cards.decision_card(result, chosen, result["school"], result["admission"])
    db.push_outbox(chat_id, "decision_card", {"text": card, "session_id": session_id})

    reminder_at = None
    if body.remind:
        reminder_at = _schedule_reminder(chat_id, result, chosen["profile_name"])
    return {"ok": True, "card": card, "reminder_at": reminder_at,
            "chosen": {"profile_id": chosen["profile_id"], "available": chosen["available"],
                       "total": chosen["total"], "percent": chosen["percent"]}}


def _schedule_reminder(chat_id: str, result: dict, profile_name: str) -> str | None:
    """Напоминание о сроке подачи заявления. Повторный вызов заменяет прежнее."""
    s = get_settings()
    admission = result["admission"]
    db.cancel_outbox(chat_id, "reminder")
    if s.reminder_demo_delay > 0:
        due = datetime.now(timezone.utc) + timedelta(seconds=s.reminder_demo_delay)
    else:
        try:
            deadline = datetime.fromisoformat(admission["deadline"]).replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        due = deadline - timedelta(days=s.reminder_days_before)
        if due <= datetime.now(timezone.utc):
            return None
    text = cards.reminder_text(result["school"], admission, profile_name)
    db.push_outbox(chat_id, "reminder", {"text": text}, due_at=due.isoformat(timespec="seconds"))
    return due.isoformat(timespec="seconds")
