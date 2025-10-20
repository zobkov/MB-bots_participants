"""Create event registrations table

Revision ID: b3b7a0d3c5f1
Revises: ee28b55a2757
Create Date: 2025-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3b7a0d3c5f1"
down_revision: Union[str, None] = "ee28b55a2757"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "event_registrations" in inspector.get_table_names():
        existing_indexes = {index["name"] for index in inspector.get_indexes("event_registrations")}
        desired_indexes = {
            "ix_event_registrations_user_id": ("user_id",),
            "ix_event_registrations_event_id": ("event_id",),
            "ix_event_registrations_group_id": ("group_id",),
        }

        for name, columns in desired_indexes.items():
            if name not in existing_indexes:
                op.create_index(name, "event_registrations", list(columns), unique=False)
        return

    op.create_table(
        "event_registrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(length=32), nullable=False),
        sa.Column("group_id", sa.String(length=32), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "group_id", name="uq_event_registration_user_group"),
        sa.UniqueConstraint("user_id", "event_id", name="uq_event_registration_user_event"),
    )
    op.create_index("ix_event_registrations_user_id", "event_registrations", ["user_id"], unique=False)
    op.create_index("ix_event_registrations_event_id", "event_registrations", ["event_id"], unique=False)
    op.create_index("ix_event_registrations_group_id", "event_registrations", ["group_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_event_registrations_group_id", table_name="event_registrations")
    op.drop_index("ix_event_registrations_event_id", table_name="event_registrations")
    op.drop_index("ix_event_registrations_user_id", table_name="event_registrations")
    op.drop_table("event_registrations")
