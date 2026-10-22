import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import get_db
from app.schemas import StatusUpdate, Task, TaskCreate, TaskUpdate
from app.security import AuthUser, get_current_user

# 모든 카드 요청은 로그인한 사용자만 쓴다 (401). 그 사용자의 카드만 대상이다.
router = APIRouter(prefix="/tasks", tags=["tasks"])


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


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
    rows = db.execute(
        "SELECT * FROM tasks WHERE owner_id = ? ORDER BY created_at DESC, id DESC", (user.id,)
    ).fetchall()
    return [Task(**row) for row in rows]


@router.post("", status_code=201)
def create_task(
    body: TaskCreate,
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Task:
    # 소유자는 요청으로 받지 않고 로그인 정보로만 정한다.
    now = _now()
    cur = db.execute(
        "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id) "
        "VALUES (?, ?, 'TODO', ?, ?, ?)",
        (body.title, body.description, now, now, user.id),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return Task(**row)


@router.patch("/{task_id}/status")
def change_status(
    body: StatusUpdate,
    task_id: int = Depends(owned_task_id),
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Task:
    # 상태만 바꾼다. updated_at은 제목·설명 수정에서만 갱신한다.
    db.execute(
        "UPDATE tasks SET status = ? WHERE id = ? AND owner_id = ?", (body.status, task_id, user.id)
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return Task(**row)


@router.put("/{task_id}")
def update_task(
    body: TaskUpdate,
    task_id: int = Depends(owned_task_id),
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Task:
    db.execute(
        "UPDATE tasks SET title = ?, description = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
        (body.title, body.description, _now(), task_id, user.id),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return Task(**row)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int = Depends(owned_task_id),
    user: AuthUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    db.execute("DELETE FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id))
    db.commit()
    return Response(status_code=204)
