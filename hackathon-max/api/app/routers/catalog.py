"""Справочники: предметы, направления подготовки, класс/школа."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path

from ..catalog import get_catalog

router = APIRouter(prefix="/api", tags=["Справочники"])


@router.get("/meta", summary="Версии и происхождение данных")
def meta() -> dict:
    cat = get_catalog()
    return {
        "product": "Профиль 10",
        "data": cat.data_versions(),
        "disclaimer": (
            "Справочник вступительных испытаний и данные школ в MVP — демонстрационные. "
            "Результат расчёта носит информационный характер и не заменяет правила приёма "
            "конкретного вуза и решение школы."
        ),
    }


@router.get("/catalog/subjects", summary="Предметы ЕГЭ")
def subjects() -> dict:
    cat = get_catalog()
    return {"version": cat.subjects_raw["version"], "items": cat.subjects_raw["items"]}


@router.get("/catalog/fields", summary="Направления подготовки (УГСН)")
def fields() -> dict:
    cat = get_catalog()
    return {
        "version": cat.fields_raw["version"],
        "updated_at": cat.fields_raw["updated_at"],
        "source_note": cat.fields_raw["source_note"],
        "groups": cat.groups,
        "items": cat.fields_raw["items"],
    }


@router.get("/classes/{class_code}", summary="Школа и профили по коду класса")
def school_by_class(class_code: str = Path(..., min_length=3, max_length=32)) -> dict:
    cat = get_catalog()
    found = cat.find_class(class_code)
    if not found:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "class_not_found",
                "message": f"Код класса «{class_code}» не найден.",
                "hint": "Проверьте код у классного руководителя. Демо-коды: 9A-114, 9B-114, 9A-ALM7.",
            },
        )
    school_id, klass = found
    school = cat.schools[school_id]
    return {
        "class": {"code": klass["code"], "title": klass["title"]},
        "school": {k: school[k] for k in ("id", "name", "city", "region")},
        "admission": school["admission"],
        "profiles": school["profiles"],
    }
