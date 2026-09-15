"""Адаптер Bot API мессенджера MAX.

Весь платформенный протокол сосредоточен в этом модуле: адрес, авторизация,
формат обновлений и клавиатур. Логика сценария (dialog.py) от него не зависит,
поэтому изменения в API платформы правятся в одном файле.

Протокол сверен с официальной библиотекой MAX для разработки чат-ботов
(github.com/max-messenger/max-botapi-python): базовый адрес botapi.max.ru,
токен передаётся query-параметром access_token, пути /me, /updates, /messages,
/answers, типы обновлений message_created, bot_started, message_callback,
клавиатура — вложение inline_keyboard с массивом рядов кнопок.

Документация MAX обновляется, поэтому адрес и тип кнопки запуска
мини-приложения вынесены в константы и переменные окружения — сверяйте их
перед пилотом.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

log = logging.getLogger("profil10.max")

BASE_URL = os.getenv("MAX_API_BASE", "https://botapi.max.ru").rstrip("/")
UPDATE_BOT_STARTED = "bot_started"
UPDATE_MESSAGE_CREATED = "message_created"
UPDATE_MESSAGE_CALLBACK = "message_callback"


class MaxApiError(RuntimeError):
    """Ошибка вызова Bot API (сеть, код ответа, неверный токен)."""


class MaxClient:
    def __init__(self, token: str, base_url: str = BASE_URL, timeout: int = 40) -> None:
        if not token:
            raise MaxApiError("Не задан MAX_BOT_TOKEN — токен выдаёт организатор/владелец бота")
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.marker: int | None = None

    # --- транспорт ------------------------------------------------------
    def _request(self, method: str, path: str, *, params: dict | None = None,
                 json_body: dict | None = None, retries: int = 3) -> dict:
        params = {**(params or {}), "access_token": self.token}
        url = f"{self.base_url}{path}"
        delay = 1.0
        last: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                resp = self.session.request(method, url, params=params, json=json_body, timeout=self.timeout)
                if resp.status_code == 429:  # ограничение частоты — ждём и повторяем
                    wait = float(resp.headers.get("Retry-After", delay))
                    log.warning("MAX API 429, повтор через %.1f с", wait)
                    time.sleep(wait)
                    delay *= 2
                    continue
                if resp.status_code >= 500:
                    raise MaxApiError(f"{resp.status_code} от MAX API: {resp.text[:200]}")
                if resp.status_code >= 400:
                    # 4xx не лечится повтором: это ошибка запроса или токена
                    raise MaxApiError(f"{resp.status_code} от MAX API: {resp.text[:300]}")
                return resp.json() if resp.content else {}
            except (requests.RequestException, MaxApiError) as exc:
                last = exc
                if attempt == retries:
                    break
                log.warning("Сбой вызова MAX API (%s), попытка %d/%d", exc, attempt, retries)
                time.sleep(delay)
                delay *= 2
        raise MaxApiError(f"MAX API недоступен: {last}")

    # --- методы ---------------------------------------------------------
    def get_me(self) -> dict:
        return self._request("GET", "/me")

    def get_updates(self, timeout: int = 30, limit: int = 50) -> list[dict]:
        params: dict[str, Any] = {"timeout": timeout, "limit": limit}
        if self.marker is not None:
            params["marker"] = self.marker
        data = self._request("GET", "/updates", params=params, retries=2)
        self.marker = data.get("marker", self.marker)
        return data.get("updates", [])

    def send_message(self, chat_id: str | int, text: str, buttons: list[list[dict]] | None = None) -> dict:
        body: dict[str, Any] = {"text": text}
        if buttons:
            body["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]
        return self._request("POST", "/messages", params={"chat_id": chat_id}, json_body=body)

    def answer_callback(self, callback_id: str, text: str | None = None,
                        buttons: list[list[dict]] | None = None, notification: str | None = None) -> dict:
        body: dict[str, Any] = {}
        if text:
            message: dict[str, Any] = {"text": text}
            if buttons:
                message["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]
            body["message"] = message
        if notification:
            body["notification"] = notification
        return self._request("POST", "/answers", params={"callback_id": callback_id}, json_body=body)


# --- конструкторы кнопок ------------------------------------------------

def button_callback(text: str, payload: str) -> dict:
    return {"type": "callback", "text": text, "payload": payload}


def button_link(text: str, url: str) -> dict:
    return {"type": "link", "text": text, "url": url}


def button_miniapp(text: str, url: str, bot_username: str | None = None,
                   bot_id: int | str | None = None) -> dict:
    """Кнопка запуска мини-приложения. Два режима, переключаются MINIAPP_BUTTON_TYPE.

    `open_app` — штатный механизм платформы. Кнопка не принимает произвольный
    адрес: мини-приложение привязано к самому боту, поэтому передаются его
    публичное имя (`web_app`) и идентификатор (`contact_id`). В этом режиме
    мини-приложение узнаёт пользователя не из ссылки, а из параметров запуска
    MAX — см. раздел «Известные ограничения» в README.

    `link` (по умолчанию) — обычная ссылка с подписанным токеном анкеты.
    Работает в мобильной и в веб-версии и не требует параметров запуска, но
    открывается как внешняя страница.

    Если выбран open_app, а бот не сообщил своих username и user_id
    (ответ /me не получен), отправляем ссылку: лучше рабочая кнопка, чем
    заведомо неполная.
    """
    kind = os.getenv("MINIAPP_BUTTON_TYPE", "link")
    if kind == "open_app":
        button: dict[str, Any] = {"type": "open_app", "text": text}
        if bot_username:
            button["web_app"] = bot_username
        if bot_id:
            button["contact_id"] = bot_id
        if len(button) > 2:
            return button
        log.warning("MINIAPP_BUTTON_TYPE=open_app, но идентификация бота неизвестна — отправляю ссылку")
    return button_link(text, url)


# --- разбор обновлений --------------------------------------------------

def parse_update(update: dict) -> dict | None:
    """Приводит обновление MAX к внутреннему виду сценария.

    Возвращает {kind, user_id, chat_id, text, payload, callback_id} либо None,
    если тип обновления сценарию не нужен.
    """
    kind = update.get("update_type")
    if kind == UPDATE_BOT_STARTED:
        user = update.get("user") or {}
        return {"kind": "start", "user_id": str(user.get("user_id") or ""),
                "chat_id": str(update.get("chat_id") or user.get("user_id") or ""),
                "text": "", "payload": update.get("payload") or "", "callback_id": None}
    if kind == UPDATE_MESSAGE_CREATED:
        msg = update.get("message") or {}
        sender = msg.get("sender") or {}
        recipient = msg.get("recipient") or {}
        return {"kind": "text", "user_id": str(sender.get("user_id") or ""),
                "chat_id": str(recipient.get("chat_id") or sender.get("user_id") or ""),
                "text": ((msg.get("body") or {}).get("text") or "").strip(),
                "payload": "", "callback_id": None}
    if kind == UPDATE_MESSAGE_CALLBACK:
        cb = update.get("callback") or {}
        msg = update.get("message") or {}
        recipient = msg.get("recipient") or {}
        user = cb.get("user") or {}
        return {"kind": "callback", "user_id": str(user.get("user_id") or ""),
                "chat_id": str(recipient.get("chat_id") or user.get("user_id") or ""),
                "text": "", "payload": cb.get("payload") or "",
                "callback_id": cb.get("callback_id")}
    log.debug("Обновление типа %s сценарием не используется", kind)
    return None
