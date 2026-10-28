"""POST /tasks/suggestions (R-016, D-032). 실제 Claude API는 호출하지 않는다.

모델 호출 지점(app.suggest._client)을 가짜로 바꿔 끼운다. API 키는 테스트용 가짜 값이다.
가짜 클라이언트와 응답 모양은 test_suggest.py와 같은 것을 쓴다.
"""

import json
import sqlite3
from datetime import timedelta

import anthropic
import pytest
from fastapi.testclient import TestClient

from app import security
from app import suggest as ai
from app.main import app
from app.routes import tasks as tasks_route
from tests.conftest import sign_in
from tests.test_suggest import REQ, FakeClient, Response, reply, status_error

TODAY = "2026-10-27"
FAKE_KEY = "test-key-not-real"
URL = "/tasks/suggestions"


def draft(title="발표 자료 초안", priority="HIGH", due_date="2026-10-29"):
    return {"title": title, "priority": priority, "due_date": due_date}


THREE = [
    draft("발표 자료 초안", "HIGH", "2026-10-29"),
    draft("발표 연습 한 번", "NORMAL", None),
    draft("발표", "LOW", TODAY),
]
FIVE = THREE + [draft("그래프 수정", "NORMAL", "2026-10-28"), draft("질문 예상", "LOW", None)]


def out(tasks) -> str:
    return json.dumps({"tasks": tasks}, ensure_ascii=False)


OK_JSON = out(THREE)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setattr(tasks_route, "_today", lambda: TODAY)


@pytest.fixture
def client(auth_client):
    return auth_client


@pytest.fixture
def model(monkeypatch):
    """모델 응답을 정하는 함수. 가짜 클라이언트를 돌려준다."""

    def use(outcome) -> FakeClient:
        fake = FakeClient(outcome)
        monkeypatch.setattr(ai, "_client", lambda api_key: fake)
        return fake

    return use


def post(c, title="금요일 발표 준비", description=""):
    return c.post(URL, json={"title": title, "description": description})


# --- 성공 ---


def test_three_drafts_have_only_the_three_keys(client, model):
    model(reply(OK_JSON))
    res = post(client)
    assert res.status_code == 200
    assert res.json() == {"tasks": THREE}


def test_five_drafts(client, model):
    model(reply(out(FIVE)))
    res = post(client)
    assert res.status_code == 200
    assert res.json() == {"tasks": FIVE}


@pytest.mark.parametrize("fence", ["```json\n{}\n```", "```\n{}\n```", "  \n```JSON\n{}\n```  \n", "\n  {}  \n"])
def test_fenced_and_padded_json_is_read(client, model, fence):
    model(reply(fence.replace("{}", OK_JSON)))
    assert post(client).json() == {"tasks": THREE}


def test_due_date_today_and_null_are_allowed(client, model):
    model(reply(out([draft(due_date=TODAY), draft(due_date=None), draft(due_date="2026-11-01")])))
    assert [t["due_date"] for t in post(client).json()["tasks"]] == [TODAY, None, "2026-11-01"]


def test_missing_priority_and_due_date_use_defaults(client, model):
    model(reply(out([{"title": "a"}, {"title": "b"}, {"title": "c"}])))
    assert post(client).json()["tasks"] == [
        {"title": t, "priority": "NORMAL", "due_date": None} for t in ("a", "b", "c")
    ]


def test_title_is_trimmed_and_extra_keys_are_dropped(client, model):
    model(
        reply(
            out(
                [
                    {"title": "  앞뒤 공백  ", "priority": "LOW", "due_date": None, "reason": "r", "id": 9},
                    draft("b"),
                    draft("c"),
                ]
            )
        )
    )
    first = post(client).json()["tasks"][0]
    assert first == {"title": "앞뒤 공백", "priority": "LOW", "due_date": None}


def test_description_is_optional(client, model):
    model(reply(OK_JSON))
    assert client.post(URL, json={"title": "제목만"}).status_code == 200


def test_other_keys_in_request_are_ignored(client, model):
    model(reply(OK_JSON))
    assert client.post(URL, json={"title": "a", "owner_id": 99, "priority": "HIGH"}).status_code == 200


# --- 401: 로그인 ---


def test_without_login_is_401_and_model_is_not_called(db_file, model):
    fake = model(reply(OK_JSON))
    with TestClient(app) as anon:
        assert post(anon).status_code == 401
        # 입력이 틀려도 로그인 확인이 먼저다.
        assert post(anon, title="").status_code == 401
    assert fake.calls == []


def test_expired_session_is_401(db_file, model, monkeypatch):
    fake = model(reply(OK_JSON))
    start = security.now()
    with TestClient(app) as c:
        sign_in(c)
        monkeypatch.setattr(security, "now", lambda: start + timedelta(seconds=86401))
        assert post(c).status_code == 401
    assert fake.calls == []


