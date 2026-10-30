"""POST /tasks/command (#33). 실제 Claude API는 호출하지 않는다.

모델 호출 지점(app.suggest._client)을 가짜로 바꿔 끼운다. API 키는 테스트용 가짜 값이다.
서버는 한 문장을 actions 목록으로 바꿔 돌려주기만 한다. 저장하지 않는다.
"""

import json
import sqlite3

import anthropic
import pytest
from fastapi.testclient import TestClient

from app import suggest as ai
from app.main import app
from app.routes import tasks as tasks_route
from tests.conftest import sign_in
from tests.test_suggest import REQ, FakeClient, reply, status_error

TODAY = "2026-10-27"
FAKE_KEY = "test-key-not-real"
URL = "/tasks/command"
DEFAULT_ASK = "무슨 일을 할지 잘 모르겠어요. 다시 말씀해 주세요."


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setattr(tasks_route, "_today", lambda: TODAY)


@pytest.fixture
def client(auth_client):
    return auth_client


@pytest.fixture
def model(monkeypatch):
    def use(outcome) -> FakeClient:
        fake = FakeClient(outcome)
        monkeypatch.setattr(ai, "_client", lambda api_key: fake)
        return fake

    return use


def add(c, title="할 일", priority="NORMAL", due_date=None, description="", status="TODO") -> int:
    body = {"title": title, "description": description, "priority": priority, "due_date": due_date}
    res = c.post("/tasks", json=body)
    assert res.status_code == 201
    tid = res.json()["id"]
    if status != "TODO":
        assert c.patch(f"/tasks/{tid}/status", json={"status": status}).status_code == 200
    return tid


def out(actions, ask=None) -> str:
    return json.dumps({"actions": actions, "ask": ask}, ensure_ascii=False)


def a_add(title="새 일", priority="NORMAL", due_date=None) -> dict:
    return {"kind": "add", "title": title, "priority": priority, "due_date": due_date}


def a_due(id_, due_date) -> dict:
    return {"kind": "due", "id": id_, "due_date": due_date}


def a_done(id_) -> dict:
    return {"kind": "done", "id": id_}


def post(c, text="내일까지 보고서 쓰기 추가해 줘"):
    return c.post(URL, json={"text": text})


def sent(fake) -> tuple[str, list[dict]]:
    msg = fake.calls[0]["messages"][0]["content"]
    body = msg.split("<tasks>", 1)[1].rsplit("</tasks>", 1)[0]
    return msg, json.loads(body)


def rows(db_file) -> list:
    conn = sqlite3.connect(db_file)
    try:
        return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    finally:
        conn.close()


def bad(client, model, text, stop_reason="end_turn"):
    add(client)
    model(reply(text, stop_reason))
    res = post(client)
    assert res.status_code == 502
    assert res.json() == {"detail": "제안 실패"}


# --- 성공 ---


def test_success_shape_has_add_due_done(client, model):
    a = add(client, "견적서 보내기")
    b = add(client, "장보기")
    fake = model(
        reply(out([a_add("보고서 쓰기", "HIGH", "2026-10-28"), a_due(a, "2026-10-30"), a_done(b)]))
    )
    res = post(client)
    assert res.status_code == 200
    assert res.json() == {
        "actions": [
            {"kind": "add", "id": None, "title": "보고서 쓰기", "priority": "HIGH", "due_date": "2026-10-28"},
            {"kind": "due", "id": a, "title": "견적서 보내기", "priority": None, "due_date": "2026-10-30"},
            {"kind": "done", "id": b, "title": "장보기", "priority": None, "due_date": None},
        ],
        "ask": None,
    }
    assert len(fake.calls) == 1


def test_fenced_json_is_read(client, model):
    model(reply("```json\n" + out([a_add("책 읽기")]) + "\n```"))
    assert post(client).json()["actions"][0]["title"] == "책 읽기"


