import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from tests.conftest import ALEMBIC_INI, upgrade_db

OLD_TASKS = """
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


@pytest.fixture
def path(tmp_path, monkeypatch) -> Path:
    p = tmp_path / "tasks.db"
    monkeypatch.setenv("TASK_FLOW_DB", str(p))
    return p


def _tables(p: Path) -> set[str]:
    with sqlite3.connect(p) as c:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(p: Path, table: str) -> set[str]:
    with sqlite3.connect(p) as c:
        return {r[1] for r in c.execute(f"PRAGMA table_info({table})")}


def test_upgrade_on_missing_db_creates_all_tables(path):
    upgrade_db()
    assert {"users", "sessions", "tasks"} <= _tables(path)
    assert "owner_id" in _columns(path, "tasks")


def test_upgrade_on_existing_tasks_keeps_rows_and_adds_owner(path):
    with sqlite3.connect(path) as c:
        c.execute(OLD_TASKS)
        c.execute(
            "INSERT INTO tasks (title, status, created_at, updated_at) VALUES ('옛 카드', 'TODO', 't', 't')"
        )
    upgrade_db()
    assert {"users", "sessions", "tasks"} <= _tables(path)
    assert "owner_id" in _columns(path, "tasks")
    with sqlite3.connect(path) as c:
        assert c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert c.execute("SELECT owner_id FROM tasks").fetchone()[0] is None
        assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def _rejects_bad_status(p: Path) -> bool:
    with sqlite3.connect(p) as c:
        try:
            c.execute(
                "INSERT INTO tasks (title, status, created_at, updated_at) VALUES ('x', 'BAD', 't', 't')"
            )
        except sqlite3.IntegrityError:
            return True
        return False


def test_status_check_survives_upgrade_and_downgrade(path):
    with sqlite3.connect(path) as c:
        c.execute(OLD_TASKS)
    upgrade_db()
    assert _rejects_bad_status(path)
    command.downgrade(Config(str(ALEMBIC_INI)), "base")
    assert _rejects_bad_status(path)


def test_username_is_unique(path):
    upgrade_db()
    with sqlite3.connect(path) as c:
        c.execute("INSERT INTO users (username, password_hash) VALUES ('abcd', 'h')")
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO users (username, password_hash) VALUES ('abcd', 'h2')")


def test_upgrade_adds_priority_and_due_date_with_defaults_to_existing_rows(path):
    with sqlite3.connect(path) as c:
        c.execute(OLD_TASKS)
        c.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at) "
            "VALUES ('옛 카드', '설명', 'IN_PROGRESS', 'c', 'u')"
        )
    upgrade_db()
    assert {"priority", "due_date"} <= _columns(path, "tasks")
    with sqlite3.connect(path) as c:
        row = c.execute(
            "SELECT title, description, status, created_at, updated_at, owner_id, priority, due_date "
            "FROM tasks"
        ).fetchall()
    assert row == [("옛 카드", "설명", "IN_PROGRESS", "c", "u", None, "NORMAL", None)]


def test_new_task_defaults_to_normal_without_due_date(path):
    upgrade_db()
    with sqlite3.connect(path) as c:
        c.execute(
            "INSERT INTO tasks (title, status, created_at, updated_at) VALUES ('x', 'TODO', 't', 't')"
        )
        assert c.execute("SELECT priority, due_date FROM tasks").fetchone() == ("NORMAL", None)


def test_priority_check_rejects_values_outside_the_three(path):
    upgrade_db()
    with sqlite3.connect(path) as c:
        for ok in ("LOW", "NORMAL", "HIGH"):
            c.execute(
                "INSERT INTO tasks (title, status, created_at, updated_at, priority) "
                "VALUES ('x', 'TODO', 't', 't', ?)",
                (ok,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(
                "INSERT INTO tasks (title, status, created_at, updated_at, priority) "
                "VALUES ('x', 'TODO', 't', 't', 'URGENT')"
            )


def test_downgrade_to_previous_revision_keeps_rows_and_status_check(path):
    upgrade_db()
    with sqlite3.connect(path) as c:
        c.execute(
            "INSERT INTO tasks (title, status, created_at, updated_at, priority, due_date) "
            "VALUES ('x', 'TODO', 't', 't', 'HIGH', '2026-10-27')"
        )
    command.downgrade(Config(str(ALEMBIC_INI)), "b2ec53722aec")
    cols = _columns(path, "tasks")
    assert "priority" not in cols and "due_date" not in cols and "owner_id" in cols
    with sqlite3.connect(path) as c:
        assert c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
    assert _rejects_bad_status(path)


def test_downgrade_removes_new_structures(path):
    upgrade_db()
    command.downgrade(Config(str(ALEMBIC_INI)), "base")
    assert "users" not in _tables(path)
    assert "sessions" not in _tables(path)
    assert "owner_id" not in _columns(path, "tasks")
