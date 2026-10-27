"""add task priority and due_date

Revision ID: c7d41a9e3f10
Revises: b2ec53722aec
Create Date: 2026-10-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d41a9e3f10'
down_revision: Union[str, Sequence[str], None] = 'b2ec53722aec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 기존 행은 priority NORMAL, due_date NULL(마감일 없음)이 된다 (R-011, R-012).
    # batch(테이블 재생성)는 이름 없는 status CHECK를 떨어뜨리므로 쓰지 않고 열만 더한다.
    op.execute(
        "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'NORMAL' "
        "CHECK (priority IN ('LOW', 'NORMAL', 'HIGH'))"
    )
    op.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")


def downgrade() -> None:
    """Downgrade schema."""
    # 열 삭제는 테이블을 다시 만들므로 status CHECK를 명시해서 유지한다.
    with op.batch_alter_table(
        "tasks",
        table_args=(sa.CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'DONE')"),),
    ) as batch:
        batch.drop_column("due_date")
        batch.drop_column("priority")
