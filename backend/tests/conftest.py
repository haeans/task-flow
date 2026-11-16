import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import app

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
SCHEMA_SQL = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
PASSWORD = "password123"


def upgrade_db() -> None:
    """TASK_FLOW_DB가 가리키는 SQLite 파일에 alembic을 적용한다. 예전 SQLite 마이그레이션 시험(test_migration)만 쓴다."""
    command.upgrade(Config(str(ALEMBIC_INI)), "head")


def raw_db(url: str) -> psycopg.Connection:
    """시험이 DB를 직접 들여다보거나 값을 넣을 때 쓴다. 행은 튜플이고 문장마다 바로 반영된다."""
    return psycopg.connect(url, autocommit=True)


def sign_in(c: TestClient, username: str = "tester01") -> None:
    """가입하고 로그인해서 이 클라이언트가 로그인 상태가 되게 한다."""
    assert c.post("/users", json={"username": username, "password": PASSWORD}).status_code == 201
    assert c.post("/sessions", json={"username": username, "password": PASSWORD}).status_code == 201


@pytest.fixture(autouse=True)
def _never_use_real_db(monkeypatch):
    """backend/.env의 DATABASE_URL(실제 DB일 수 있다)로 시험이 연결되지 않게 막는다."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none?connect_timeout=2")


@pytest.fixture(scope="session")
def pg_url(tmp_path_factory):
    """시험용 PostgreSQL 주소. TEST_DATABASE_URL이 있으면 그 DB를 쓰고(테이블이 비워진다), 없으면 pgserver로 임시 서버를 띄운다."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    try:
        import pgserver
    except ModuleNotFoundError:
        pytest.skip("TEST_DATABASE_URL을 정하거나 uv run --with pgserver pytest 로 실행하세요")
    server = pgserver.get_server(tmp_path_factory.mktemp("pg"))
    yield server.get_uri()
    server.cleanup()


@pytest.fixture
def db_file(pg_url, monkeypatch):
    """시험마다 비워진 시험용 DB. 이름은 예전 그대로이고 값은 DB 주소이다."""
    monkeypatch.setenv("DATABASE_URL", pg_url)
    # 테스트용 값이다. 실제 비밀값이 아니다.
    monkeypatch.setenv("SESSION_SECRET", "test-secret-not-real")
    with raw_db(pg_url) as c:
        c.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        c.execute("TRUNCATE users, sessions, tasks RESTART IDENTITY CASCADE")
    return pg_url


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