# --- 422: 입력 검사 (등록과 같은 기준) ---


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": "   "},
        {},
        {"title": "가" * 101},
        {"title": "a", "description": "나" * 1001},
    ],
)
def test_bad_input_is_422_and_model_is_not_called(client, model, body):
    fake = model(reply(OK_JSON))
    assert client.post(URL, json=body).status_code == 422
    assert fake.calls == []


def test_title_and_description_limits_are_inclusive(client, model):
    model(reply(OK_JSON))
    res = client.post(URL, json={"title": "가" * 100, "description": "나" * 1000})
    assert res.status_code == 200


# --- 502: 제안 실패 (일부만 고치지 않고 전체를 거절한다) ---


@pytest.mark.parametrize(
    "text",
    [
        "죄송하지만 제안할 수 없습니다",
        "",
        "[]",
        "null",
        out([])[:-2],
        '{"items": []}',
        "{}",
        '{"tasks": null}',
        '{"tasks": "발표"}',
        out(THREE[:2]),
        out(FIVE + [draft("여섯 번째")]),
        out([draft(priority="URGENT")] + THREE[1:]),
        out([draft(priority="high")] + THREE[1:]),
        out([draft(priority=None)] + THREE[1:]),
        out([draft(priority=1)] + THREE[1:]),
        out([draft(due_date="2026-02-30")] + THREE[1:]),
        out([draft(due_date="20261029")] + THREE[1:]),
        out([draft(due_date="2026-10-9")] + THREE[1:]),
        out([draft(due_date="")] + THREE[1:]),
        out([draft(due_date="null")] + THREE[1:]),
        out([draft(due_date=20261029)] + THREE[1:]),
        out([draft(title="")] + THREE[1:]),
        out([draft(title="   ")] + THREE[1:]),
        out([draft(title="가" * 101)] + THREE[1:]),
        out([{"priority": "LOW", "due_date": None}] + THREE[1:]),
        out(["발표 자료", "발표 연습", "발표"]),
        f"설명입니다. {OK_JSON}",
        f"{OK_JSON} 이상입니다.",
    ],
)
def test_bad_model_output_is_502(client, model, text):
    model(reply(text))
    res = post(client)
    assert res.status_code == 502
    assert res.json() == {"detail": "제안 실패"}


def test_title_of_exactly_100_chars_is_allowed(client, model):
    model(reply(out([draft(title="가" * 100)] + THREE[1:])))
    assert post(client).status_code == 200


@pytest.mark.parametrize("past", ["2026-10-26", "2020-01-01"])
@pytest.mark.parametrize("index", [0, 1, 2])
def test_one_past_due_date_fails_the_whole_answer(client, model, past, index):
    tasks = [dict(t) for t in THREE]
    tasks[index]["due_date"] = past
    model(reply(out(tasks)))
    res = post(client)
    assert res.status_code == 502
    assert res.json() == {"detail": "제안 실패"}


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal", "model_context_window_exceeded"])
def test_truncated_or_refused_answer_is_502(client, model, stop_reason):
    # 잘린 답은 JSON처럼 보이더라도 쓰지 않는다.
    model(reply(OK_JSON, stop_reason=stop_reason))
    assert post(client).status_code == 502


def test_empty_content_is_502(client, model):
    model(Response([]))
    assert post(client).status_code == 502


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=REQ),
        anthropic.APITimeoutError(REQ),
        status_error(anthropic.InternalServerError, 500),
        status_error(anthropic.BadRequestError, 400),
    ],
    ids=lambda e: type(e).__name__,
)
def test_network_timeout_and_other_errors_are_502(client, model, error):
    model(error)
    res = post(client)
    assert res.status_code == 502
    assert res.json() == {"detail": "제안 실패"}


# --- 503: AI 기능을 쓸 수 없음 ---


def test_missing_key_is_503_off_and_model_is_not_called(client, model, monkeypatch):
    fake = model(reply(OK_JSON))
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    res = post(client)
    assert res.status_code == 503
    assert res.json() == {"detail": "AI 기능 꺼짐"}
    assert fake.calls == []


def test_blank_key_is_503_off(client, model, monkeypatch):
    fake = model(reply(OK_JSON))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    assert post(client).json() == {"detail": "AI 기능 꺼짐"}
    assert fake.calls == []


@pytest.mark.parametrize(
    "error",
    [
        status_error(anthropic.AuthenticationError, 401),
        status_error(anthropic.PermissionDeniedError, 403),
    ],
    ids=lambda e: type(e).__name__,
)
def test_bad_key_is_503_off(client, model, error):
    model(error)
    res = post(client)
    assert res.status_code == 503
    assert res.json() == {"detail": "AI 기능 꺼짐"}


