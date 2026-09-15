"""Роль школы: обезличенный агрегат по классу и подсказка по элективам.

Персональные данные не раскрываются: агрегат отдаётся только при наличии
не менее MIN_AGGREGATE заполненных анкет (k-анонимность), в ответе нет
идентификаторов пользователей MAX.
"""

from __future__ import annotations

import json
from collections import Counter

from fastapi import APIRouter, Header, HTTPException, Path
from pydantic import BaseModel, Field

from .. import db
from ..catalog import get_catalog
from ..config import get_settings
from ..engine import school_gap_report
from ..security import TokenError, issue_token, read_token

router = APIRouter(prefix="/api/school", tags=["Роль школы"])


class CuratorAuth(BaseModel):
    curator_code: str = Field(..., min_length=3, max_length=48)


def _fail(status: int, error: str, message: str, hint: str | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": error, "message": message, "hint": hint})


@router.post("/auth", summary="Вход куратора по коду")
def curator_auth(body: CuratorAuth) -> dict:
    found = get_catalog().find_curator(body.curator_code)
    if not found:
        raise _fail(401, "bad_curator_code", "Код куратора не распознан.",
                    "Демо-коды: KUR-114-9A, KUR-114-9B, KUR-ALM7-9A.")
    school_id, klass = found
    school = get_catalog().schools[school_id]
    return {
        "token": issue_token(f"class:{klass['code']}", "curator", ttl=8 * 3600),
        "class": {"code": klass["code"], "title": klass["title"]},
        "school": {k: school[k] for k in ("id", "name", "city", "region")},
    }


def _auth_curator(class_code: str, authorization: str | None) -> None:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise _fail(401, "no_token", "Нужен токен куратора.", "Войдите по коду куратора.")
    try:
        payload = read_token(token)
    except TokenError as exc:
        raise _fail(401, "bad_token", f"Токен недействителен: {exc}.")
    if payload.get("role") != "curator" or payload.get("sid") != f"class:{class_code.upper()}":
        raise _fail(403, "wrong_class", "Токен выдан для другого класса.")


@router.get("/{class_code}/analytics", summary="Обезличенный агрегат по классу")
def analytics(class_code: str = Path(..., min_length=3, max_length=32),
              authorization: str | None = Header(None)) -> dict:
    cat, s = get_catalog(), get_settings()
    found = cat.find_class(class_code)
    if not found:
        raise _fail(404, "class_not_found", f"Код класса «{class_code}» не найден.")
    _auth_curator(class_code, authorization)
    school_id, klass = found

    rows = db.sessions_of_class(klass["code"])
    filled = [r for r in rows if json.loads(r["selected_fields"])]
    base = {
        "class": {"code": klass["code"], "title": klass["title"]},
        "school": {k: cat.schools[school_id][k] for k in ("id", "name", "city", "region")},
        "started": len(rows),
        "filled": len(filled),
        "k_anonymity_threshold": s.min_aggregate,
        "privacy_note": (
            "Агрегат обезличен: идентификаторы пользователей MAX не выдаются. "
            f"Разрезы показываются, если заполненных анкет не меньше {s.min_aggregate}."
        ),
    }
    if len(filled) < s.min_aggregate:
        base["status"] = "insufficient_data"
        base["message"] = (
            f"Заполнено анкет: {len(filled)}. Разрезы откроются с {s.min_aggregate} — "
            "так по агрегату нельзя узнать ответ конкретного ученика."
        )
        return base

    demand = Counter()
    for r in filled:
        demand.update(json.loads(r["selected_fields"]))
    chosen = Counter(r["chosen_profile"] for r in filled if r["chosen_profile"])
    changed = sum(
        1 for r in filled
        if r["initial_profile"] and r["chosen_profile"] and r["initial_profile"] != r["chosen_profile"]
    )
    with_initial = sum(1 for r in filled if r["initial_profile"] and r["chosen_profile"])

    report = school_gap_report(cat.profiles(school_id), cat.fields_by_code, dict(demand), cat.subject_order)
    profiles = {p["id"]: p["name"] for p in cat.schools[school_id]["profiles"]}
    base.update({
        "status": "ok",
        "completed": sum(1 for r in filled if r["chosen_profile"]),
        "top_fields": [
            {"code": c, "name": cat.fields_by_code[c].name, "students": n}
            for c, n in demand.most_common(10)
        ],
        "profile_demand": [
            {"profile_id": pid, "name": profiles.get(pid, pid), "students": n} for pid, n in chosen.most_common()
        ],
        "changed_mind": {"count": changed, "of": with_initial},
        "uncovered_fields": report["uncovered"],
        "best_elective": (
            {**report["best_elective"], "subject_name": cat.subject_names[report["best_elective"]["subject"]]}
            if report["best_elective"] else None
        ),
    })
    return base