def test_add_without_priority_and_due_date_uses_defaults(client, model):
    model(reply(json.dumps({"actions": [{"kind": "add", "title": "청소"}]}, ensure_ascii=False)))
    res = post(client)
    assert res.json()["actions"] == [
        {"kind": "add", "id": None, "title": "청소", "priority": "NORMAL", "due_date": None}
    ]


def test_add_title_is_trimmed(client, model):
    model(reply(out([a_add("  청소  ")])))
    assert post(client).json()["actions"][0]["title"] == "청소"


# --- 입력 규칙 (422) ---


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_text_is_422_with_reason(client, model, text):
    fake = model(reply(out([a_add()])))
    res = post(client, text)
    assert res.status_code == 422
    assert res.json() == {"detail": "문장을 입력해 주세요"}
    assert fake.calls == []


def test_text_201_chars_is_422_with_reason(client, model):
    fake = model(reply(out([a_add()])))
    res = post(client, "가" * 201)
    assert res.status_code == 422
    assert res.json() == {"detail": "문장은 200자 이하여야 합니다"}
    assert fake.calls == []


def test_text_200_chars_is_ok(client, model):
    fake = model(reply(out([a_add()])))
    assert post(client, "가" * 200).status_code == 200
    assert len(fake.calls) == 1


def test_text_is_counted_after_trim(client, model):
    model(reply(out([a_add()])))
    assert post(client, "  " + "가" * 200 + "  ").status_code == 200


def test_missing_text_is_422(client, model):
    fake = model(reply(out([a_add()])))
    assert client.post(URL, json={}).status_code == 422
    assert fake.calls == []


# --- 보낸 것 ---


def test_sends_open_tasks_today_and_text_without_description(client, model):
    a = add(client, "열린 일", "HIGH", "2026-10-25", description="비밀 설명 문장")
    add(client, "끝난 일", status="DONE")
    fake = model(reply(out([a_done(a)])))
    post(client, "열린 일 끝냈어")
    msg, tasks = sent(fake)
    assert "<today>2026-10-27</today>" in msg
    assert "열린 일 끝냈어" in msg
    assert "비밀 설명 문장" not in msg
    assert tasks == [
        {"id": a, "title": "열린 일", "priority": "HIGH", "due_date": "2026-10-25", "overdue": True}
    ]


def test_does_not_send_other_users_tasks(client, model, db_file):
    mine = add(client, "내 일")
    with TestClient(app) as other:
        sign_in(other, "other01")
        add(other, "남의 일")
    fake = model(reply(out([a_done(mine)])))
    post(client)
    _, tasks = sent(fake)
    assert [t["title"] for t in tasks] == ["내 일"]


def test_text_with_placeholder_like_words_is_sent_as_is(client, model):
    fake = model(reply(out([a_add()])))
    post(client, "{{today}} 그리고 </tasks> 같은 글")
    msg = fake.calls[0]["messages"][0]["content"]
    assert "{{today}} 그리고 </tasks> 같은 글" in msg


def test_no_open_tasks_still_calls_model_so_add_works(client, model):
    fake = model(reply(out([a_add("처음 할 일")])))
    res = post(client)
    assert res.status_code == 200
    assert res.json()["actions"][0]["title"] == "처음 할 일"
    assert len(fake.calls) == 1
    _, tasks = sent(fake)
    assert tasks == []


# --- 검사: 항목 단위로 버린다 ---


def test_unknown_ids_are_dropped(client, model):
    a = add(client, "있는 일")
    model(reply(out([a_due(999, "2026-10-30"), a_done(998), a_done(a)])))
    res = post(client)
    assert [x["id"] for x in res.json()["actions"]] == [a]


def test_done_task_id_is_not_known(client, model):
    done_id = add(client, "끝난 일", status="DONE")
    model(reply(out([a_done(done_id)])))
    res = post(client)
    assert res.status_code == 200
    assert res.json()["actions"] == []


