"""Тесты расчётного ядра.

Ожидаемые значения посчитаны вручную по справочникам data/ и зафиксированы
здесь: любое изменение данных или логики, меняющее выдачу пользователю,
роняет тест.
"""

import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.catalog import get_catalog                      # noqa: E402
from app.engine import (                                 # noqa: E402
    FULL, NONE, PARTIAL, coverage, evaluate_field, match_profiles,
    percent, profile_subjects, school_gap_report,
)

CAT = get_catalog()
SUBJ_ORDER = CAT.subject_order
# Набор интересов демо-ученика: IT, экономика, право, медицина, языки
SELECTION = ["09.00.00", "38.00.00", "40.00.00", "31.00.00", "45.00.00"]


def test_profile_subjects_always_includes_russian():
    prof = [p for p in CAT.profiles("kzn-114") if p.id == "hum"][0]
    assert profile_subjects(prof) == {"rus", "hist", "soc", "lit", "lang"}


def test_statuses_for_technological_profile():
    tech = [p for p in CAT.profiles("kzn-114") if p.id == "tech"][0]
    s = profile_subjects(tech)                      # {rus, math, phys, inf}
    by = {c: evaluate_field(CAT.fields_by_code[c], s) for c in SELECTION}

    assert by["09.00.00"].status == PARTIAL         # закрыты inf и phys, но не chem
    assert by["38.00.00"].status == PARTIAL         # из choice закрыта только inf
    assert by["40.00.00"].status == NONE            # нет обществознания
    assert by["40.00.00"].gap_required == ["soc"]
    assert by["40.00.00"].gap_options == []         # inf из choice уже есть
    assert by["31.00.00"].status == NONE            # нет химии и биологии
    assert by["31.00.00"].gap_required == ["chem", "bio"]
    assert by["45.00.00"].gap_required == ["lang"]
    assert by["45.00.00"].gap_options == ["lit", "hist", "soc"]


def test_full_coverage_when_every_option_closed():
    hum = [p for p in CAT.profiles("kzn-114") if p.id == "hum"][0]
    s = profile_subjects(hum)
    # 45.00.00: обязательны rus+lang, из choice закрыты lit, hist и soc -> все вузы
    assert evaluate_field(CAT.fields_by_code["45.00.00"], s).status == FULL
    # 31.00.00 без choice: обязательны rus+chem+bio
    assert evaluate_field(CAT.fields_by_code["31.00.00"], s).status == NONE


def test_exact_fraction_and_percent():
    share, available, total, full = coverage(
        [evaluate_field(CAT.fields_by_code[c],
                        profile_subjects([p for p in CAT.profiles("kzn-114") if p.id == "tech"][0]))
         for c in SELECTION]
    )
    assert (available, total, full) == (2, 5, 0)
    assert share == Fraction(2, 5)
    assert percent(share) == 40.0
    # округление, а не усечение: 5/6 -> 83.3, 2/3 -> 66.7
    assert percent(Fraction(5, 6)) == 83.3
    assert percent(Fraction(2, 3)) == 66.7


def test_ranking_and_shape():
    res = match_profiles(CAT.profiles("kzn-114"), CAT.specs(SELECTION), SUBJ_ORDER)
    assert [r["profile_id"] for r in res] == ["nat", "hum", "tech", "soc", "uni"]
    assert [(r["available"], r["full"]) for r in res] == [(2, 1), (2, 1), (2, 0), (1, 0), (0, 0)]
    assert [r["percent"] for r in res] == [40.0, 40.0, 40.0, 20.0, 0.0]
    assert [r["fraction"] for r in res] == ["2/5", "2/5", "2/5", "1/5", "0/1"]
    assert all(len(r["fields"]) == len(SELECTION) for r in res)


def test_advice_finds_minimal_addition():
    res = match_profiles(CAT.profiles("kzn-114"), CAT.specs(SELECTION), SUBJ_ORDER)
    tech = [r for r in res if r["profile_id"] == "tech"][0]
    # одного обществознания хватает только для юриспруденции; пара soc+lang
    # возвращает ещё и языкознание -> выигрыш 2 из 3 закрытых
    assert tech["advice"]["add"] == ["soc", "lang"]
    assert tech["advice"]["gain"] == 2
    assert tech["advice"]["becomes_available"] == ["40.00.00", "45.00.00"]
    assert tech["advice"]["elective_in_school"] is False   # у технологического электив только химия


def test_extra_subjects_recompute():
    base = match_profiles(CAT.profiles("kzn-114"), CAT.specs(SELECTION), SUBJ_ORDER)
    with_soc = match_profiles(CAT.profiles("kzn-114"), CAT.specs(SELECTION), SUBJ_ORDER,
                              extra_subjects=["soc"])
    tech_before = [r for r in base if r["profile_id"] == "tech"][0]["available"]
    tech_after = [r for r in with_soc if r["profile_id"] == "tech"][0]["available"]
    assert (tech_before, tech_after) == (2, 3)


def test_universal_profile_closes_everything_but_needs_one_subject():
    res = match_profiles(CAT.profiles("kzn-114"), CAT.specs(SELECTION), SUBJ_ORDER)
    uni = [r for r in res if r["profile_id"] == "uni"][0]
    assert uni["available"] == 0
    # универсальный профиль: один предмет возвращает сразу два направления
    assert uni["advice"]["gain"] >= 2


def test_school_gap_report():
    profiles = CAT.profiles("alm-7")          # только технологический и универсальный
    demand = {"31.00.00": 6, "40.00.00": 4, "09.00.00": 9}
    rep = school_gap_report(profiles, CAT.fields_by_code, demand, SUBJ_ORDER)
    codes = [u["code"] for u in rep["uncovered"]]
    assert codes == ["31.00.00", "40.00.00"]   # ИВТ закрыт технологическим
    assert rep["uncovered"][0]["students"] == 6
    best = rep["best_elective"]
    # Обществознание в ТЕХНОЛОГИЧЕСКОМ профиле возвращает юриспруденцию (4 ученика):
    # обязательные рус+общ закрыты, а из списка вуза уже закрыта информатика.
    # В универсальном профиле то же обществознание юриспруденцию не открывает —
    # там не закрыт ни один предмет из списка вуза (ист/ин.яз/инф).
    # Клиническая медицина требует сразу химию и биологию и одним элективом
    # не закрывается ни в одном профиле школы.
    assert (best["profile_id"], best["subject"]) == ("tech", "soc")
    assert (best["affected_students"], best["returns_fields"]) == (4, ["40.00.00"])
    assert best["elective_in_school"] is False   # такого электива в школе пока нет
