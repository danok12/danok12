"""Тесты формата кнопок MAX.

Формат сверен с официальной библиотекой max-messenger/max-botapi-python:
клавиатура — вложение inline_keyboard с массивом рядов; кнопка запуска
мини-приложения имеет тип open_app и принимает публичное имя бота (web_app)
и его идентификатор (contact_id), а не произвольный адрес.
"""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from bot import max_api  # noqa: E402

URL = "https://example.org/app/?t=token"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("MINIAPP_BUTTON_TYPE", raising=False)
    yield


def test_keyboard_attachment_shape():
    buttons = [[max_api.button_callback("Да", "yes")], [max_api.button_link("Сайт", "https://e.org")]]
    # так клавиатура кладётся в сообщение (см. MaxClient.send_message)
    attachment = {"type": "inline_keyboard", "payload": {"buttons": buttons}}
    assert attachment["payload"]["buttons"][0][0] == {"type": "callback", "text": "Да", "payload": "yes"}
    assert attachment["payload"]["buttons"][1][0]["type"] == "link"


def test_default_mode_is_link_with_token():
    b = max_api.button_miniapp("Открыть подбор", URL, bot_username="profil10_bot", bot_id=777)
    assert b == {"type": "link", "text": "Открыть подбор", "url": URL}


def test_open_app_mode_uses_bot_identity_not_url(monkeypatch):
    monkeypatch.setenv("MINIAPP_BUTTON_TYPE", "open_app")
    b = max_api.button_miniapp("Открыть подбор", URL, bot_username="profil10_bot", bot_id=777)
    assert b == {"type": "open_app", "text": "Открыть подбор",
                 "web_app": "profil10_bot", "contact_id": 777}
    assert "url" not in b   # платформа не принимает произвольный адрес в этой кнопке


def test_open_app_without_identity_falls_back_to_link(monkeypatch):
    """Если /me не ответил, лучше рабочая ссылка, чем кнопка без адресата."""
    monkeypatch.setenv("MINIAPP_BUTTON_TYPE", "open_app")
    b = max_api.button_miniapp("Открыть подбор", URL)
    assert b["type"] == "link" and b["url"] == URL


def test_update_parsing_matches_platform_types():
    started = max_api.parse_update({"update_type": "bot_started", "chat_id": 5,
                                    "user": {"user_id": 42}})
    assert (started["kind"], started["user_id"], started["chat_id"]) == ("start", "42", "5")

    text = max_api.parse_update({"update_type": "message_created", "message": {
        "sender": {"user_id": 42}, "recipient": {"chat_id": 5, "chat_type": "dialog"},
        "body": {"mid": "m1", "seq": 1, "text": "  9A-114 "}}})
    assert (text["kind"], text["text"]) == ("text", "9A-114")

    cb = max_api.parse_update({"update_type": "message_callback", "callback": {
        "callback_id": "cb1", "payload": "init:tech", "user": {"user_id": 42}},
        "message": {"recipient": {"chat_id": 5, "chat_type": "dialog"}}})
    assert (cb["kind"], cb["payload"], cb["callback_id"]) == ("callback", "init:tech", "cb1")

    assert max_api.parse_update({"update_type": "dialog_muted"}) is None
