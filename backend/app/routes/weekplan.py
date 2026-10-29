import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import weekplan as ai
from app.db import get_db
from app.routes import tasks as tasks_route
from app.schemas import WeekPlan
from app.security import AuthUser, get_current_user

# AI 이번 주 계획 (R-019, D-037). 저장하지 않는다. DB는 읽기만 한다.
router = APIRouter(prefix="/tasks", tags=["weekplan"])


# 검사 순서: 로그인(401) → DB 조회 → (Task 0개면 바로 200) → 키 확인(503) → 호출 → 응답 검사(502). 본문이 없어 422는 없다.
# POST /tasks/weekplan은 /tasks/{task_id}(PUT, PATCH, DELETE)와 메서드가 달라 가려지지 않는다.
@router.post("/weekplan")
def weekplan(
    user: AuthUser = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)
) -> WeekPlan:
    try:
        return ai.plan(db, user.id, tasks_route._today())
    except ai.SuggestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
