"""Конфигурация API. Все значения берутся из переменных окружения."""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        # Секрет подписи токенов мини-приложения. В проде задаётся обязательно.
        self.app_secret: str = os.getenv("APP_SECRET", "")
        # Общий ключ для служебных вызовов бот -> API (не выдаётся наружу).
        self.internal_key: str = os.getenv("INTERNAL_KEY", "")
        # Публичный HTTPS-адрес, по которому MAX открывает мини-приложение.
        self.public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
        self.db_path: str = os.getenv("DB_PATH", "/data/profil10.sqlite3")
        # Время жизни токена мини-приложения, секунды.
        self.token_ttl: int = int(os.getenv("TOKEN_TTL", "86400"))
        # k-анонимность: минимум анкет в классе, чтобы показать агрегат школе.
        self.min_aggregate: int = int(os.getenv("MIN_AGGREGATE", "5"))
        # Сколько направлений разрешено отметить (границы MVP).
        self.max_fields: int = int(os.getenv("MAX_FIELDS", "8"))
        self.cors_origins: list[str] = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        ]
        # Демо-режим напоминаний: прислать напоминание через N секунд вместо
        # «за 3 дня до срока». Используется только для проверки сценария.
        self.reminder_demo_delay: int = int(os.getenv("REMINDER_DEMO_DELAY", "0"))
        self.reminder_days_before: int = int(os.getenv("REMINDER_DAYS_BEFORE", "3"))

    def require_secrets(self) -> None:
        missing = [n for n, v in (("APP_SECRET", self.app_secret), ("INTERNAL_KEY", self.internal_key)) if not v]
        if missing:
            raise RuntimeError(
                "Не заданы обязательные переменные окружения: " + ", ".join(missing)
                + ". См. .env.example"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
