import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import tasks as tasks_route
from tests.conftest import sign_in

TODAY = "2026-10-27"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """"오늘"을 고정한다. 날짜 경계 테스트가 실행 날짜에 흔들리지 않게 한다."""
    monkeypatch.setattr(tasks_route, "_today", lambda: TODAY)


@pytest.fixture
def client(auth_client):
    return auth_client


def _make(c, title="카드", **extra):
    res = c.post("/tasks", json={"title": title, **extra})
    assert res.status_code == 201, res.text
    return res.json()


def _titles(c):
    return [t["title"] for t in c.get("/tasks").json()]


# --- R-011 우선순위 ---


def test_priority_defaults_to_normal_and_due_date_to_null(client):
    body = _make(client)
    assert body["priority"] == "NORMAL"
    assert body["due_date"] is None
    assert body["overdue"] is False


@pytest.mark.parametrize("p", ["LOW", "NORMAL", "HIGH"])
def test_create_accepts_each_priority(client, p):
    assert _make(client, priority=p)["priority"] == p


@pytest.mark.parametrize("bad", ["URGENT", "high", "", None, 1])
def test_create_rejects_bad_priority(client, bad):
    assert client.post("/tasks", json={"title": "a", "priority": bad}).status_code == 422
    assert client.get("/tasks").json() == []


def test_update_changes_priority_and_persists(client):
    task = _make(client)
    res = client.put(f"/tasks/{task['id']}", json={"title": "a", "priority": "HIGH"})
    assert res.status_code == 200
    assert res.json()["priority"] == "HIGH"
    assert client.get("/tasks").json()[0]["priority"] == "HIGH"


@pytest.mark.parametrize("bad", ["URGENT", None])
def test_update_rejects_bad_or_null_priority_and_keeps_card(client, bad):
    task = _make(client, priority="LOW")
    res = client.put(f"/tasks/{task['id']}", json={"title": "b", "priority": bad})
    assert res.status_code == 422
    after = client.get("/tasks").json()[0]
    assert after["priority"] == "LOW" and after["title"] == "카드"


# --- R-012 마감일 ---


def test_create_with_due_date_and_update_and_clear(client):
    task = _make(client, due_date="2026-11-01")
    assert task["due_date"] == "2026-11-01"
    url = f"/tasks/{task['id']}"
    assert client.put(url, json={"title": "a", "due_date": "2026-12-31"}).json()["due_date"] == "2026-12-31"
    assert client.get("/tasks").json()[0]["due_date"] == "2026-12-31"
    assert client.put(url, json={"title": "a", "due_date": None}).json()["due_date"] is None
    assert client.get("/tasks").json()[0]["due_date"] is None


@pytest.mark.parametrize(
    "bad", ["2026-02-30", "2026-13-01", "20261027", "2026-1-5", "", " ", "2026-10-27T10:00", "내일", 20261027]
)
def test_rejects_bad_due_date(client, bad):
    assert client.post("/tasks", json={"title": "a", "due_date": bad}).status_code == 422
    task = _make(client, due_date="2026-11-01")
    res = client.put(f"/tasks/{task['id']}", json={"title": "a", "due_date": bad})
    assert res.status_code == 422
    assert client.get("/tasks").json()[0]["due_date"] == "2026-11-01"


def test_past_due_date_is_accepted(client):
    assert _make(client, due_date="2000-01-01")["overdue"] is True


def test_update_without_priority_and_due_date_keeps_them(client):
    task = _make(client, priority="HIGH", due_date="2026-11-01")
    body = client.put(f"/tasks/{task['id']}", json={"title": "새 제목"}).json()
    assert body["priority"] == "HIGH"
    assert body["due_date"] == "2026-11-01"


def test_update_only_due_date_keeps_priority(client):
    task = _make(client, priority="HIGH")
    body = client.put(f"/tasks/{task['id']}", json={"title": "a", "due_date": "2026-11-01"}).json()
    assert body["priority"] == "HIGH"


def test_title_rules_still_apply_with_new_fields(client):
    task = _make(client)
    url = f"/tasks/{task['id']}"
    assert client.put(url, json={"title": "  ", "priority": "HIGH"}).status_code == 422
    assert client.put(url, json={"title": "가" * 101, "due_date": "2026-11-01"}).status_code == 422
    assert client.put(url, json={"title": "a", "description": "나" * 1001}).status_code == 422


# --- Q-021: 수정 시각 ---


def test_update_of_priority_or_due_date_refreshes_updated_at(client):
    task = _make(client)
    body = client.put(f"/tasks/{task['id']}", json={"title": "카드", "priority": "HIGH"}).json()
    assert body["updated_at"] > task["updated_at"]
    assert body["created_at"] == task["created_at"]


# --- 상태 변경은 새 항목을 바꾸지 않는다 (D-004, D-021) ---


def test_status_change_keeps_priority_due_date_and_updated_at(client):
    task = _make(client, priority="HIGH", due_date="2026-11-01")
    body = client.patch(f"/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"}).json()
    assert body["priority"] == "HIGH"
    assert body["due_date"] == "2026-11-01"
    assert body["updated_at"] == task["updated_at"]


# --- R-013 기한 초과 판정표 ---


