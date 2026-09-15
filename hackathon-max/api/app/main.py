"""Профиль 10 — API и раздача мини-приложения.

Компонент отвечает за справочники, расчёт, хранение анкет, обезличенный
агрегат для школы и очередь сообщений для чат-бота.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .catalog import get_catalog
from .config import get_settings
from .routers import catalog as catalog_router
from .routers import internal as internal_router
from .routers import school as school_router
from .routers import sessions as sessions_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("profil10.api")

STATIC_DIR = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Старт: проверяем секреты, готовим базу, прогреваем справочники."""
    get_settings().require_secrets()
    db.init_db()
    cat = get_catalog()
    log.info("Справочники загружены: направлений %d, школ %d, версия %s",
             len(cat.fields), len(cat.schools), cat.fields_raw["version"])
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Профиль 10 — API",
    version="1.0.0",
    description=(
        "Сервис подбора профиля обучения в 10 классе по направлениям подготовки, "
        "которые интересны ученику. Данные справочников в MVP демонстрационные."
    ),
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(catalog_router.router)
app.include_router(sessions_router.router)
app.include_router(school_router.router)
app.include_router(internal_router.router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Любая неожиданная ошибка отдаётся в том же формате, что и остальные.

    Пользователь мини-приложения видит понятное сообщение и может повторить
    действие, не перезапуская сценарий.
    """
    log.exception("Необработанная ошибка на %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error",
                 "message": "Внутренняя ошибка сервиса. Повторите действие.",
                 "hint": "Если ошибка повторяется, вернитесь в чат-бота и откройте подбор заново."},
    )


@app.get("/api/health", tags=["Служебное"], summary="Проверка готовности")
def health() -> dict:
    cat = get_catalog()
    db.connect().execute("SELECT 1")
    return {"status": "ok", "fields": len(cat.fields), "schools": len(cat.schools),
            "data_version": cat.fields_raw["version"]}


# --- мини-приложение ----------------------------------------------------
if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=STATIC_DIR, html=True), name="miniapp")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")
else:  # сборка мини-приложения не выполнена — API всё равно работает
    @app.get("/", include_in_schema=False)
    def index_missing() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": "miniapp_not_built",
                     "message": "Мини-приложение не собрано.",
                     "hint": "Соберите miniapp (npm ci && npm run build) или запустите через docker compose."},
        )
