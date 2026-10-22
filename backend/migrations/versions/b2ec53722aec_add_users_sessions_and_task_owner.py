"""add users sessions and task owner

Revision ID: b2ec53722aec
Revises: 
Create Date: 2026-10-22 16:44:33.747887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2ec53722aec'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.Text, nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
    )

    inspector = sa.inspect(op.get_bind())
    if "tasks" in inspector.get_table_names():
        # 예전 카드는 지우지 않는다. owner_id가 NULL인 카드는 어느 사용자에게도 보이지 않는다 (D-028).
        # SQLite는 기존 행이 있는 테이블에 NOT NULL 열을 더할 수 없어 DB 수준에서는 nullable이다.
        # batch(테이블 재생성)는 이름 없는 status CHECK를 떨어뜨리므로 쓰지 않고 열만 더한다.
        op.execute("ALTER TABLE tasks ADD COLUMN owner_id INTEGER REFERENCES users(id)")
    else:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("title", sa.Text, nullable=False),
            sa.Column("description", sa.Text, nullable=False, server_default=""),
            sa.Column("status", sa.Text, nullable=False),
            sa.Column("created_at", sa.Text, nullable=False),
            sa.Column("updated_at", sa.Text, nullable=False),
            # 기존 DB에 더한 열과 같은 모양을 유지한다. 앱이 항상 값을 넣는다.
            sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
            sa.CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'DONE')"),
            sqlite_autoincrement=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # 열 삭제는 테이블을 다시 만들므로 status CHECK를 명시해서 유지한다.
    with op.batch_alter_table(
        "tasks",
        table_args=(sa.CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'DONE')"),),
    ) as batch:
        batch.drop_column("owner_id")
    op.drop_table("sessions")
    op.drop_table("users")