@pytest.mark.parametrize(
    "due,status,expected",
    [
        ("2026-10-26", "TODO", True),
        ("2026-10-26", "IN_PROGRESS", True),
        ("2026-10-26", "DONE", False),
        (TODAY, "TODO", False),
        (TODAY, "DONE", False),
        ("2026-10-28", "TODO", False),
        ("2026-10-28", "DONE", False),
        (None, "TODO", False),
        (None, "DONE", False),
    ],
)
def test_overdue_table(client, due, status, expected):
    task = _make(client, due_date=due)
    client.patch(f"/tasks/{task['id']}/status", json={"status": status})
    assert client.get("/tasks").json()[0]["overdue"] is expected


def test_overdue_does_not_change_status(client):
    task = _make(client, due_date="2000-01-01")
    listed = client.get("/tasks").json()[0]
    assert listed["overdue"] is True and listed["status"] == "TODO"
    assert client.get("/tasks").json()[0]["status"] == "TODO"
    assert task["status"] == "TODO"


def test_moving_to_done_clears_overdue_and_back_restores(client):
    task = _make(client, due_date="2000-01-01")
    url = f"/tasks/{task['id']}/status"
    assert client.patch(url, json={"status": "DONE"}).json()["overdue"] is False
    assert client.patch(url, json={"status": "TODO"}).json()["overdue"] is True


# --- R-014 정렬 ---


def test_sort_overdue_first_then_priority_then_due_date_then_id(client):
    _make(client, "보통-마감없음")  # 1
    _make(client, "낮음-마감없음", priority="LOW")  # 2
    _make(client, "높음-마감없음", priority="HIGH")  # 3
    _make(client, "보통-내일", due_date="2026-10-28")  # 4
    _make(client, "보통-다음주", due_date="2026-11-03")  # 5
    _make(client, "낮음-지남", priority="LOW", due_date="2026-10-20")  # 6
    _make(client, "높음-어제지남", priority="HIGH", due_date="2026-10-26")  # 7
    _make(client, "보통-오늘", due_date=TODAY)  # 8: 당일은 기한 초과가 아니다
    _make(client, "보통-마감없음2")  # 9
    assert _titles(client) == [
        "높음-어제지남",  # 기한 초과, HIGH
        "낮음-지남",  # 기한 초과, LOW
        "높음-마감없음",  # HIGH
        "보통-오늘",  # NORMAL, 마감일 빠른 순
        "보통-내일",
        "보통-다음주",
        "보통-마감없음",  # NORMAL, 마감일 없음은 뒤, ID 오름차순
        "보통-마감없음2",
        "낮음-마감없음",  # LOW
    ]


def test_sort_overdue_cards_oldest_due_date_first_within_same_priority(client):
    _make(client, "최근", due_date="2026-10-26")
    _make(client, "오래됨", due_date="2026-10-01")
    assert _titles(client) == ["오래됨", "최근"]


def test_done_card_with_past_due_date_is_not_ranked_as_overdue(client):
    done = _make(client, "완료", priority="LOW", due_date="2026-10-01")
    _make(client, "일반", priority="NORMAL")
    client.patch(f"/tasks/{done['id']}/status", json={"status": "DONE"})
    assert _titles(client) == ["일반", "완료"]


def test_sort_does_not_change_card_content_or_status(client):
    a = _make(client, "a", priority="LOW")
    b = _make(client, "b", priority="HIGH", due_date="2000-01-01")
    client.patch(f"/tasks/{a['id']}/status", json={"status": "DONE"})
    by_id = {t["id"]: t for t in client.get("/tasks").json()}
    assert by_id[a["id"]]["status"] == "DONE" and by_id[a["id"]]["title"] == "a"
    assert by_id[b["id"]]["status"] == "TODO" and by_id[b["id"]]["updated_at"] == b["updated_at"]


# --- 소유자 분리와 응답 (R-010, M14, M8) ---


def test_other_users_card_with_new_fields_is_404_and_unchanged(db_file):
    with TestClient(app) as a, TestClient(app) as b:
        sign_in(a, "usera01")
        sign_in(b, "userb01")
        card = _make(a, "A의 카드", priority="LOW", due_date="2026-11-01")
        res = b.put(
            f"/tasks/{card['id']}",
            json={"title": "탈취", "priority": "HIGH", "due_date": None},
        )
        assert res.status_code == 404
        after = a.get("/tasks").json()[0]
        assert (after["title"], after["priority"], after["due_date"]) == ("A의 카드", "LOW", "2026-11-01")
        assert b.get("/tasks").json() == []


def test_sorting_and_overdue_stay_within_own_cards(db_file):
    with TestClient(app) as a, TestClient(app) as b:
        sign_in(a, "usera01")
        sign_in(b, "userb01")
        _make(a, "A", due_date="2000-01-01")
        _make(b, "B")
        assert _titles(a) == ["A"]
        assert _titles(b) == ["B"]


def test_responses_have_no_owner_or_hash(client):
    body = _make(client)
    text = client.get("/tasks").text + str(body)
    assert "owner" not in text and "hash" not in text


def test_task_without_login_is_401_with_new_fields(client, db_file):
    with TestClient(app) as anon:
        assert anon.post("/tasks", json={"title": "a", "priority": "HIGH"}).status_code == 401
        assert anon.post("/tasks", json={"title": "", "priority": "BAD"}).status_code == 401
