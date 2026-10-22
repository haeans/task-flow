import sqlite3
from datetime import timedelta

import pytest
from fastapi import Depends

from app import security
from app.main import app
from app.security import AuthUser, get_current_user

PASSWORD = "password123"


@pytest.fixture(autouse=True)
def probe_route():
    """로그인 확인(get_current_user)만 쓰는 테스트 전용 경로. 카드 보호는 다른 테스트에서 본다."""

    def probe(user: AuthUser = Depends(get_current_user)) -> dict[str, str]:
        return {"username": user.username}

    app.add_api_route("/_probe", probe, methods=["GET"])
    yield
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/_probe"]


def signup(client, username="alice1", password=PASSWORD):
    return client.post("/users", json={"username": username, "password": password})


def login(client, username="alice1", password=PASSWORD):
    return client.post("/sessions", json={"username": username, "password": password})


def _all_text(db_file) -> str:
    with sqlite3.connect(db_file) as c:
        return c.execute("SELECT password_hash FROM users").fetchone()[0]


# --- 가입 ---


def test_signup_returns_201_with_id_and_username_only(client, db_file):
    res = signup(client)
    assert res.status_code == 201
    assert set(res.json()) == {"id", "username"}
    assert res.json()["username"] == "alice1"
    # 해시값이 어떤 형태로도 응답에 없다.
    assert _all_text(db_file) not in res.text
    assert "password" not in res.text.lower()


def test_signup_does_not_log_in(client):
    res = signup(client)
    assert "set-cookie" not in res.headers
    assert client.get("/_probe").status_code == 401


def test_signup_stores_argon2_hash_not_plain_password(client, db_file):
    signup(client)
    stored = _all_text(db_file)
    assert stored.startswith("$argon2")
    assert PASSWORD not in stored


def test_signup_duplicate_username_is_409(client, db_file):
    assert signup(client).status_code == 201
    assert signup(client, password="another-pass1").status_code == 409
    with sqlite3.connect(db_file) as c:
        assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


@pytest.mark.parametrize(
    "username,ok",
    [
        ("abc", False),
        ("abcd", True),
        ("a" * 20, True),
        ("a" * 21, False),
        ("한글아이디", False),
        ("abc_def", False),
        ("abc def", False),
        ("abcd\n", False),
        ("", False),
    ],
)
def test_signup_username_rules(client, username, ok):
    res = signup(client, username=username)
    assert res.status_code == (201 if ok else 422)


@pytest.mark.parametrize(
    "password,ok",
    [("1234567", False), ("12345678", True), ("p" * 100, True), ("p" * 101, False), ("", False)],
)
def test_signup_password_rules(client, password, ok):
    res = signup(client, password=password)
    assert res.status_code == (201 if ok else 422)


def test_signup_missing_fields_is_422(client):
    assert client.post("/users", json={}).status_code == 422
    assert client.post("/users", json={"username": "alice1"}).status_code == 422


# --- 로그인 ---


def test_login_sets_cookie_with_required_attributes(client):
    signup(client)
    res = login(client)
    assert res.status_code == 201
    assert set(res.json()) == {"id", "username"}
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "max-age=86400" in cookie
    assert "secure" not in cookie


def test_login_response_has_no_hash(client, db_file):
    signup(client)
    res = login(client)
    assert _all_text(db_file) not in res.text
    assert PASSWORD not in res.text


def test_cookie_holds_signed_session_id_stored_in_sessions(client, db_file):
    signup(client)
    login(client)
    value = client.cookies.get(security.COOKIE_NAME)
    session_id = security.unsign(value)
    assert session_id is not None
    assert len(session_id) >= 43  # 32바이트의 urlsafe 표현
    with sqlite3.connect(db_file) as c:
        assert c.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", (session_id,)).fetchone()[0] == 1


def test_login_failure_is_401_with_same_message_for_both_causes(client):
    signup(client)
    wrong_password = login(client, password="wrong-password")
    wrong_username = login(client, username="nobody1")
    assert wrong_password.status_code == 401
    assert wrong_username.status_code == 401
    assert wrong_password.json() == wrong_username.json()
    assert "set-cookie" not in wrong_password.headers


def test_login_while_logged_in_issues_new_session(client, db_file):
    signup(client)
    login(client)
    first = client.cookies.get(security.COOKIE_NAME)
    login(client)
    second = client.cookies.get(security.COOKIE_NAME)
    assert first != second
    assert client.get("/_probe").status_code == 200
    with sqlite3.connect(db_file) as c:
        assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 2


def test_login_persists_across_requests(client):
    signup(client)
    login(client)
    assert client.get("/_probe").status_code == 200
    assert client.get("/_probe").status_code == 200


# --- 로그아웃 ---


def test_logout_is_204_and_ends_session(client, db_file):
    signup(client)
    login(client)
    cookie = client.cookies.get(security.COOKIE_NAME)
    assert client.delete("/sessions").status_code == 204
    with sqlite3.connect(db_file) as c:
        assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    # 같은 세션 번호를 다시 보내도 401 (M2)
    client.cookies.set(security.COOKIE_NAME, cookie)
    assert client.get("/_probe").status_code == 401


def test_logout_without_login_is_401(client):
    assert client.delete("/sessions").status_code == 401


# --- 막을 요청: 쿠키 변조·만료 ---


def test_tampered_signature_is_401(client):
    signup(client)
    login(client)
    value = client.cookies.get(security.COOKIE_NAME)
    session_id, _, signature = value.rpartition(".")
    flipped = ("0" if signature[0] != "0" else "1") + signature[1:]
    client.cookies.set(security.COOKIE_NAME, f"{session_id}.{flipped}")
    assert client.get("/_probe").status_code == 401


def test_unsigned_or_unknown_session_is_401(client):
    signup(client)
    login(client)
    value = client.cookies.get(security.COOKIE_NAME)
    session_id = value.rpartition(".")[0]
    client.cookies.set(security.COOKIE_NAME, session_id)  # 서명 없음
    assert client.get("/_probe").status_code == 401
    # 서명은 맞지만 sessions에 없는 번호
    client.cookies.set(security.COOKIE_NAME, security.sign("not-in-sessions"))
    assert client.get("/_probe").status_code == 401


def test_session_expires_after_86400_seconds(client, db_file, monkeypatch):
    signup(client)
    login(client)
    start = security.now()
    monkeypatch.setattr(security, "now", lambda: start + timedelta(seconds=86399))
    assert client.get("/_probe").status_code == 200
    monkeypatch.setattr(security, "now", lambda: start + timedelta(seconds=86401))
    assert client.get("/_probe").status_code == 401
    # 끝난 세션의 행은 조회될 때 지운다.
    with sqlite3.connect(db_file) as c:
        assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_expiry_counts_from_login_not_from_last_use(client, monkeypatch):
    signup(client)
    login(client)
    start = security.now()
    monkeypatch.setattr(security, "now", lambda: start + timedelta(seconds=80000))
    assert client.get("/_probe").status_code == 200  # 사용해도 연장되지 않는다
    monkeypatch.setattr(security, "now", lambda: start + timedelta(seconds=86401))
    assert client.get("/_probe").status_code == 401


# --- 비밀값 ---


def test_missing_session_secret_fails_login(client, monkeypatch):
    signup(client)
    monkeypatch.delenv("SESSION_SECRET")
    # .env가 없어도(또는 비어 있어도) 기본값으로 동작하지 않는다.
    with pytest.raises(RuntimeError):
        login(client)
