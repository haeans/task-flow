import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash

from app.config import session_secret
from app.db import get_db

COOKIE_NAME = "session"
SESSION_SECONDS = 86400  # 로그인한 시각부터 24시간 (D-029)

# pwdlib의 권장 설정(argon2 기본값)을 그대로 쓴다.
_hasher = PasswordHash.recommended()
# 없는 아이디로 로그인할 때도 해시 검증 시간을 비슷하게 쓰기 위한 값이다.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def now() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    return _hasher.verify(password, password_hash)


def new_session_id() -> str:
    # 추측할 수 없는 무작위 32바이트 값
    return secrets.token_urlsafe(32)


def _signature(session_id: str) -> str:
    return hmac.new(session_secret(), session_id.encode(), hashlib.sha256).hexdigest()


def sign(session_id: str) -> str:
    return f"{session_id}.{_signature(session_id)}"


def unsign(cookie_value: str | None) -> str | None:
    if not cookie_value or "." not in cookie_value:
        return None
    session_id, _, signature = cookie_value.rpartition(".")
    if not hmac.compare_digest(signature, _signature(session_id)):
        return None
    return session_id


@dataclass
class AuthUser:
    id: int
    username: str
    session_id: str


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="로그인이 필요하다")


def get_current_user(request: Request, db: sqlite3.Connection = Depends(get_db)) -> AuthUser:
    """로그인 확인. 쿠키가 없거나 서명이 맞지 않거나 세션이 없거나 끝났으면 401."""
    session_id = unsign(request.cookies.get(COOKIE_NAME))
    if session_id is None:
        raise _unauthorized()
    row = db.execute(
        "SELECT s.created_at, u.id AS user_id, u.username "
        "FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ?",
        (session_id,),
    ).fetchone()
    if row is None:
        raise _unauthorized()
    # 만든 시각부터 86400초가 지나면 끝난 세션이다. 끝난 행은 조회될 때 지운다.
    if now() >= datetime.fromisoformat(row["created_at"]) + timedelta(seconds=SESSION_SECONDS):
        db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        db.commit()
        raise _unauthorized()
    return AuthUser(id=row["user_id"], username=row["username"], session_id=session_id)
