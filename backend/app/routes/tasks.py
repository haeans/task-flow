import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import get_db
from app.schemas import StatusUpdate, Task, TaskCreate, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


@router.get("")
def list_tasks(db: sqlite3.Connection = Depends(get_db)) -> list[Task]:
    rows = db.execute("SELECT * FROM tasks ORDER BY created_at DESC, id DESC").fetchall()
    return [Task(**row) for row in rows]


@router.post("", status_code=201)
def create_task(body: TaskCreate, db: sqlite3.Connection = Depends(get_db)) -> Task:
    now = _now()
    cur = db.execute(
        "INSERT INTO tasks (title, description, status, created_at, updated_at) "
        "VALUES (?, ?, 'TODO', ?, ?)",
        (body.title, body.description, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return Task(**row)


@router.patch("/{task_id}/status")
def change_status(
    task_id: int, body: StatusUpdate, db: sqlite3.Connection = Depends(get_db)
) -> Task:
    # 상태만 바꾼다. updated_at은 제목·설명 수정에서만 갱신한다.
    cur = db.execute("UPDATE tasks SET status = ? WHERE id = ?", (body.status, task_id))
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없음")
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return Task(**row)


@router.put("/{task_id}")
def update_task(
    task_id: int, body: TaskUpdate, db: sqlite3.Connection = Depends(get_db)
) -> Task:
    cur = db.execute(
        "UPDATE tasks SET title = ?, description = ?, updated_at = ? WHERE id = ?",
        (body.title, body.description, _now(), task_id),
    )
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없음")
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return Task(**row)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: sqlite3.Connection = Depends(get_db)) -> Response:
    cur = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없음")
    return Response(status_code=204)
