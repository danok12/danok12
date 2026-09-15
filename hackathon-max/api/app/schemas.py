"""Контракты API (pydantic). Совпадают с openapi.yaml и DATA-API.yaml."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    max_user_id: str = Field(..., min_length=1, max_length=64, description="Идентификатор пользователя в MAX")
    chat_id: str | None = Field(None, max_length=64, description="Чат для ответных сообщений бота")
    class_code: str = Field(..., min_length=3, max_length=32, description="Код класса от классного руководителя")


class SessionCreated(BaseModel):
    session_id: str
    token: str
    miniapp_url: str
    school: dict
    profiles: list[dict]
    admission: dict


class SessionPatch(BaseModel):
    selected_fields: list[str] | None = Field(None, max_length=32)
    extra_subjects: list[str] | None = Field(None, max_length=11)
    initial_profile: str | None = Field(None, max_length=32)


class MatchRequest(BaseModel):
    class_code: str = Field(..., min_length=3, max_length=32)
    fields: list[str] = Field(..., min_length=1, max_length=32)
    extra_subjects: list[str] = Field(default_factory=list, max_length=11)


class Decision(BaseModel):
    profile_id: str = Field(..., min_length=1, max_length=32)
    remind: bool = True


class Problem(BaseModel):
    """Единый формат ошибки: код, человекочитаемое сообщение, подсказка."""

    error: str
    message: str
    hint: str | None = None
