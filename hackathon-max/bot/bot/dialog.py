"""Сценарий чат-бота «Профиль 10».

Бот ведёт короткую часть пути: вход, код класса, исходное намерение ученика
и запуск мини-приложения. Сравнение профилей и каталог направлений живут
в мини-приложении — там нужен экран со списком и таблицей.

Состояние диалога не хранится в памяти процесса: всё, что нужно, бот
запрашивает у API. Перезапуск контейнера не ломает начатый сценарий.
"""

from __future__ import annotations

import logging
import re

from .api_client import ApiClient, ApiError
from .max_api import button_callback, button_miniapp

log = logging.getLogger("profil10.dialog")

CLASS_CODE_RE = re.compile(r"^\s*\d{1,2}\s*[A-Za-zА-Яа-я]\s*-\s*[A-Za-z0-9-]{2,}\s*$")

GREETING = (
    "👋 Это «Профиль 10».\n\n"
    "В 9 классе вы выбираете профиль на два года вперёд. Профиль задаёт предметы, "
    "которые вы изучаете углублённо, а они — какие ЕГЭ вы реально сможете сдать. "
    "От этого зависит, какие направления в вузах останутся доступны, а какие закроются.\n\n"
    "Я покажу это сравнение по профилям вашей школы за 3 минуты.\n\n"
    "Введите код класса — его даёт классный руководитель. Например: 9A-114"
)

ABOUT = (
    "Как это работает:\n"
    "1. Вы вводите код класса — я подтягиваю профили именно вашей школы.\n"
    "2. Отмечаете направления подготовки, которые вам интересны.\n"
    "3. Получаете сравнение: сколько ваших направлений закрывает каждый профиль, "
    "что закроется и какой предмет нужно добрать, чтобы вернуть потерянное.\n"
    "4. Карточка с разбором приходит в чат — её можно показать родителям и классному руководителю.\n\n"
    "Важно: расчёт информационный. Он показывает требования к вступительным испытаниям "
    "и не заменяет правила приёма конкретного вуза и решение школы.\n"
    "В демо-версии справочник вступительных испытаний модельный."
)

HELP = (
    "Команды:\n"
    "/start — начать заново\n"
    "/help — эта справка\n\n"
    "Чтобы продолжить, введите код класса (например, 9A-114) "
    "или нажмите кнопку в сообщении выше."
)

UNKNOWN = (
    "Не понял сообщение. Введите код класса от классного руководителя "
    "(например, 9A-114) или нажмите /help."
)


