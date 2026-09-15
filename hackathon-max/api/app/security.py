"""Подпись и проверка токенов доступа к мини-приложению.

Бот создаёт сессию и кладёт подписанный токен в ссылку на мини-приложение.
Мини-приложение предъявляет его API. Токен подписан HMAC-SHA256 и содержит
идентификатор сессии, роль и срок действия — персональных данных внутри нет.

ОГРАНИЧЕНИЕ MVP: платформенная валидация параметров запуска мини-приложения
MAX здесь не реализована (нет доступа к стенду платформы). В пилоте проверку
launch-параметров MAX следует добавить дополнительно к этой подписи.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from .config import get_settings


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def issue_token(session_id: str, role: str = "student", ttl: int | None = None) -> str:
    s = get_settings()
    payload = {"sid": session_id, "role": role, "exp": int(time.time()) + (ttl or s.token_ttl)}
    body = _b64e(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    sig = hmac.new(s.app_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


class TokenError(ValueError):
    """Токен отсутствует, повреждён, подделан или истёк."""


def read_token(token: str) -> dict:
    s = get_settings()
    try:
        body, sig = (token or "").split(".", 1)
        expected = hmac.new(s.app_secret.encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64d(sig), expected):
            raise TokenError("подпись токена не совпадает")
        payload = json.loads(_b64d(body))
    except TokenError:
        raise
    except Exception as exc:  # noqa: BLE001 - любой разбор мусора трактуем одинаково
        raise TokenError("токен повреждён") from exc
    if payload.get("exp", 0) < time.time():
        raise TokenError("срок действия токена истёк")
    return payload
