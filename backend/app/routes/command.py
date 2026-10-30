import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import command as ai
from app.db import get_db
from app.routes import tasks as tasks_route
from app.rules import validate_text
from app.schemas import CommandRequest, CommandResult
from app.security import AuthUser, get_current_user

# AI 한 문장으로 시키기 (#33). 돌려주기만 하고 저장하지 않는다. DB는 읽기만 한다.
router = APIRouter(prefix="/tasks", tags=["command"])


# 검사 순서: 로그인(401) → 문장 규칙(422, 이유 문자열) → DB 조회 → 키 확인(503) → 호출 → 응답 검사(502).
# 완료가 아닌 Task가 0개여도 add를 할 수 있어 모델을 부른다.
# POST /tasks/command는 /tasks/{task_id}(PUT, PATCH, DELETE)와 메서드가 달라 가려지지 않는다.
@router.post("/command")
def command(
    body: CommandRequest,
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> CommandResult:
    try:
        text = validate_text(body.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        return ai.command(db, user.id, text, tasks_route._today())
    except ai.SuggestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
