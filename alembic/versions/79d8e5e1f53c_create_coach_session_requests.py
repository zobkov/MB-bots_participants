"""Create coach session requests table

Revision ID: 79d8e5e1f53c
Revises: ee28b55a2757
Create Date: 2025-10-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "79d8e5e1f53c"
down_revision: Union[str, None] = "b3b7a0d3c5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "coach_session_requests" in inspector.get_table_names():
        existing_indexes = {index["name"] for index in inspector.get_indexes("coach_session_requests")}
        if "ix_coach_session_requests_user_id" not in existing_indexes:
            op.create_index("ix_coach_session_requests_user_id", "coach_session_requests", ["user_id"], unique=False)
        return

    op.create_table(
        "coach_session_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("university", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.Column("telegram", sa.String(length=128), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_coach_session_requests_user_id", "coach_session_requests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_coach_session_requests_user_id", table_name="coach_session_requests")
    op.drop_table("coach_session_requests")
