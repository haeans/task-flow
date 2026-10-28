"""POST /tasks/suggest (R-015, D-031). 실제 Claude API는 호출하지 않는다.

모델 호출 지점(app.suggest._client)을 가짜로 바꿔 끼운다. API 키는 테스트용 가짜 값이다.
"""

import logging
import sqlite3
from datetime import timedelta

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from app import security
from app import suggest as ai
from app.main import app
from app.routes import tasks as tasks_route
from tests.conftest import sign_in

TODAY = "2026-10-27"
FAKE_KEY = "test-key-not-real"
OK_JSON = '{"priority": "HIGH", "due_date": "2026-10-28", "reason": "마감이 내일이라 높음"}'
URL = "/tasks/suggest"
REQ = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


class Block:
    def __init__(self, type_: str = "text", text: str = ""):
        self.type = type_
        self.text = text


class Response:
    def __init__(self, content, stop_reason: str = "end_turn"):
        self.content = content
        self.stop_reason = stop_reason


def reply(text: str, stop_reason: str = "end_turn") -> Response:
    return Response([Block("text", text)], stop_reason)


class FakeClient:
    """messages.create만 흉내 낸다. 받은 인자를 calls에 쌓고, 정해 둔 응답을 돌려주거나 예외를 던진다."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def status_error(cls, status: int):
    return cls("오류", response=httpx2.Response(status, request=REQ), body=None)


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


def post(c, title="내일까지 보고서 마무리, 급함", description=""):
    return c.post(URL, json={"title": title, "description": description})


# --- 성공 ---


def test_success_returns_only_the_three_keys(client, model):
    model(reply(OK_JSON))
    res = post(client)
    assert res.status_code == 200
    assert res.json() == {
        "priority": "HIGH",
        "due_date": "2026-10-28",
        "reason": "마감이 내일이라 높음",
    }


@pytest.mark.parametrize(
    "text",
    [
        OK_JSON,
        f"```json\n{OK_JSON}\n```",
        f"```\n{OK_JSON}\n```",
        f"  \n```JSON\n{OK_JSON}\n```  \n",
        f"\n  {OK_JSON}  \n",
    ],
)
def test_fenced_and_padded_json_is_read(client, model, text):
    model(reply(text))
    assert post(client).json()["priority"] == "HIGH"


def test_due_date_null_is_allowed(client, model):
    model(reply('{"priority": "LOW", "due_date": null, "reason": "단서 없음"}'))
    assert post(client).json() == {"priority": "LOW", "due_date": None, "reason": "단서 없음"}


def test_missing_keys_use_defaults(client, model):
    model(reply('{"reason": "단서 없음"}'))
    assert post(client).json() == {"priority": "NORMAL", "due_date": None, "reason": "단서 없음"}


def test_description_is_optional(client, model):
    model(reply(OK_JSON))
    assert client.post(URL, json={"title": "제목만"}).status_code == 200


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


# --- 502: 제안 실패 ---


@pytest.mark.parametrize(
    "text",
    [
        "죄송하지만 제안할 수 없습니다",
        "",
        "[]",
        '["HIGH"]',
        '"HIGH"',
        "null",
        '{"priority": "HIGH"',
        '{"priority": "URGENT", "reason": "r"}',
        '{"priority": "high", "reason": "r"}',
        '{"priority": null, "reason": "r"}',
        '{"priority": 1, "reason": "r"}',
        '{"priority": "LOW", "due_date": "2026-02-30", "reason": "r"}',
        '{"priority": "LOW", "due_date": "20261027", "reason": "r"}',
        '{"priority": "LOW", "due_date": "2026-1-5", "reason": "r"}',
        '{"priority": "LOW", "due_date": "", "reason": "r"}',
        '{"priority": "LOW", "due_date": "null", "reason": "r"}',
        '{"priority": "LOW", "due_date": 20261027, "reason": "r"}',
        '{"priority": "LOW", "due_date": "2026-10-27T10:00", "reason": "r"}',
        '{"priority": "LOW", "due_date": null}',
        '{"priority": "LOW", "due_date": null, "reason": null}',
        f"설명입니다. {OK_JSON}",
        f"{OK_JSON} 이상입니다.",
        f"```json\n{OK_JSON}\n``` 끝",
    ],
)
def test_bad_model_output_is_502(client, model, text):
    model(reply(text))
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


def test_first_block_not_text_is_502(client, model):
    model(Response([Block("thinking", "생각"), Block("text", OK_JSON)]))
    assert post(client).status_code == 502


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=REQ),
        anthropic.APITimeoutError(REQ),
        status_error(anthropic.InternalServerError, 500),
        status_error(anthropic.ServiceUnavailableError, 503),
        status_error(anthropic.BadRequestError, 400),
        status_error(anthropic.NotFoundError, 404),
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


def test_key_is_passed_to_the_client_and_never_leaks(client, monkeypatch, caplog):
    seen = []

    def make(api_key):
        seen.append(api_key)
        return FakeClient(status_error(anthropic.RateLimitError, 429))

    monkeypatch.setattr(ai, "_client", make)
    # 테스트가 DB를 준비할 때 alembic의 fileConfig가 기존 로거를 꺼 둔다. 서버 실행에는 없는 일이다.
    monkeypatch.setattr(ai.logger, "disabled", False)
    with caplog.at_level(logging.DEBUG):
        res = post(client, title="비밀 제목", description="비밀 설명")
    assert seen == [FAKE_KEY]
    assert FAKE_KEY not in res.text
    # 로그에는 예외 종류만 남는다. 키, 제목, 설명은 없다.
    assert FAKE_KEY not in caplog.text
    assert "비밀 제목" not in caplog.text and "비밀 설명" not in caplog.text
    assert "RateLimitError" in caplog.text


# --- 모델에 보내는 요청 ---


def test_request_to_the_model(client, model):
    fake = model(reply(OK_JSON))
    post(client, title="내일까지 보고서 마무리, 급함", description="")
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["thinking"] == {"type": "disabled"}
    assert call["system"] == ai.SYSTEM_PROMPT
    assert call["max_tokens"] == ai.MAX_TOKENS
    # 비기본 샘플링 값은 이 모델에서 400이다. prefill(마지막 assistant 턴)도 쓰지 않는다.
    assert not {"temperature", "top_p", "top_k"} & call.keys()
    assert [m["role"] for m in call["messages"]] == ["user"]
    assert call["messages"][0]["content"] == (
        f"<today>{TODAY}</today>\n"
        "<title>내일까지 보고서 마무리, 급함</title>\n"
        "<description></description>\n\n"
        "위 할 일의 priority, due_date, reason을 JSON 객체 하나로만 답해 주세요."
    )


def test_server_supplies_today(client, model, monkeypatch):
    fake = model(reply(OK_JSON))
    monkeypatch.setattr(tasks_route, "_today", lambda: "2030-01-02")
    post(client)
    assert "<today>2030-01-02</today>" in fake.calls[0]["messages"][0]["content"]


def test_placeholders_in_user_text_are_not_substituted_again(client, model):
    fake = model(reply(OK_JSON))
    post(client, title="A {{description}} B", description="{{today}}")
    content = fake.calls[0]["messages"][0]["content"]
    assert "<title>A {{description}} B</title>" in content
    assert "<description>{{today}}</description>" in content


def test_client_is_built_with_timeout_and_retry_settings(client, monkeypatch):
    built = {}

    class Spy:
        def __init__(self, **kwargs):
            built.update(kwargs)
            self.messages = FakeClient(reply(OK_JSON))

    monkeypatch.setattr(ai.anthropic, "Anthropic", Spy)
    assert post(client).status_code == 200
    assert built == {"api_key": FAKE_KEY, "timeout": ai.TIMEOUT_SECONDS, "max_retries": ai.MAX_RETRIES}


# --- 저장하지 않는다 ---


def _rows(db_file):
    with sqlite3.connect(db_file) as c:
        return {t: c.execute(f"SELECT * FROM {t}").fetchall() for t in ("tasks", "users")}


def test_suggest_does_not_touch_the_database(client, model, db_file):
    client.post("/tasks", json={"title": "기존 카드", "priority": "LOW", "due_date": "2026-11-01"})
    before = _rows(db_file)
    model(reply(OK_JSON))
    assert post(client, title="기존 카드").status_code == 200
    model(reply("깨진 답"))
    assert post(client).status_code == 502
    assert _rows(db_file) == before
    assert len(client.get("/tasks").json()) == 1


# --- 경로가 기존 요청과 부딪히지 않는다 ---


def test_existing_task_requests_still_work(client, model):
    model(reply(OK_JSON))
    task = client.post("/tasks", json={"title": "a"}).json()
    assert client.get("/tasks").status_code == 200
    assert client.put(f"/tasks/{task['id']}", json={"title": "b"}).status_code == 200
    assert client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"}).status_code == 200
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    # GET /tasks/suggest는 없는 요청이다 (제안은 POST만).
    assert client.get(URL).status_code in (404, 405, 422)
