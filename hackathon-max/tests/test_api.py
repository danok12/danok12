"""Тесты API: контракты, авторизация, обработка ошибок, приватность агрегата."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

# Значения задаются жёстко, а не через setdefault: иначе переменные окружения
# запущенного рядом сервиса (INTERNAL_KEY, DB_PATH) протекали бы в тесты —
# ключ не совпадал бы с заголовком в тесте, а база писалась бы поверх рабочей.
os.environ["APP_SECRET"] = "test-secret"
os.environ["INTERNAL_KEY"] = "test-internal"
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.sqlite3")
os.environ["PUBLIC_BASE_URL"] = "https://example.org"

from fastapi.testclient import TestClient    # noqa: E402
from app.main import app                     # noqa: E402

SELECTION = ["09.00.00", "38.00.00", "40.00.00", "31.00.00", "45.00.00"]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session(client):
    r = client.post("/api/sessions", json={"max_user_id": "pytest-user", "chat_id": "pytest-chat",
                                           "class_code": "9A-114"})
    assert r.status_code == 201
    return r.json()


def auth(session):
    return {"authorization": f"Bearer {session['token']}"}


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["fields"] >= 30


def test_meta_marks_demo_data(client):
    body = client.get("/api/meta").json()
    assert body["data"]["demo_data"] is True
    assert "не заменяет" in body["disclaimer"]


def test_class_lookup_is_case_insensitive(client):
    assert client.get("/api/classes/9a-114").json()["class"]["code"] == "9A-114"


def test_unknown_class_gives_hint(client):
    r = client.get("/api/classes/NOPE")
    assert r.status_code == 404
    assert r.json()["detail"]["hint"]


def test_session_is_idempotent_per_class(client, session):
    again = client.post("/api/sessions", json={"max_user_id": "pytest-user", "chat_id": "pytest-chat",
                                               "class_code": "9A-114"})
    assert again.json()["session_id"] == session["session_id"]


def test_miniapp_url_uses_public_base(session):
    assert session["miniapp_url"].startswith("https://example.org/app/?t=")


def test_match_requires_token(client, session):
    r = client.post(f"/api/sessions/{session['session_id']}/match", json={"selected_fields": SELECTION})
    assert r.status_code == 401


def test_match_rejects_foreign_token(client, session):
    other = client.post("/api/sessions", json={"max_user_id": "someone-else", "class_code": "9A-114"}).json()
    r = client.post(f"/api/sessions/{session['session_id']}/match",
                    json={"selected_fields": SELECTION}, headers=auth(other))
    assert r.status_code == 403


def test_match_contract(client, session):
    r = client.post(f"/api/sessions/{session['session_id']}/match",
                    json={"selected_fields": SELECTION}, headers=auth(session))
    assert r.status_code == 200
    body = r.json()
    assert {"school", "class", "admission", "profiles", "subjects", "data"} <= set(body)
    tech = [p for p in body["profiles"] if p["profile_id"] == "tech"][0]
    assert (tech["available"], tech["total"], tech["percent"]) == (2, 5, 40.0)
    assert all(f["status"] in {"full", "partial", "none"} for f in tech["fields"])


def test_too_many_fields_rejected(client, session):
    codes = [f["code"] for f in client.get("/api/catalog/fields").json()["items"]][:9]
    r = client.post(f"/api/sessions/{session['session_id']}/match",
                    json={"selected_fields": codes}, headers=auth(session))
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "too_many_fields"


def test_decision_requires_selection_first(client):
    fresh = client.post("/api/sessions", json={"max_user_id": "pytest-empty", "class_code": "9A-114"}).json()
    r = client.post(f"/api/sessions/{fresh['session_id']}/decision",
                    json={"profile_id": "tech"}, headers=auth(fresh))
    assert r.status_code == 409


def test_decision_puts_card_into_outbox(client, session):
    client.post(f"/api/sessions/{session['session_id']}/match",
                json={"selected_fields": SELECTION}, headers=auth(session))
    r = client.post(f"/api/sessions/{session['session_id']}/decision",
                    json={"profile_id": "tech", "remind": True}, headers=auth(session))
    assert r.status_code == 200
    items = client.get("/api/internal/outbox", headers={"x-internal-key": "test-internal"}).json()["items"]
    cards = [i for i in items if i["kind"] == "decision_card"]
    assert cards and "Ваш разбор профилей" in cards[-1]["payload"]["text"]


def test_internal_contour_is_closed(client):
    assert client.get("/api/internal/outbox").status_code == 401
    assert client.get("/api/internal/outbox", headers={"x-internal-key": "wrong"}).status_code == 401


def test_analytics_hides_data_below_threshold(client):
    token = client.post("/api/school/auth", json={"curator_code": "KUR-114-9B"}).json()["token"]
    body = client.get("/api/school/9B-114/analytics", headers={"authorization": f"Bearer {token}"}).json()
    assert body["status"] == "insufficient_data"
    assert "top_fields" not in body


def test_curator_token_is_bound_to_class(client):
    token = client.post("/api/school/auth", json={"curator_code": "KUR-114-9B"}).json()["token"]
    r = client.get("/api/school/9A-114/analytics", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_bad_curator_code(client):
    r = client.post("/api/school/auth", json={"curator_code": "NO-SUCH"})
    assert r.status_code == 401 and r.json()["detail"]["hint"]


def test_subject_names_in_bot_match_catalog():
    """Словарь подписей в боте не должен расходиться со справочником."""
    sys.path.insert(0, str(ROOT / "bot"))
    from bot.subject_names import SUBJECT_NAMES
    from app.catalog import get_catalog
    assert set(SUBJECT_NAMES) == set(get_catalog().subject_names)
