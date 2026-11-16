"""schema.sql을 DATABASE_URL이 가리키는 PostgreSQL에 한 번 실행하고, 테이블마다 주인과 RLS 상태를 출력한다.

실행 (psycopg는 프로젝트 의존성에 넣지 않고 --with로만 쓴다):
    cd backend
    uv run --with "psycopg[binary]" python supabase/apply_schema.py
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
TABLES = ["users", "sessions", "tasks"]

CHECK_SQL = """
SELECT c.relname, r.rolname, c.relrowsecurity
FROM pg_class c
JOIN pg_roles r ON r.oid = c.relowner
WHERE c.relnamespace = 'public'::regnamespace AND c.relname = ANY(%s)
"""


def scrub(text: str, url: str) -> str:
    """오류 문장에 비밀번호가 섞여 있으면 가린다."""
    password = urlsplit(url).password
    return text.replace(password, "***") if password else text


def main() -> int:
    try:
        import psycopg
    except ModuleNotFoundError:
        print('psycopg가 없습니다. uv run --with "psycopg[binary]" python supabase/apply_schema.py 로 실행하세요.')
        return 1

    load_dotenv(BACKEND_DIR / ".env")
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("DATABASE_URL이 없습니다 (backend/.env).")
        return 1

    try:
        # prepare_threshold=None: Supabase 연결 풀러(transaction 모드)에서도 실행되게 한다.
        with psycopg.connect(url, prepare_threshold=None) as conn:
            conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            rows = {name: (owner, rls) for name, owner, rls in conn.execute(CHECK_SQL, (TABLES,))}
    except Exception as exc:  # 연결·실행 실패. 주소 전체나 비밀번호는 출력하지 않는다.
        print(f"실패: {type(exc).__name__}: {scrub(str(exc), url)}")
        return 1

    for name in TABLES:
        if name not in rows:
            print(f"{name}: 없음")
            continue
        owner, rls = rows[name]
        print(f"{name}: 주인={owner}, RLS={'켜짐' if rls else '꺼짐'}")
    return 0 if all(name in rows and rows[name][1] for name in TABLES) else 1


if __name__ == "__main__":
    sys.exit(main())
