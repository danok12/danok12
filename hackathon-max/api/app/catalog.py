"""Загрузка демонстрационных справочников из каталога data/."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from .engine import FieldSpec, ProfileSpec

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


class Catalog:
    """Справочники предметов, направлений подготовки и школ.

    Загружаются один раз при старте: это статические демо-данные, в пилоте
    источник заменяется на выгрузку из информационной системы.
    """

    def __init__(self) -> None:
        self.subjects_raw = _load("subjects.json")
        self.fields_raw = _load("fields.json")
        self.schools_raw = _load("schools.json")

        self.subject_order: list[str] = [s["id"] for s in self.subjects_raw["items"]]
        self.subject_names: dict[str, str] = {s["id"]: s["name"] for s in self.subjects_raw["items"]}
        self.subject_short: dict[str, str] = {s["id"]: s["short"] for s in self.subjects_raw["items"]}

        self.fields: list[FieldSpec] = [FieldSpec.from_dict(f) for f in self.fields_raw["items"]]
        self.fields_by_code: dict[str, FieldSpec] = {f.code: f for f in self.fields}
        self.groups: list[dict] = self.fields_raw["groups"]

        self.schools: dict[str, dict] = {s["id"]: s for s in self.schools_raw["schools"]}
        self.class_index: dict[str, tuple[str, dict]] = {}
        self.curator_index: dict[str, tuple[str, dict]] = {}
        for school in self.schools_raw["schools"]:
            for klass in school["classes"]:
                self.class_index[klass["code"].upper()] = (school["id"], klass)
                self.curator_index[klass["curator_code"].upper()] = (school["id"], klass)

    # --- доступ ---------------------------------------------------------
    def profiles(self, school_id: str) -> list[ProfileSpec]:
        return [ProfileSpec.from_dict(p) for p in self.schools[school_id]["profiles"]]

    def find_class(self, code: str) -> tuple[str, dict] | None:
        return self.class_index.get((code or "").strip().upper())

    def find_curator(self, code: str) -> tuple[str, dict] | None:
        return self.curator_index.get((code or "").strip().upper())

    def specs(self, codes: list[str]) -> list[FieldSpec]:
        """Направления по кодам, в порядке справочника (устойчивый вывод)."""
        wanted = set(codes)
        return [f for f in self.fields if f.code in wanted]

    def data_versions(self) -> dict:
        return {
            "subjects": self.subjects_raw["version"],
            "fields": self.fields_raw["version"],
            "fields_updated_at": self.fields_raw["updated_at"],
            "fields_source": self.fields_raw["source_note"],
            "schools": self.schools_raw["version"],
            "demo_data": True,
        }


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return Catalog()
