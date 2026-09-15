"""Расчётное ядро «Профиль 10».

Отвечает на один вопрос: какие направления подготовки останутся доступны
ученику, если он выберет тот или иной профиль обучения в 10 классе.

Модель:
  * профиль задаёт набор предметов, изучаемых углублённо (`advanced`);
  * школьник гарантированно может сдать ЕГЭ по русскому языку и по предметам
    профиля (модельное допущение, см. ASSUMPTION ниже);
  * направление подготовки требует набор `required` (все предметы) плюс один
    предмет из `choice` (его выбирает вуз в правилах приёма).

ASSUMPTION (явное допущение продукта, показывается пользователю):
    формально ученик вправе сдавать ЕГЭ по любому предмету независимо от
    профиля. Модель считает предмет «закрытым», если он не изучается
    углублённо и не добран элективом/самостоятельно. Пользователь может
    добавить предметы вручную (`extra_subjects`) и пересчитать.

Вся арифметика долей — точная (fractions.Fraction); проценты округляются
через round(), а не усечением.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from fractions import Fraction
from typing import Iterable, Sequence

# Статусы доступности направления при выбранном профиле
FULL = "full"        # закрыты все варианты испытаний -> доступны все вузы направления
PARTIAL = "partial"  # закрыт хотя бы один вариант -> доступна часть вузов
NONE = "none"        # не закрыт ни один вариант -> направление недоступно

AVAILABLE = (FULL, PARTIAL)


@dataclass(frozen=True)
class FieldSpec:
    """Направление подготовки (укрупнённая группа) и его вступительные испытания."""

    code: str
    name: str
    group: str
    required: tuple[str, ...]
    choice: tuple[str, ...]
    extra_exam: str | None = None

    @staticmethod
    def from_dict(d: dict) -> "FieldSpec":
        return FieldSpec(
            code=d["code"],
            name=d["name"],
            group=d.get("group", ""),
            required=tuple(d.get("required", ())),
            choice=tuple(d.get("choice", ())),
            extra_exam=d.get("extra_exam"),
        )


@dataclass(frozen=True)
class ProfileSpec:
    """Профиль обучения конкретной школы."""

    id: str
    name: str
    advanced: tuple[str, ...]
    electives: tuple[str, ...] = ()
    seats: int | None = None

    @staticmethod
    def from_dict(d: dict) -> "ProfileSpec":
        return ProfileSpec(
            id=d["id"],
            name=d["name"],
            advanced=tuple(d.get("advanced", ())),
            electives=tuple(d.get("electives", ())),
            seats=d.get("seats"),
        )


@dataclass
class FieldResult:
    code: str
    name: str
    status: str
    gap_required: list[str] = dc_field(default_factory=list)   # предметы, которых не хватает (нужны все)
    gap_options: list[str] = dc_field(default_factory=list)    # достаточно одного из них
    extra_exam: str | None = None

    @property
    def available(self) -> bool:
        return self.status in AVAILABLE


def profile_subjects(profile: ProfileSpec, extra: Iterable[str] = ()) -> set[str]:
    """Предметы, по которым ученик сможет сдать ЕГЭ при данном профиле.

    Русский язык добавляется всегда: он обязателен для аттестата и входит
    в каждый набор вступительных испытаний.
    """
    return {"rus", *profile.advanced, *extra}


def evaluate_field(spec: FieldSpec, subjects: set[str]) -> FieldResult:
    """Статус одного направления при данном наборе предметов."""
    missing_required = [s for s in spec.required if s not in subjects]
    if spec.choice:
        have_choice = [s for s in spec.choice if s in subjects]
        if not missing_required and have_choice:
            status = FULL if len(have_choice) == len(spec.choice) else PARTIAL
            return FieldResult(spec.code, spec.name, status, extra_exam=spec.extra_exam)
        gap_options = [] if have_choice else list(spec.choice)
    else:
        if not missing_required:
            return FieldResult(spec.code, spec.name, FULL, extra_exam=spec.extra_exam)
        gap_options = []
    return FieldResult(
        spec.code,
        spec.name,
        NONE,
        gap_required=missing_required,
        gap_options=gap_options,
        extra_exam=spec.extra_exam,
    )


def coverage(results: Sequence[FieldResult]) -> tuple[Fraction, int, int, int]:
    """Точная доля доступных направлений: (Fraction, доступно, всего, из них full)."""
    total = len(results)
    available = sum(1 for r in results if r.available)
    full = sum(1 for r in results if r.status == FULL)
    share = Fraction(available, total) if total else Fraction(0)
    return share, available, total, full


def percent(share: Fraction) -> float:
    """Процент из точной дроби. round(), не усечение: int(83.99999) дал бы 83."""
    return round(float(share) * 100, 1)


def _candidate_subjects(all_subjects: Sequence[str], have: set[str]) -> list[str]:
    return [s for s in all_subjects if s not in have]


def advise(
    profile: ProfileSpec,
    specs: Sequence[FieldSpec],
    subjects: set[str],
    all_subjects: Sequence[str],
    max_add: int = 2,
) -> dict | None:
    """Минимальное дополнение: какие предметы добрать, чтобы вернуть направления.

    Перебираем наборы размера 1, затем 2. Порядок детерминирован: сначала
    больший выигрыш, затем предметы, доступные элективом в этой школе,
    затем порядок предметов в справочнике.
    """
    closed = [s for s in specs if not evaluate_field(s, subjects).available]
    if not closed:
        return None
    candidates = _candidate_subjects(all_subjects, subjects)
    order = {s: i for i, s in enumerate(all_subjects)}
    best: dict | None = None
    from itertools import combinations

    for size in range(1, max_add + 1):
        for combo in combinations(candidates, size):
            gained = [s.code for s in closed if evaluate_field(s, subjects | set(combo)).available]
            if not gained:
                continue
            in_school = all(c in profile.electives for c in combo)
            key = (-len(gained), size, 0 if in_school else 1, tuple(order[c] for c in combo))
            if best is None or key < best["_key"]:
                best = {
                    "_key": key,
                    "add": list(combo),
                    "gain": len(gained),
                    "becomes_available": gained,
                    "elective_in_school": in_school,
                }
        if best is not None and best["gain"] == len(closed):
            break  # меньшим набором уже закрыли всё — большие не рассматриваем
    if best is None:
        return None
    best.pop("_key")
    return best


def match_profiles(
    profiles: Sequence[ProfileSpec],
    specs: Sequence[FieldSpec],
    all_subjects: Sequence[str],
    extra_subjects: Iterable[str] = (),
) -> list[dict]:
    """Сравнение всех профилей школы по выбранным направлениям.

    Результат отсортирован: больше доступных направлений -> больше полностью
    закрытых -> порядок профилей в справочнике школы (устойчивая сортировка).
    """
    extra = set(extra_subjects)
    out: list[dict] = []
    for prof in profiles:
        subjects = profile_subjects(prof, extra)
        results = [evaluate_field(s, subjects) for s in specs]
        share, available, total, full = coverage(results)
        out.append(
            {
                "profile_id": prof.id,
                "profile_name": prof.name,
                "advanced": list(prof.advanced),
                "electives": list(prof.electives),
                "subjects_considered": sorted(subjects, key=lambda s: all_subjects.index(s)),
                "available": available,
                "total": total,
                "full": full,
                "fraction": f"{share.numerator}/{share.denominator}" if total else "0/0",
                "percent": percent(share),
                "fields": [
                    {
                        "code": r.code,
                        "name": r.name,
                        "status": r.status,
                        "gap_required": r.gap_required,
                        "gap_options": r.gap_options,
                        "extra_exam": r.extra_exam,
                    }
                    for r in results
                ],
                "advice": advise(prof, specs, subjects, all_subjects),
            }
        )
    out.sort(key=lambda p: (-p["available"], -p["full"]))
    return out


def school_gap_report(
    profiles: Sequence[ProfileSpec],
    specs_by_code: dict[str, FieldSpec],
    demand: dict[str, int],
    all_subjects: Sequence[str],
) -> dict:
    """Агрегат для школы: какие запросы учеников не закрывает ни один профиль.

    `demand` — сколько учеников отметили направление (обезличенно).
    Возвращает список «непокрытых» направлений и лучший одиночный электив.
    """
    uncovered: list[dict] = []
    for code, count in demand.items():
        spec = specs_by_code.get(code)
        if spec is None:
            continue
        if any(evaluate_field(spec, profile_subjects(p)).available for p in profiles):
            continue
        uncovered.append({"code": code, "name": spec.name, "students": count})
    uncovered.sort(key=lambda u: (-u["students"], u["code"]))

    best = None
    for prof_index, prof in enumerate(profiles):
        subjects = profile_subjects(prof)
        for subj in _candidate_subjects(all_subjects, subjects):
            with_subj = subjects | {subj}
            gained = [
                u for u in uncovered
                if evaluate_field(specs_by_code[u["code"]], with_subj).available
            ]
            if not gained:
                continue
            students = sum(u["students"] for u in gained)
            # при равном эффекте дешевле тот профиль, где предмет уже заявлен
            # школой как электив: не нужно менять учебный план
            key = (-students, -len(gained), 0 if subj in prof.electives else 1,
                   all_subjects.index(subj), prof_index)
            if best is None or key < best["_key"]:
                best = {
                    "_key": key,
                    "profile_id": prof.id,
                    "profile_name": prof.name,
                    "subject": subj,
                    "returns_fields": [u["code"] for u in gained],
                    "affected_students": students,
                    "elective_in_school": subj in prof.electives,
                }
    if best:
        best.pop("_key")
    return {"uncovered": uncovered, "best_elective": best}
