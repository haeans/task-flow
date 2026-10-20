from fastapi.testclient import TestClient

from app.main import app


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


def test_list_newest_first(client):
    client.post("/tasks", json={"title": "먼저"})
    client.post("/tasks", json={"title": "나중"})
    titles = [t["title"] for t in client.get("/tasks").json()]
    assert titles == ["나중", "먼저"]


def test_data_survives_restart(db_file):
    with TestClient(app) as c:
        c.post("/tasks", json={"title": "남아야 함"})
    with TestClient(app) as c:
        assert [t["title"] for t in c.get("/tasks").json()] == ["남아야 함"]


def test_unreadable_storage_returns_error(db_file):
    db_file.write_bytes(b"this is not a sqlite database" * 50)
    with TestClient(app, raise_server_exceptions=False) as c:
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
        task = _make(c)
        c.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"})
    with TestClient(app) as c:
        assert c.get("/tasks").json()[0]["status"] == "DONE"
