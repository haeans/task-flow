import os
from pathlib import Path

from dotenv import load_dotenv

# backend/.env는 Git에 올리지 않는다. 항목 이름은 backend/.env.example에 있다.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def session_secret() -> bytes:
    # 기본값을 두지 않는다. 없으면 가입·로그인 쪽에서 실패한다.
    value = os.environ.get("SESSION_SECRET", "")
    if not value:
        raise RuntimeError("SESSION_SECRET이 설정되지 않았다 (backend/.env)")
    return value.encode()
