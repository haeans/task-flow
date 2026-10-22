import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response

from app import security
from app.db import get_db
from app.schemas import LoginRequest, SignupRequest, UserOut
from app.security import AuthUser, get_current_user

router = APIRouter(tags=["auth"])

LOGIN_FAILED = "아이디 또는 비밀번호가 올바르지 않다"


@router.post("/users", status_code=201)
def signup(body: SignupRequest, db: sqlite3.Connection = Depends(get_db)) -> UserOut:
    # 가입 뒤 자동으로 로그인하지 않는다.
    if db.execute("SELECT 1 FROM users WHERE username = ?", (body.username,)).fetchone():
        raise HTTPException(status_code=409, detail="이미 있는 아이디다")
    try:
        cur = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (body.username, security.hash_password(body.password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="이미 있는 아이디다")
    return UserOut(id=cur.lastrowid, username=body.username)


@router.post("/sessions", status_code=201)
def login(
    body: LoginRequest, response: Response, db: sqlite3.Connection = Depends(get_db)
) -> UserOut:
    row = db.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?", (body.username,)
    ).fetchone()
    ok = security.verify_password(body.password, row["password_hash"] if row else None)
    if row is None or not ok:
        # 아이디가 틀렸는지 비밀번호가 틀렸는지 구분하지 않는다.
        raise HTTPException(status_code=401, detail=LOGIN_FAILED)
    # 이미 로그인한 상태여도 새 세션을 만들고 쿠키를 바꾼다. 옛 세션은 그대로 둔다.
    session_id = security.new_session_id()
    db.execute(
        "INSERT INTO sessions (id, user_id, created_at) VALUES (?, ?, ?)",
        (session_id, row["id"], security.now().isoformat()),
    )
    db.commit()
    response.set_cookie(
        security.COOKIE_NAME,
        security.sign(session_id),
        max_age=security.SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
        secure=False,  # 로컬 http라서 끈다 (F-004)
    )
    return UserOut(id=row["id"], username=row["username"])


@router.delete("/sessions", status_code=204)
def logout(
    user: AuthUser = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)
) -> Response:
    db.execute("DELETE FROM sessions WHERE id = ?", (user.session_id,))
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie(security.COOKIE_NAME, path="/")
    return response
