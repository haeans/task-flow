import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import sign_in, upgrade_db


@pytest.fixture
def client(auth_client):
    """이 파일의 카드 규칙 테스트는 모두 로그인한 사용자로 한다."""
    return auth_client


def _restart(c):
    """서버를 다시 켠 것처럼 새 클라이언트를 만들고, 같은 로그인 쿠키를 보낸다 (DB의 세션은 그대로)."""
    cookie = c.cookies.get("session")
    new = TestClient(app)
    new.cookies.set("session", cookie)
    return new


def test_list_empty(client):
    res = client.get("/tasks")
    assert res.status_code == 200
    assert res.json() == []


def test_create_returns_todo_card_with_times(client):
    res = client.post("/tasks", json={"title": "  첫 카드  ", "description": "설명"})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "첫 카드"
    assert body["description"] == "설명"
    assert body["status"] == "TODO"
    assert body["created_at"] == body["updated_at"]


def test_create_description_optional(client):
    res = client.post("/tasks", json={"title": "제목만"})
    assert res.status_code == 201
    assert res.json()["description"] == ""


def test_create_rejects_blank_title(client):
    for title in ["", "   "]:
        assert client.post("/tasks", json={"title": title}).status_code == 422
    assert client.get("/tasks").json() == []


def test_create_length_limits(client):
    assert client.post("/tasks", json={"title": "가" * 100}).status_code == 201
    assert client.post("/tasks", json={"title": "가" * 101}).status_code == 422
    assert client.post("/tasks", json={"title": "a", "description": "나" * 1000}).status_code == 201
    assert client.post("/tasks", json={"title": "a", "description": "나" * 1001}).status_code == 422


def test_create_ignores_client_supplied_status_and_times(client):
    res = client.post(
        "/tasks",
        json={"title": "a", "status": "DONE", "created_at": "2000-01-01T00:00:00Z"},
    )
    body = res.json()
    assert body["status"] == "TODO"
    assert body["created_at"] != "2000-01-01T00:00:00Z"


def test_list_same_priority_and_no_due_date_is_id_ascending(client):
    # 최신순(D-017)은 정렬 규칙(R-014)으로 대체되었다. 앞 기준이 모두 같으면 ID 오름차순이다.
    client.post("/tasks", json={"title": "먼저"})
    client.post("/tasks", json={"title": "나중"})
    titles = [t["title"] for t in client.get("/tasks").json()]
    assert titles == ["먼저", "나중"]


def test_data_survives_restart(db_file):
    with TestClient(app) as c:
        sign_in(c)
        c.post("/tasks", json={"title": "남아야 함"})
        with _restart(c) as c2:
            assert [t["title"] for t in c2.get("/tasks").json()] == ["남아야 함"]


def test_unreadable_storage_returns_error(db_file):
    with TestClient(app, raise_server_exceptions=False) as c:
        sign_in(c)
        db_file.write_bytes(b"this is not a sqlite database" * 50)
        res = c.get("/tasks")
    assert res.status_code == 500


def _make(client, title="카드"):
    return client.post("/tasks", json={"title": title}).json()


def test_status_change_any_direction(client):
    task = _make(client)
    for status in ["IN_PROGRESS", "DONE", "TODO", "DONE", "IN_PROGRESS"]:
        res = client.patch(f"/tasks/{task['id']}/status", json={"status": status})
        assert res.status_code == 200
        assert res.json()["status"] == status
    assert client.get("/tasks").json()[0]["status"] == "IN_PROGRESS"


def test_status_change_keeps_other_fields_and_updated_at(client):
    task = _make(client)
    body = client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"}).json()
    assert body["title"] == task["title"]
    assert body["created_at"] == task["created_at"]
    assert body["updated_at"] == task["updated_at"]


def test_status_change_does_not_touch_other_cards(client):
    a, b = _make(client, "a"), _make(client, "b")
    client.patch(f"/tasks/{a['id']}/status", json={"status": "DONE"})
    by_id = {t["id"]: t["status"] for t in client.get("/tasks").json()}
    assert by_id == {a["id"]: "DONE", b["id"]: "TODO"}