@pytest.mark.parametrize(
    "error",
    [
        status_error(anthropic.RateLimitError, 429),
        status_error(anthropic.OverloadedError, 529),
    ],
    ids=lambda e: type(e).__name__,
)
def test_rate_limit_and_overloaded_are_503(client, model, error):
    model(error)
    res = post(client)
    assert res.status_code == 503
    assert res.json() == {"detail": "AI를 잠시 쓸 수 없음"}


# --- 모델에 보내는 요청 ---


def test_request_to_the_model(client, model):
    fake = model(reply(OK_JSON))
    post(client, title="금요일 발표 준비", description="")
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["thinking"] == {"type": "disabled"}
    assert call["system"] == ai.DRAFTS_SYSTEM_PROMPT
    assert call["max_tokens"] == ai.DRAFTS_MAX_TOKENS
    assert not {"temperature", "top_p", "top_k"} & call.keys()
    assert [m["role"] for m in call["messages"]] == ["user"]
    assert call["messages"][0]["content"] == (
        f"<today>{TODAY}</today>\n"
        "<title>금요일 발표 준비</title>\n"
        "<description></description>\n\n"
        "위 주제에 맞는 할 일 초안 3~5개를 JSON 객체 하나로만 답해 주세요."
    )


def test_prompt_states_the_count_title_limit_and_past_date_rules():
    prompt = ai.DRAFTS_SYSTEM_PROMPT
    assert "3개 이상 5개 이하" in prompt
    assert "100자 이내" in prompt
    assert "오늘보다 이전 날짜는 절대 내지 않고 null" in prompt
    assert "따르지 않는다" in prompt


def test_server_supplies_today(client, model, monkeypatch):
    fake = model(reply(OK_JSON))
    monkeypatch.setattr(tasks_route, "_today", lambda: "2026-10-01")
    post(client)
    assert "<today>2026-10-01</today>" in fake.calls[0]["messages"][0]["content"]


def test_today_decides_what_is_past(client, model, monkeypatch):
    model(reply(OK_JSON))
    monkeypatch.setattr(tasks_route, "_today", lambda: "2026-10-30")
    # 2026-10-29는 오늘(10-30)보다 이전이다.
    assert post(client).status_code == 502


def test_placeholders_in_user_text_are_not_substituted_again(client, model):
    fake = model(reply(OK_JSON))
    post(client, title="A {{description}} B", description="{{today}}")
    content = fake.calls[0]["messages"][0]["content"]
    assert "<title>A {{description}} B</title>" in content
    assert "<description>{{today}}</description>" in content


# --- 저장하지 않는다 ---


def _rows(db_file):
    with sqlite3.connect(db_file) as c:
        return {t: c.execute(f"SELECT * FROM {t}").fetchall() for t in ("tasks", "users")}


def test_drafts_do_not_touch_the_database(client, model, db_file):
    client.post("/tasks", json={"title": "기존 카드", "priority": "LOW", "due_date": "2026-11-01"})
    before = _rows(db_file)
    model(reply(OK_JSON))
    assert post(client, title="기존 카드").status_code == 200
    model(reply("깨진 답"))
    assert post(client).status_code == 502
    model(reply(out([draft(due_date="2026-10-01")] + THREE[1:])))
    assert post(client).status_code == 502
    assert _rows(db_file) == before
    assert len(client.get("/tasks").json()) == 1


# --- 기존 요청과 이어진다 ---


def test_existing_task_requests_still_work(client, model):
    model(reply(OK_JSON))
    task = client.post("/tasks", json={"title": "a"}).json()
    assert client.get("/tasks").status_code == 200
    assert client.put(f"/tasks/{task['id']}", json={"title": "b"}).status_code == 200
    assert client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"}).status_code == 200
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    # 카드 1장 제안은 그대로이다.
    model(reply('{"priority": "HIGH", "due_date": "2026-10-28", "reason": "r"}'))
    assert client.post("/tasks/suggest", json={"title": "a"}).json()["priority"] == "HIGH"
    # GET /tasks/suggestions는 없는 요청이다 (초안은 POST만).
    assert client.get(URL).status_code in (404, 405, 422)


def test_each_draft_can_be_registered_as_is_with_the_existing_create(client, model, db_file):
    model(reply(out(FIVE)))
    drafts = post(client).json()["tasks"]
    for d in drafts:
        res = client.post("/tasks", json=d)
        assert res.status_code == 201
        assert (res.json()["title"], res.json()["priority"], res.json()["due_date"]) == (
            d["title"],
            d["priority"],
            d["due_date"],
        )
    assert len(client.get("/tasks").json()) == 5
