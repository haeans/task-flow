import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.db import get_db
from app.schemas import Task, TaskCreate

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