def test_status_change_rejects_invalid_value(client):
    task = _make(client)
    for bad in ["done", "BLOCKED", "", None]:
        res = client.patch(f"/tasks/{task['id']}/status", json={"status": bad})
        assert res.status_code == 422
    assert client.get("/tasks").json()[0]["status"] == "TODO"


def test_status_change_missing_card_is_404(client):
    res = client.patch("/tasks/999/status", json={"status": "DONE"})
    assert res.status_code == 404


def test_status_persists_across_restart(db_file):
    with TestClient(app) as c:
        sign_in(c)
        task = _make(c)
        c.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"})
        with _restart(c) as c2:
            assert c2.get("/tasks").json()[0]["status"] == "DONE"


def test_update_changes_title_description_and_updated_at_only(client):
    task = _make(client)
    client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"})
    res = client.put(f"/tasks/{task['id']}", json={"title": " 새 제목 ", "description": "새 설명"})
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "새 제목"
    assert body["description"] == "새 설명"
    assert body["status"] == "DONE"
    assert body["created_at"] == task["created_at"]
    assert body["updated_at"] > task["updated_at"]


def test_update_rejects_blank_title_and_keeps_card(client):
    task = _make(client, "원래")
    for title in ["", "   "]:
        assert client.put(f"/tasks/{task['id']}", json={"title": title}).status_code == 422
    assert client.get("/tasks").json()[0]["title"] == "원래"


def test_update_length_limits(client):
    task = _make(client)
    url = f"/tasks/{task['id']}"
    assert client.put(url, json={"title": "가" * 101}).status_code == 422
    assert client.put(url, json={"title": "a", "description": "나" * 1001}).status_code == 422


def test_update_ignores_status_in_body(client):
    task = _make(client)
    res = client.put(f"/tasks/{task['id']}", json={"title": "a", "status": "DONE"})
    assert res.json()["status"] == "TODO"


def test_update_missing_card_is_404(client):
    assert client.put("/tasks/999", json={"title": "a"}).status_code == 404


def test_delete_removes_card_and_persists(db_file):
    with TestClient(app) as c:
        sign_in(c)
        a, b = _make(c, "a"), _make(c, "b")
        assert c.delete(f"/tasks/{a['id']}").status_code == 204
        assert [t["id"] for t in c.get("/tasks").json()] == [b["id"]]
        with _restart(c) as c2:
            assert [t["id"] for t in c2.get("/tasks").json()] == [b["id"]]


def test_delete_missing_card_is_404(client):
    assert client.delete("/tasks/999").status_code == 404
    task = _make(client)
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.delete(f"/tasks/{task['id']}").status_code == 404


def test_create_on_unreadable_storage_fails_without_success(db_file):
    with TestClient(app, raise_server_exceptions=False) as c:
        sign_in(c)
        db_file.write_bytes(b"this is not a sqlite database" * 50)
        res = c.post("/tasks", json={"title": "저장되면 안 됨"})
    assert res.status_code == 500


def test_recovers_after_storage_is_fixed_without_restart(db_file):
    with TestClient(app, raise_server_exceptions=False) as c:
        sign_in(c)
        db_file.write_bytes(b"this is not a sqlite database" * 50)
        assert c.get("/tasks").status_code == 500
        db_file.unlink()  # 원인이 풀린다 (테스트용 임시 폴더의 파일)
        upgrade_db()  # 스키마는 alembic이 만든다. 서버 재시작은 필요 없다.
        # 새 저장소에는 예전 로그인 정보가 없으므로 다시 가입·로그인해야 한다.
        assert c.get("/tasks").status_code == 401
        sign_in(c)
        assert c.get("/tasks").json() == []
        assert c.post("/tasks", json={"title": "복구 뒤 등록"}).status_code == 201
