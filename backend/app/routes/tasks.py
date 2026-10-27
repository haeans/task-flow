import sqlite3
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import get_db
from app.schemas import StatusUpdate, Task, TaskCreate, TaskUpdate
from app.security import AuthUser, get_current_user

# 모든 카드 요청은 로그인한 사용자만 쓴다 (401). 그 사용자의 카드만 대상이다.
router = APIRouter(prefix="/tasks", tags=["tasks"])


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _today() -> str:
    # "오늘"은 서버 PC의 로컬 날짜이다 (Q-018). 테스트에서 이 함수를 바꿔 날짜를 고정한다.
    return date.today().isoformat()


def _to_task(row: sqlite3.Row, today: str) -> Task:
    # 기한 초과: 마감일이 오늘보다 이전이고 완료가 아닐 때. 당일은 아니다 (R-013).
    # YYYY-MM-DD 문자열은 사전순 비교가 날짜순이다.
    overdue = row["due_date"] is not None and row["due_date"] < today and row["status"] != "DONE"
    return Task(**dict(row), overdue=overdue)


def _fetch_task(db: sqlite3.Connection, task_id: int) -> Task:
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _to_task(row, _today())


# 정렬 (R-014, Q-020): 기한 초과 → 우선순위(HIGH 먼저) → 마감일 빠른 순(없으면 뒤) → ID 오름차순.
# D-017(최신순)을 대체한다.
_LIST_SQL = """
SELECT * FROM tasks WHERE owner_id = :owner
ORDER BY
  (due_date IS NOT NULL AND due_date < :today AND status != 'DONE') DESC,
  CASE priority WHEN 'HIGH' THEN 0 WHEN 'NORMAL' THEN 1 ELSE 2 END,
  due_date IS NULL,
  due_date,
  id
"""


def owned_task_id(
    task_id: int,
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> int:
    """검사 순서의 2번: 대상 카드가 로그인한 사용자의 것인지 확인한다.

    남의 카드와 없는 카드는 같은 404이다. 요청 본문의 입력 검사(422)보다 먼저 실행되도록
    핸들러가 아니라 의존성으로 둔다. 핸들러는 본문 검증이 끝난 뒤에야 실행된다.
    """
    row = db.execute(
        "SELECT id FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없음")
    return task_id


@router.get("")
def list_tasks(
    user: AuthUser = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)
) -> list[Task]:
    today = _today()
    rows = db.execute(_LIST_SQL, {"owner": user.id, "today": today}).fetchall()
    return [_to_task(row, today) for row in rows]


@router.post("", status_code=201)
def create_task(
    body: TaskCreate,
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Task:
    # 소유자는 요청으로 받지 않고 로그인 정보로만 정한다.
    now = _now()
    cur = db.execute(
        "INSERT INTO tasks (title, description, status, priority, due_date, created_at, updated_at, owner_id) "
        "VALUES (?, ?, 'TODO', ?, ?, ?, ?, ?)",
        (body.title, body.description, body.priority, body.due_date, now, now, user.id),
    )
    db.commit()
    return _fetch_task(db, cur.lastrowid)


@router.patch("/{task_id}/status")
def change_status(
    body: StatusUpdate,
    task_id: int = Depends(owned_task_id),
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Task:
    # 상태만 바꾼다. updated_at은 수정 요청에서만 갱신한다 (D-021).
    db.execute(
        "UPDATE tasks SET status = ? WHERE id = ? AND owner_id = ?", (body.status, task_id, user.id)
    )
    db.commit()
    return _fetch_task(db, task_id)


@router.put("/{task_id}")
def update_task(
    body: TaskUpdate,
    task_id: int = Depends(owned_task_id),
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Task:
    # priority와 due_date는 보낸 것만 바꾼다. due_date가 null이면 지운다 (R-011, R-012, Q-021).
    sets = {"title": body.title, "description": body.description, "updated_at": _now()}
    for field in ("priority", "due_date"):
        if field in body.model_fields_set:
            sets[field] = getattr(body, field)
    assignments = ", ".join(f"{col} = ?" for col in sets)
    db.execute(
        f"UPDATE tasks SET {assignments} WHERE id = ? AND owner_id = ?",
        (*sets.values(), task_id, user.id),
    )
    db.commit()
    return _fetch_task(db, task_id)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int = Depends(owned_task_id),
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    db.execute("DELETE FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id))
    db.commit()
    return Response(status_code=204)
