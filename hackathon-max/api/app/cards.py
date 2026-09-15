"""Тексты сообщений бота собираются здесь — в одном месте на весь продукт.

Бот остаётся тонким: он доставляет готовый текст и кнопки из очереди,
а формулировки и расчёт живут в API. Это же позволяет менять тексты
без пересборки бота.
"""

from __future__ import annotations

from .catalog import get_catalog

STATUS_MARK = {"full": "●", "partial": "◐", "none": "○"}


def _subj(ids: list[str]) -> str:
    names = get_catalog().subject_names
    return ", ".join(names.get(i, i) for i in ids)


def decision_card(result: dict, chosen: dict, school: dict, admission: dict) -> str:
    """Карточка решения: что выбрано, что закрывается, что теряется, что делать."""
    lines = [
        "🎓 Ваш разбор профилей",
        f"{school['name']}, {school['city']} · {admission['description']}",
        "",
        f"Выбранный профиль: {chosen['profile_name']}",
        f"Углублённо: {_subj(chosen['advanced'])}",
        f"Закрывает направлений: {chosen['available']} из {chosen['total']} ({chosen['percent']}%)",
        "",
    ]
    open_fields = [f for f in chosen["fields"] if f["status"] != "none"]
    closed = [f for f in chosen["fields"] if f["status"] == "none"]
    if open_fields:
        lines.append("Остаются доступны:")
        for f in open_fields:
            suffix = " (не во всех вузах)" if f["status"] == "partial" else ""
            lines.append(f"  {STATUS_MARK[f['status']]} {f['name']}{suffix}")
    if closed:
        lines.append("")
        lines.append("Закрываются при этом профиле:")
        for f in closed:
            need = list(f["gap_required"])
            alt = f["gap_options"]
            text = _subj(need) if need else ""
            if alt:
                text = (text + "; " if text else "") + "один из: " + _subj(alt)
            lines.append(f"  ○ {f['name']} — не хватает: {text}")
    advice = chosen.get("advice")
    if advice:
        where = "есть в школе как электив" if advice["elective_in_school"] else "школа пока не предлагает"
        lines += [
            "",
            f"Что спросить в школе: можно ли добрать {_subj(advice['add'])} "
            f"({where}). Это вернёт направлений: {advice['gain']}.",
        ]
    lines += [
        "",
        f"Срок подачи заявления: {admission['deadline']}.",
        f"Данные школы актуальны на {admission['updated_at']}.",
        "",
        "ℹ️ Расчёт информационный: он показывает, какие ЕГЭ нужны направлению, "
        "и не заменяет правила приёма вуза и решение школы. "
        "Справочник в демо-версии модельный.",
    ]
    return "\n".join(lines)


def comparison_summary(results: list[dict]) -> str:
    """Короткая сводка по всем профилям — для ответа в чате без мини-приложения."""
    lines = ["Сравнение профилей по вашим направлениям:", ""]
    for r in results:
        lines.append(f"{r['profile_name']}: {r['available']} из {r['total']} ({r['percent']}%)")
    lines.append("")
    lines.append("● — доступны все вузы направления, ◐ — часть вузов, ○ — недоступно.")
    return "\n".join(lines)


def reminder_text(school: dict, admission: dict, chosen_profile: str | None) -> str:
    tail = f"\nВы рассматривали профиль: {chosen_profile}." if chosen_profile else ""
    return (
        "⏰ Напоминание\n"
        f"{admission['description']} в «{school['name']}» — до {admission['deadline']}.{tail}\n"
        "Уточните перечень документов у классного руководителя."
    )
