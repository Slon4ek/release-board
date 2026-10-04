"""initial migrations

Revision ID: 733acd6c7ae8
Revises:
Create Date: 2026-10-01 15:46:04.296993

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "733acd6c7ae8"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE release_environment AS ENUM ('dev', 'stage', 'prod');
    """)
    op.execute("""
        CREATE TYPE release_status AS ENUM (
            'planned', 'deployed', 'failed', 'rolled_back'
        );
    """)

    op.create_table(
        "releases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "environment",
            postgresql.ENUM("dev", "stage", "prod", name="release_environment", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("planned", "deployed", "failed", "rolled_back", name="release_status", create_type=False),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("releases")
    op.execute("DROP TYPE IF EXISTS release_status;")
    op.execute("DROP TYPE IF EXISTS release_environment;")
