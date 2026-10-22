from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import app

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def upgrade_db() -> None:
    """TASK_FLOW_DB가 가리키는 파일에 alembic을 적용한다 (테스트는 임시 파일만 쓴다)."""
    command.upgrade(Config(str(ALEMBIC_INI)), "head")


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
    with TestClient(app) as c:
        yield c
