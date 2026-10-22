from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import app

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
PASSWORD = "password123"


def upgrade_db() -> None:
    """TASK_FLOW_DB가 가리키는 파일에 alembic을 적용한다 (테스트는 임시 파일만 쓴다)."""
    command.upgrade(Config(str(ALEMBIC_INI)), "head")


def sign_in(c: TestClient, username: str = "tester01") -> None:
    """가입하고 로그인해서 이 클라이언트가 로그인 상태가 되게 한다."""
    assert c.post("/users", json={"username": username, "password": PASSWORD}).status_code == 201
    assert c.post("/sessions", json={"username": username, "password": PASSWORD}).status_code == 201


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    path = tmp_path / "tasks.db"
    monkeypatch.setenv("TASK_FLOW_DB", str(path))
    # 테스트용 값이다. 실제 비밀값이 아니다.
    monkeypatch.setenv("SESSION_SECRET", "test-secret-not-real")
    upgrade_db()
    return path


@pytest.fixture
def client(db_file):
    """로그인하지 않은 클라이언트."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(db_file):
    """tester01로 로그인한 클라이언트."""
    with TestClient(app) as c:
        sign_in(c)
        yield c
