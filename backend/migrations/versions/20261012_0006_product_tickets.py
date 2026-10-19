"""Product tickets, messages, attachments, and audit logs schema (§21, Phase 1).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. product_tickets
    op.create_table(
        "product_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_number", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="NEW", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("system_diagnostics", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assigned_agent_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_agent_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_number"),
    )
    op.create_index("ix_product_tickets_ticket_number", "product_tickets", ["ticket_number"])
    op.create_index("ix_product_tickets_product_id", "product_tickets", ["product_id"])
    op.create_index("ix_product_tickets_external_user_id", "product_tickets", ["external_user_id"])
    op.create_index("ix_product_tickets_category", "product_tickets", ["category"])
    op.create_index("ix_product_tickets_severity", "product_tickets", ["severity"])
    op.create_index("ix_product_tickets_status", "product_tickets", ["status"])
    op.create_index("ix_product_tickets_assigned_agent_id", "product_tickets", ["assigned_agent_id"])
    op.create_index("ix_product_tickets_sla_due_at", "product_tickets", ["sla_due_at"])

    # 2. product_ticket_messages
    op.create_table(
        "product_ticket_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("sender_type", sa.String(length=32), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=True),
        sa.Column("sender_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal_note", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["product_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_ticket_messages_ticket_id", "product_ticket_messages", ["ticket_id"])

    # 3. product_ticket_attachments
    op.create_table(
        "product_ticket_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("mime_type", sa.String(length=64), server_default="application/octet-stream", nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["product_ticket_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_ticket_attachments_message_id", "product_ticket_attachments", ["message_id"])

    # 4. product_ticket_audit_logs
    op.create_table(
        "product_ticket_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["product_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_ticket_audit_logs_ticket_id", "product_ticket_audit_logs", ["ticket_id"])


def downgrade() -> None:
    op.drop_table("product_ticket_audit_logs")
    op.drop_table("product_ticket_attachments")
    op.drop_table("product_ticket_messages")
    op.drop_table("product_tickets")