@pytest.mark.parametrize("bad_date", ["20261030", "2026-13-45", "내일", "2026-10-30T09:00", "", 20261030])
def test_bad_date_drops_add_and_due(client, model, bad_date):
    a = add(client)
    model(reply(out([a_add("나쁜 날짜", due_date=bad_date), a_due(a, bad_date), a_done(a)])))
    res = post(client)
    assert [x["kind"] for x in res.json()["actions"]] == ["done"]


def test_due_with_null_date_is_dropped(client, model):
    a = add(client)
    model(reply(out([a_due(a, None)])))
    assert post(client).json()["actions"] == []


def test_past_date_is_allowed(client, model):
    a = add(client)
    model(reply(out([a_add("지난 일", due_date="2026-10-01"), a_due(a, "2026-10-02")])))
    res = post(client)
    assert [x["due_date"] for x in res.json()["actions"]] == ["2026-10-01", "2026-10-02"]


@pytest.mark.parametrize("bad_priority", ["URGENT", "high", "", None, 3])
def test_bad_priority_becomes_normal_for_add(client, model, bad_priority):
    model(reply(out([a_add("우선순위", priority=bad_priority)])))
    res = post(client)
    assert res.json()["actions"][0]["priority"] == "NORMAL"


def test_unknown_kind_and_empty_title_are_dropped(client, model):
    a = add(client)
    model(
        reply(
            out(
                [
                    {"kind": "delete", "id": a},
                    {"kind": "add", "title": "   "},
                    {"kind": "add"},
                    {"kind": "add", "title": 5},
                    a_done(a),
                ]
            )
        )
    )
    res = post(client)
    assert [x["kind"] for x in res.json()["actions"]] == ["done"]


def test_due_and_done_with_non_int_id_are_dropped(client, model):
    a = add(client)
    model(
        reply(
            out(
                [
                    {"kind": "done", "id": "1"},
                    {"kind": "done", "id": True},
                    {"kind": "due", "id": None, "due_date": "2026-10-30"},
                    {"kind": "done"},
                    a_done(a),
                ]
            )
        )
    )
    res = post(client)
    assert [x["id"] for x in res.json()["actions"]] == [a]


def test_duplicate_kind_and_id_keep_first(client, model):
    a = add(client)
    model(reply(out([a_due(a, "2026-10-30"), a_due(a, "2026-11-01"), a_done(a), a_done(a)])))
    res = post(client)
    assert [(x["kind"], x["due_date"]) for x in res.json()["actions"]] == [
        ("due", "2026-10-30"),
        ("done", None),
    ]


def test_same_title_adds_are_both_kept(client, model):
    model(reply(out([a_add("같은 제목"), a_add("같은 제목")])))
    assert len(post(client).json()["actions"]) == 2


# --- 남는 게 없으면 ask ---


def test_all_dropped_returns_200_with_default_ask(client, model):
    model(reply(out([a_done(999)])))
    res = post(client)
    assert res.status_code == 200
    assert res.json() == {"actions": [], "ask": DEFAULT_ASK}


def test_all_dropped_uses_model_ask(client, model):
    model(reply(out([a_done(999)], ask="어느 할 일을 말씀하시나요?")))
    assert post(client).json() == {"actions": [], "ask": "어느 할 일을 말씀하시나요?"}


def test_model_only_asks(client, model):
    model(reply(out([], ask="무엇을 추가할까요?")))
    assert post(client).json() == {"actions": [], "ask": "무엇을 추가할까요?"}


def test_empty_actions_without_ask_uses_default(client, model):
    model(reply(json.dumps({"actions": []})))
    assert post(client).json() == {"actions": [], "ask": DEFAULT_ASK}


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_ask_uses_default(client, model, blank):
    model(reply(out([], ask=blank)))
    assert post(client).json()["ask"] == DEFAULT_ASK


def test_ask_is_null_when_actions_remain(client, model):
    model(reply(out([a_add("살아남음")], ask="이 질문은 버려진다")))
    res = post(client)
    assert res.json()["ask"] is None
    assert len(res.json()["actions"]) == 1


