from fastapi import APIRouter, Depends, HTTPException

from app import suggest as ai
from app.routes import tasks as tasks_route
from app.schemas import SuggestRequest, Suggestion
from app.security import get_current_user

# AI 제안 (R-015, D-031). 제안만 돌려주고 저장하지 않는다. DB를 읽거나 쓰지 않는다.
router = APIRouter(prefix="/tasks", tags=["suggest"])


# 검사 순서: 로그인(401) → 입력 검사(422) → 키 확인(503) → 호출. 대상 카드가 없어 소유자 확인은 없다.
# 동기 함수라 FastAPI가 스레드 풀에서 실행한다. 모델 호출이 서버 전체를 막지 않는다.
@router.post("/suggest", dependencies=[Depends(get_current_user)])
def suggest_task(body: SuggestRequest) -> Suggestion:
    try:
        return ai.suggest(body.title, body.description, tasks_route._today())
    except ai.SuggestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
