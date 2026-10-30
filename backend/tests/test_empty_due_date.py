"""규칙 밖 마감일이 DB에 있어도 보드와 AI 계획·브리핑이 깨지지 않는다 (R-012, R-013, #32).

API는 마감일을 YYYY-MM-DD로만 받지만 DB의 due_date 칸에는 검사 규칙이 없어서, DB를 직접 고치면
규칙 밖 값이 들어갈 수 있다. 빈 문자열은 "마감일 없음"이므로 기한 초과가 아니다 (R-013).
실제 Claude API는 호출하지 않는다.
"""

import json
import sqlite3

import pytest

from app import suggest as ai
from app.routes import tasks as tasks_route
from tests.test_suggest import FakeClient, reply

TODAY = "2026-10-27"


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(tasks_route, "_today", lambda: TODAY)


def add_with_raw_due_date(c, db_file, raw) -> int:
    """API로 카드를 만든 뒤 DB의 due_date를 직접 raw 값으로 바꾼다."""
    res = c.post("/tasks", json={"title": "카드"})
    assert res.status_code == 201
    tid = res.json()["id"]
    conn = sqlite3.connect(db_file)
    try:
        conn.execute("UPDATE tasks SET due_date = ? WHERE id = ?", (raw, tid))
        conn.commit()
    finally:
        conn.close()
    return tid


def use_model(monkeypatch, text) -> FakeClient:
    fake = FakeClient(reply(text))
    monkeypatch.setattr(ai, "_client", lambda api_key: fake)
    return fake


def sent_tasks(fake) -> list[dict]:
    msg = fake.calls[0]["messages"][0]["content"]
    return json.loads(msg.split("<tasks>", 1)[1].rsplit("</tasks>", 1)[0])


def plan_text(tid) -> str:
    return json.dumps({"days": [{"date": "2026-10-28", "task_ids": [tid]}], "note": "나눴어요."}, ensure_ascii=False)


def brief_text(tid) -> str:
    body = {"top3": [{"id": tid, "reason": "먼저"}], "later": [], "cheer": "힘내요."}
    return json.dumps(body, ensure_ascii=False)


# --- 빈 문자열 마감일은 마감일 없음이다: 기한 초과가 아니다 (R-013) ---


def test_board_empty_string_due_date_is_not_overdue(auth_client, db_file):
    tid = add_with_raw_due_date(auth_client, db_file, "")
    task = {t["id"]: t for t in auth_client.get("/tasks").json()}[tid]
    assert task["overdue"] is False


def test_weekplan_sends_empty_string_due_date_as_not_overdue(auth_client, db_file, monkeypatch):
    tid = add_with_raw_due_date(auth_client, db_file, "")
    fake = use_model(monkeypatch, plan_text(tid))
    assert auth_client.post("/tasks/weekplan").status_code == 200
    assert sent_tasks(fake)[0]["overdue"] is False


def test_briefing_sends_empty_string_due_date_as_not_overdue(auth_client, db_file, monkeypatch):
    tid = add_with_raw_due_date(auth_client, db_file, "")
    fake = use_model(monkeypatch, brief_text(tid))
    assert auth_client.post("/tasks/briefing").status_code == 200
    assert sent_tasks(fake)[0]["overdue"] is False


# --- 규칙 밖 값이 있어도 보드와 계획이 깨지지 않는다 (완성 조건 ④) ---

BAD_VALUES = ["", "NEXTWEEK", "2026-13-45", "20261030"]


@pytest.mark.parametrize("raw", BAD_VALUES)
def test_board_and_weekplan_do_not_break_on_bad_due_date(auth_client, db_file, monkeypatch, raw):
    tid = add_with_raw_due_date(auth_client, db_file, raw)
    assert auth_client.get("/tasks").status_code == 200
    use_model(monkeypatch, plan_text(tid))
    res = auth_client.post("/tasks/weekplan")
    assert res.status_code == 200
    assert res.json()["days"] == [{"date": "2026-10-28", "task_ids": [tid]}]
