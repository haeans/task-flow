import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

# 저장소 파일 위치 (AQ-003 확정). 테스트에서는 환경 변수 TASK_FLOW_DB로 바꾼다.
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tasks.db"


def db_path() -> Path:
    return Path(os.environ.get("TASK_FLOW_DB", DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    # 스키마는 만들지 않는다. 테이블은 alembic(`alembic upgrade head`)이 만든다.
    db_path().parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path())
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def init_db() -> None:
    try:
        connect().close()
    except (sqlite3.Error, OSError):
        # 파일을 읽을 수 없어도 앱은 뜬다. 요청이 오면 오류로 응답한다 (AQ-002).
        pass


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
