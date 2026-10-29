import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import briefing as ai
from app.db import get_db
from app.routes import tasks as tasks_route
from app.schemas import Briefing
from app.security import AuthUser, get_current_user

# AI 오늘 브리핑 (R-018, D-035). 저장하지 않는다. DB는 읽기만 한다.
router = APIRouter(prefix="/tasks", tags=["briefing"])


# 검사 순서: 로그인(401) → DB 조회 → 키 확인(503) → 호출 → 응답 검사(502). 본문이 없어 422는 없다.
# 완료가 아닌 Task가 0개이면 모델을 부르지 않으므로 키가 없어도 200이다.
# POST /tasks/briefing은 /tasks/{task_id}(PUT, PATCH, DELETE)와 메서드가 달라 가려지지 않는다.
@router.post("/briefing")
def briefing(
    user: AuthUser = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)
) -> Briefing:
    try:
        return ai.brief(db, user.id, tasks_route._today())
    except ai.SuggestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
