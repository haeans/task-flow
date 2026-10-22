import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import sign_in

PROTECTED = [
    ("GET", "/tasks", None),
    ("POST", "/tasks", {"title": "a"}),
    ("PUT", "/tasks/1", {"title": "a"}),
    ("PATCH", "/tasks/1/status", {"status": "DONE"}),
    ("DELETE", "/tasks/1", None),
]


@pytest.fixture
def two_users(db_file):
    """A와 B가 각자 로그인한 두 클라이언트. 쿠키 보관함이 따로다."""
    with TestClient(app) as a, TestClient(app) as b:
        sign_in(a, "usera01")
        sign_in(b, "userb01")
        yield a, b


def _titles(c):
    return [t["title"] for t in c.get("/tasks").json()]


def _db_rows(db_file):
    with sqlite3.connect(db_file) as c:
        return c.execute("SELECT id, title, description, status, owner_id FROM tasks").fetchall()


# --- M1, 사례 ①: 로그인하지 않은 카드 요청은 모두 401 ---


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_every_task_request_without_login_is_401(client, db_file, method, path, body):
    res = client.request(method, path, json=body)
    assert res.status_code == 401
    assert _db_rows(db_file) == []


def test_unauthenticated_list_returns_no_cards(two_users, client):
    a, _ = two_users
    a.post("/tasks", json={"title": "A의 카드"})
    res = client.get("/tasks")
    assert res.status_code == 401
    assert "A의 카드" not in res.text


# --- 목록 분리 ---


def test_list_shows_only_own_cards(two_users):
    a, b = two_users
    a.post("/tasks", json={"title": "A1"})
    a.post("/tasks", json={"title": "A2"})
    b.post("/tasks", json={"title": "B1"})
    assert sorted(_titles(a)) == ["A1", "A2"]
    assert _titles(b) == ["B1"]


def test_card_stays_owned_after_logout_and_login(two_users):
    a, _ = two_users
    a.post("/tasks", json={"title": "A1"})
    a.delete("/sessions")
    assert a.post("/sessions", json={"username": "usera01", "password": "password123"}).status_code == 201
    assert _titles(a) == ["A1"]


def test_cards_before_login_feature_are_invisible(db_file, client):
    # 로그인 도입 전에 있던 카드(owner_id 없음)는 어느 사용자에게도 보이지 않는다 (D-028, S-56).
    with sqlite3.connect(db_file) as c:
        c.execute(
            "INSERT INTO tasks (title, status, created_at, updated_at) VALUES ('옛 카드', 'TODO', 't', 't')"
        )
    sign_in(client)
    assert client.get("/tasks").json() == []
    assert client.patch("/tasks/1/status", json={"status": "DONE"}).status_code == 404
    assert client.delete("/tasks/1").status_code == 404
    assert len(_db_rows(db_file)) == 1


# --- M5: 소유자 값은 요청으로 정하지 못한다 ---


def test_create_ignores_owner_in_request(two_users, db_file):
    a, b = two_users
    res = a.post("/tasks", json={"title": "A의 카드", "owner_id": 2, "owner": "userb01"})
    assert res.status_code == 201
    assert _titles(a) == ["A의 카드"]
    assert _titles(b) == []
    with sqlite3.connect(db_file) as c:
        owner = c.execute("SELECT owner_id FROM tasks").fetchone()[0]
        a_id = c.execute("SELECT id FROM users WHERE username = 'usera01'").fetchone()[0]
    assert owner == a_id


def test_task_response_has_no_owner_or_hash(two_users, db_file):
    a, _ = two_users
    res = a.post("/tasks", json={"title": "x"})
    assert "owner_id" not in res.json()
    assert "owner_id" not in a.get("/tasks").json()[0]
    assert "argon2" not in res.text
    assert "argon2" not in a.get("/tasks").text


# --- M4, 사례 ②: 남의 카드는 404, 카드는 그대로 ---


def test_other_users_card_cannot_be_updated_status_changed_or_deleted(two_users, db_file):
    a, b = two_users
    card = a.post("/tasks", json={"title": "A의 카드", "description": "설명"}).json()
    before = _db_rows(db_file)
    url = f"/tasks/{card['id']}"

    assert b.put(url, json={"title": "해킹", "description": "x"}).status_code == 404
    assert b.patch(f"{url}/status", json={"status": "DONE"}).status_code == 404
    assert b.delete(url).status_code == 404

    assert _db_rows(db_file) == before
    assert _titles(a) == ["A의 카드"]


def test_other_users_card_404_is_same_as_missing_card(two_users):
    a, b = two_users
    card = a.post("/tasks", json={"title": "A"}).json()
    theirs = b.put(f"/tasks/{card['id']}", json={"title": "x"})
    missing = b.put("/tasks/9999", json={"title": "x"})
    assert theirs.status_code == missing.status_code == 404
    assert theirs.json() == missing.json()


# --- 사례 ③: 자기 카드 수정 ---


def test_owner_can_update_own_card(two_users):
    a, _ = two_users
    card = a.post("/tasks", json={"title": "원래"}).json()
    a.patch(f"/tasks/{card['id']}/status", json={"status": "DONE"})
    res = a.put(f"/tasks/{card['id']}", json={"title": "새 제목", "description": "새 설명"})
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "새 제목"
    assert body["status"] == "DONE"
    assert body["updated_at"] > card["updated_at"]
    assert "owner_id" not in body


# --- 사례 ④와 검사 순서: 로그인 → 소유자 → 입력 ---


def test_own_card_blank_title_is_422_and_card_unchanged(two_users):
    a, _ = two_users
    card = a.post("/tasks", json={"title": "원래"}).json()
    assert a.put(f"/tasks/{card['id']}", json={"title": ""}).status_code == 422
    assert a.put(f"/tasks/{card['id']}", json={"title": "   "}).status_code == 422
    assert a.put(f"/tasks/{card['id']}", json={}).status_code == 422
    assert _titles(a) == ["원래"]


def test_order_login_first_unauthenticated_with_blank_title_is_401(client):
    assert client.post("/tasks", json={"title": ""}).status_code == 401
    assert client.put("/tasks/1", json={"title": ""}).status_code == 401
    assert client.patch("/tasks/1/status", json={"status": "BAD"}).status_code == 401


def test_order_owner_before_input_other_users_card_with_bad_input_is_404(two_users, db_file):
    a, b = two_users
    card = a.post("/tasks", json={"title": "A의 카드"}).json()
    before = _db_rows(db_file)
    url = f"/tasks/{card['id']}"
    # 빈 제목·길이 초과·허용 밖 상태 값이라도 남의 카드면 404이다 (카드가 있다는 사실을 알려 주지 않는다).
    assert b.put(url, json={"title": ""}).status_code == 404
    assert b.put(url, json={"title": "가" * 101}).status_code == 404
    assert b.patch(f"{url}/status", json={"status": "BAD"}).status_code == 404
    assert _db_rows(db_file) == before


def test_order_missing_card_with_bad_input_is_404(auth_client):
    assert auth_client.put("/tasks/9999", json={"title": ""}).status_code == 404
    assert auth_client.patch("/tasks/9999/status", json={"status": "BAD"}).status_code == 404


# --- M2·M10: 끝난 로그인으로는 카드를 못 본다 ---


def test_cards_not_visible_after_logout(two_users):
    a, _ = two_users
    a.post("/tasks", json={"title": "A1"})
    cookie = a.cookies.get("session")
    a.delete("/sessions")
    a.cookies.set("session", cookie)
    assert a.get("/tasks").status_code == 401