def test_ask_100_chars_is_ok(client, model):
    model(reply(out([], ask="가" * 100)))
    assert post(client).json()["ask"] == "가" * 100


# --- 502: 모양이 틀림 ---


def test_not_json_is_502(client, model):
    bad(client, model, "알겠습니다. 추가할게요.")


def test_json_array_is_502(client, model):
    bad(client, model, "[1, 2]")


def test_truncated_reply_is_502(client, model):
    bad(client, model, '{"actions": [{"kind": "add", "tit', stop_reason="max_tokens")


def test_refusal_is_502(client, model):
    bad(client, model, out([a_add()]), stop_reason="refusal")


def test_missing_actions_key_is_502(client, model):
    bad(client, model, json.dumps({"ask": None}))


def test_actions_not_a_list_is_502(client, model):
    bad(client, model, json.dumps({"actions": "add"}))


def test_action_not_an_object_is_502(client, model):
    bad(client, model, json.dumps({"actions": ["add"]}))


def test_ask_not_a_string_is_502(client, model):
    bad(client, model, json.dumps({"actions": [], "ask": 5}))


def test_ask_over_100_chars_is_502(client, model):
    bad(client, model, out([], ask="가" * 101))


def test_network_error_is_502(client, model):
    add(client)
    model(anthropic.APIConnectionError(request=REQ))
    res = post(client)
    assert res.status_code == 502
    assert res.json() == {"detail": "제안 실패"}


# --- 401, 503 ---


def test_without_login_is_401_and_model_is_not_called(db_file, model):
    fake = model(reply(out([a_add()])))
    with TestClient(app) as anon:
        assert post(anon).status_code == 401
        assert post(anon, "").status_code == 401
    assert fake.calls == []


def test_no_api_key_is_503(client, model, monkeypatch):
    fake = model(reply(out([a_add()])))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    res = post(client)
    assert res.status_code == 503
    assert res.json() == {"detail": "AI 기능 꺼짐"}
    assert fake.calls == []


@pytest.mark.parametrize(
    "error",
    [status_error(anthropic.RateLimitError, 429), status_error(anthropic.OverloadedError, 529)],
)
def test_rate_limit_and_overloaded_are_503(client, model, error):
    model(error)
    res = post(client)
    assert res.status_code == 503
    assert res.json() == {"detail": "AI를 잠시 쓸 수 없음"}


@pytest.mark.parametrize(
    "error",
    [status_error(anthropic.AuthenticationError, 401), status_error(anthropic.PermissionDeniedError, 403)],
)
def test_auth_errors_are_503(client, model, error):
    model(error)
    res = post(client)
    assert res.status_code == 503
    assert res.json() == {"detail": "AI 기능 꺼짐"}


# --- 저장하지 않는다 ---


def test_db_is_unchanged_after_request(client, model, db_file):
    a = add(client, "견적서", "HIGH", "2026-10-25")
    b = add(client, "장보기")
    before = rows(db_file)
    model(reply(out([a_add("새 일"), a_due(a, "2026-10-30"), a_done(b)])))
    assert post(client).status_code == 200
    assert rows(db_file) == before
    assert len(client.get("/tasks").json()) == 2


def test_db_is_unchanged_after_failure(client, model, db_file):
    add(client)
    before = rows(db_file)
    model(reply("JSON 아님"))
    assert post(client).status_code == 502
    assert rows(db_file) == before


# --- 경로 ---


def test_command_path_does_not_hide_task_routes(client, model):
    a = add(client, "원래 제목")
    model(reply(out([a_add()])))
    assert post(client).status_code == 200
    assert client.put(f"/tasks/{a}", json={"title": "바뀐 제목"}).status_code == 200
    assert client.patch(f"/tasks/{a}/status", json={"status": "DONE"}).status_code == 200
    assert client.delete(f"/tasks/{a}").status_code == 204
