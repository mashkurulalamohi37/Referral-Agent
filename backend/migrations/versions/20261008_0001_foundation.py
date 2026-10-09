"""Foundation: extensions and the insert-only trigger function.

Revision ID: 0001
Revises:
Create Date: 2026-10-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.core.migration_helpers import (
    DROP_FORBID_MUTATION_FUNCTION_SQL,
    FORBID_MUTATION_FUNCTION_SQL,
)

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # btree_gist: exclusion constraint that prevents commission rule ties (ADR 0022).
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
    op.execute(FORBID_MUTATION_FUNCTION_SQL)


def downgrade() -> None:
    op.execute(DROP_FORBID_MUTATION_FUNCTION_SQL)
    op.execute("DROP EXTENSION IF EXISTS btree_gist;")
