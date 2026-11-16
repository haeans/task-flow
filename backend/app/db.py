import logging
import os
from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row

from app import config  # noqa: F401  backend/.env를 읽어 둔다 (DATABASE_URL)

log = logging.getLogger(__name__)

# 테이블은 backend/supabase/schema.sql이 만든다. 앱은 만들지 않고 열이 있는지만 확인한다.
EXPECTED_COLUMNS = {
    "users": {"id", "username", "password_hash"},
    "sessions": {"id", "user_id", "created_at"},
    "tasks": {
        "id", "title", "description", "status", "created_at", "updated_at",
        "owner_id", "priority", "due_date",
    },
}


def database_url() -> str:
    # 기본값을 두지 않는다. 없으면 연결할 때 오류가 난다.
    return os.environ.get("DATABASE_URL", "")


def connect() -> psycopg.Connection:
    # autocommit: 문장마다 바로 반영한다. 여러 문장을 묶을 곳은 with conn.transaction()을 쓴다.
    # prepare_threshold=None: Supabase 연결 풀러(transaction 모드)에서도 쓸 수 있게 한다.
    return psycopg.connect(
        database_url(), row_factory=dict_row, autocommit=True, prepare_threshold=None
    )


def missing_columns(conn: psycopg.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = ANY(%s)",
        (list(EXPECTED_COLUMNS),),
    ).fetchall()
    have = {(r["table_name"], r["column_name"]) for r in rows}
    return [
        f"{table}.{column}"
        for table, columns in EXPECTED_COLUMNS.items()
        for column in sorted(columns)
        if (table, column) not in have
    ]


def init_db() -> None:
    try:
        with connect() as conn:
            missing = missing_columns(conn)
    except psycopg.Error as exc:
        # 연결하지 못해도 앱은 뜬다. 요청이 오면 오류로 응답한다 (AQ-002). 주소는 남기지 않는다.
        log.warning("DB에 연결하지 못했습니다: %s", type(exc).__name__)
        return
    if missing:
        log.warning("schema.sql을 적용하세요. 없는 열: %s", ", ".join(missing))


def get_db() -> Iterator[psycopg.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
