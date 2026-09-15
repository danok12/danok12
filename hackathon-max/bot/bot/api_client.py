"""Клиент API «Профиль 10». Бот не хранит состояние сам — владелец данных API."""

from __future__ import annotations

import logging
import os
import time

import requests

log = logging.getLogger("profil10.apiclient")


class ApiError(RuntimeError):
    def __init__(self, message: str, hint: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.hint = hint
        self.status = status


class ApiClient:
    def __init__(self, base_url: str | None = None, internal_key: str | None = None, timeout: int = 15) -> None:
        self.base = (base_url or os.getenv("API_BASE_URL", "http://api:8080")).rstrip("/")
        self.key = internal_key or os.getenv("INTERNAL_KEY", "")
        self.timeout = timeout
        self.session = requests.Session()

    def _call(self, method: str, path: str, *, json_body: dict | None = None,
              headers: dict | None = None, retries: int = 3) -> dict:
        url = f"{self.base}{path}"
        delay = 1.0
        for attempt in range(1, retries + 1):
            try:
                resp = self.session.request(method, url, json=json_body,
                                            headers=headers or {}, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt == retries:
                    raise ApiError(f"Сервис недоступен: {exc}") from exc
                time.sleep(delay)
                delay *= 2
                continue
            if resp.status_code >= 500 and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            if resp.status_code >= 400:
                # Тело ошибки может быть объектом {error,message,hint}, строкой
                # или вовсе не JSON — сценарий должен пережить любой вариант.
                detail: object = {}
                try:
                    payload = resp.json()
                    detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
                except ValueError:
                    detail = resp.text[:200]
                if isinstance(detail, dict):
                    raise ApiError(detail.get("message", f"Ошибка {resp.status_code}"),
                                   detail.get("hint"), resp.status_code)
                raise ApiError(f"Ошибка {resp.status_code}: {detail}", None, resp.status_code)
            return resp.json() if resp.content else {}
        raise ApiError("Сервис недоступен")

    # --- сценарий -------------------------------------------------------
    def create_session(self, user_id: str, chat_id: str, class_code: str) -> dict:
        return self._call("POST", "/api/sessions", json_body={
            "max_user_id": user_id, "chat_id": chat_id, "class_code": class_code})

    def session_by_user(self, user_id: str) -> dict:
        return self._call("GET", f"/api/internal/sessions/by-user/{user_id}",
                          headers={"x-internal-key": self.key})

    def patch_session(self, session_id: str, token: str, **fields) -> dict:
        return self._call("PATCH", f"/api/sessions/{session_id}", json_body=fields,
                          headers={"authorization": f"Bearer {token}"})

    def class_info(self, class_code: str) -> dict:
        return self._call("GET", f"/api/classes/{class_code}")

    # --- служебный контур ----------------------------------------------
    def take_outbox(self, limit: int = 20) -> list[dict]:
        data = self._call("GET", f"/api/internal/outbox?limit={limit}",
                          headers={"x-internal-key": self.key}, retries=2)
        return data.get("items", [])

    def ack_outbox(self, item_id: int, ok: bool = True) -> None:
        self._call("POST", f"/api/internal/outbox/{item_id}/ack?ok={'true' if ok else 'false'}",
                   headers={"x-internal-key": self.key}, retries=2)

    def cancel_reminder(self, chat_id: str) -> dict:
        return self._call("POST", "/api/internal/reminders/cancel", json_body={"chat_id": chat_id},
                          headers={"x-internal-key": self.key}, retries=2)

    def track(self, type_: str, session_id: str | None = None, payload: dict | None = None) -> None:
        try:
            self._call("POST", "/api/internal/events",
                       json_body={"type": type_, "session_id": session_id, "payload": payload or {}},
                       headers={"x-internal-key": self.key}, retries=1)
        except ApiError as exc:  # метрики не должны ломать диалог
            log.warning("Событие %s не записано: %s", type_, exc)