class Dialog:
    """Обработчик одного обновления. Возвращает (text, buttons) для ответа."""

    def __init__(self, api: ApiClient, miniapp_hint: str = "Открыть подбор") -> None:
        self.api = api
        self.miniapp_hint = miniapp_hint

    # --- точка входа ----------------------------------------------------
    def handle(self, event: dict) -> tuple[str, list[list[dict]] | None]:
        kind = event["kind"]
        try:
            if kind == "start":
                return self.on_start(event)
            if kind == "callback":
                return self.on_callback(event)
            return self.on_text(event)
        except ApiError as exc:
            log.warning("Ошибка API в диалоге: %s", exc)
            hint = f"\n{exc.hint}" if exc.hint else ""
            return (f"⚠️ {exc}{hint}", [[button_callback("Начать заново", "menu:restart")]])

    # --- обработчики ----------------------------------------------------
    def on_start(self, event: dict) -> tuple[str, list[list[dict]] | None]:
        self.api.track("bot_started")
        resume = self._resume(event["user_id"])
        if resume:
            return resume
        return GREETING, [[button_callback("Что это и зачем", "menu:about")]]

    def on_text(self, event: dict) -> tuple[str, list[list[dict]] | None]:
        text = (event.get("text") or "").strip()
        low = text.lower()
        if low.startswith("/start"):
            return self.on_start(event)
        if low.startswith("/help"):
            return HELP, None
        if CLASS_CODE_RE.match(text):
            return self.enter_class(event["user_id"], event["chat_id"], re.sub(r"\s+", "", text))
        resume = self._resume(event["user_id"])
        if resume:
            return resume
        return UNKNOWN, [[button_callback("Что это и зачем", "menu:about")]]

    def on_callback(self, event: dict) -> tuple[str, list[list[dict]] | None]:
        payload = event.get("payload") or ""
        if payload == "menu:about":
            return ABOUT, [[button_callback("Понятно, ввести код класса", "menu:restart")]]
        if payload == "menu:restart":
            return ("Введите код класса от классного руководителя. Например: 9A-114", None)
        if payload.startswith("init:"):
            return self.set_initial_profile(event, payload.removeprefix("init:"))
        if payload == "menu:open":
            return self._open_app_message(event["user_id"], event["chat_id"])
        if payload == "reminder:off":
            self.api.cancel_reminder(event["chat_id"])
            return ("Напоминание о сроке отключено. Включить снова можно после нового расчёта.", None)
        return UNKNOWN, None

    # --- шаги сценария --------------------------------------------------
    def enter_class(self, user_id: str, chat_id: str, code: str) -> tuple[str, list[list[dict]] | None]:
        data = self.api.create_session(user_id, chat_id, code)
        school, adm = data["school"], data["admission"]
        profiles = data["profiles"]
        names = "\n".join(f"  • {p['name']} — углублённо: {self._subjects(p)}" for p in profiles)
        text = (
            f"Школа: {school['name']}, {school['city']}\n"
            f"{adm['description']} — до {adm['deadline']}\n\n"
            f"Профили вашей школы:\n{names}\n\n"
            "Какой профиль вы рассматриваете сейчас? Отмечу его как исходный — "
            "потом будет видно, изменился ли выбор после расчёта."
        )
        buttons = [[button_callback(p["name"], f"init:{p['id']}")] for p in profiles]
        buttons.append([button_callback("Ещё не решил", "init:none")])
        self.api.track("class_entered", data["session_id"], {"class_code": code})
        return text, buttons

    def set_initial_profile(self, event: dict, profile_id: str) -> tuple[str, list[list[dict]] | None]:
        resume = self.api.session_by_user(event["user_id"])
        if not resume.get("found"):
            return ("Сначала введите код класса. Например: 9A-114", None)
        data = self.api.create_session(event["user_id"], event["chat_id"], resume["class_code"])
        if profile_id != "none":
            self.api.patch_session(data["session_id"], data["token"], initial_profile=profile_id)
        return self._open_app_message(event["user_id"], event["chat_id"], data)

    def _open_app_message(self, user_id: str, chat_id: str,
                          data: dict | None = None) -> tuple[str, list[list[dict]] | None]:
        if data is None:
            resume = self.api.session_by_user(user_id)
            if not resume.get("found"):
                return ("Сначала введите код класса. Например: 9A-114", None)
            data = self.api.create_session(user_id, chat_id, resume["class_code"])
        text = (
            "Теперь отметьте направления подготовки, которые вам интересны — "
            "их удобнее выбирать на отдельном экране, там же будет сравнение профилей.\n\n"
            "Выбрать можно до 8 направлений. Результат вернётся сюда, в чат."
        )
        return text, [[button_miniapp(self.miniapp_hint, data["miniapp_url"])]]

    def _resume(self, user_id: str) -> tuple[str, list[list[dict]] | None] | None:
        """Если у пользователя уже есть анкета — предлагаем продолжить, а не начинать заново."""
        try:
            resume = self.api.session_by_user(user_id)
        except ApiError:
            return None
        if not resume.get("found"):
            return None
        try:
            info = self.api.class_info(resume["class_code"])
        except ApiError:
            return None
        chosen = resume.get("chosen_profile")
        tail = " Вы уже выбирали профиль — можно пересчитать с другими направлениями." if chosen else ""
        text = (f"Продолжим? Вы работали с классом {info['class']['title']} "
                f"({info['school']['name']}).{tail}")
        return text, [[button_callback("Открыть подбор", "menu:open")],
                      [button_callback("Другой класс", "menu:restart")]]

    @staticmethod
    def _subjects(profile: dict) -> str:
        from .subject_names import SUBJECT_NAMES
        return ", ".join(SUBJECT_NAMES.get(s, s) for s in profile.get("advanced", []))
