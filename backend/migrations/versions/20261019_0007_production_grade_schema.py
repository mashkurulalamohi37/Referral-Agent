"""Production grade schema completion: Credits, Payouts, Risk, Notifications, Reporting & Audit Logs (§21, Phase 7-14).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.core.migration_helpers import attach_forbid_mutation_trigger, detach_forbid_mutation_trigger

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. credit_reservations
    op.create_table(
        "credit_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("product_account_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("order_ref", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("requested_minor", sa.BigInteger(), nullable=False),
        sa.Column("reserved_minor", sa.BigInteger(), nullable=False),
        sa.Column("from_credit_only_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("from_available_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("captured_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("late_captured_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("payment_id", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=32), server_default="RESERVED", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_account_id"], ["product_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "idempotency_key", name="uq_credit_reservation_idempotency"),
    )
    op.create_index("ix_credit_reservations_product_id", "credit_reservations", ["product_id"])
    op.create_index("ix_credit_reservations_product_account_id", "credit_reservations", ["product_account_id"])
    op.create_index("ix_credit_reservations_user_id", "credit_reservations", ["user_id"])
    op.create_index("ix_credit_reservations_payment_id", "credit_reservations", ["payment_id"])
    op.create_index("ix_credit_reservations_state", "credit_reservations", ["state"])
    op.create_index("ix_credit_reservations_expires_at", "credit_reservations", ["expires_at"])
    op.create_index("ix_credit_reservations_user_state", "credit_reservations", ["user_id", "state"])
    op.create_index("ix_credit_reservations_expires", "credit_reservations", ["state", "expires_at"])

    # 2. credit_refunds
    op.create_table(
        "credit_refunds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reservation_id"], ["credit_reservations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "idempotency_key", name="uq_credit_refund_idempotency"),
    )
    op.create_index("ix_credit_refunds_reservation_id", "credit_refunds", ["reservation_id"])
    op.create_index("ix_credit_refunds_product_id", "credit_refunds", ["product_id"])

    # 3. payout_methods
    op.create_table(
        "payout_methods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("masked_identifier", sa.String(length=128), nullable=False),
        sa.Column("details_enc", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payout_methods_user_id", "payout_methods", ["user_id"])
    op.create_index("ix_payout_methods_status", "payout_methods", ["status"])

    # 4. payouts
    op.create_table(
        "payouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("payout_method_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("tax_withheld_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("net_minor", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=32), server_default="REQUESTED", nullable=False),
        sa.Column("provider", sa.String(length=64), server_default="manual", nullable=False),
        sa.Column("provider_ref", sa.String(length=255), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["payout_method_id"], ["payout_methods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payouts_user_id", "payouts", ["user_id"])
    op.create_index("ix_payouts_payout_method_id", "payouts", ["payout_method_id"])
    op.create_index("ix_payouts_state", "payouts", ["state"])
    op.create_index("ix_payouts_user_state", "payouts", ["user_id", "state"])

    # 5. approvals (payout approvals)
    op.create_table(
        "approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payout_id", sa.Uuid(), nullable=False),
        sa.Column("approver_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payout_id"], ["payouts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approvals_payout_id", "approvals", ["payout_id"])
    op.create_index("ix_approvals_approver_user_id", "approvals", ["approver_user_id"])

    # 6. risk_signals
    op.create_table(
        "risk_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("product_account_id", sa.Uuid(), nullable=True),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("value_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_account_id"], ["product_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["inbound_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_signals_user_id", "risk_signals", ["user_id"])
    op.create_index("ix_risk_signals_product_account_id", "risk_signals", ["product_account_id"])
    op.create_index("ix_risk_signals_kind", "risk_signals", ["kind"])
    op.create_index("ix_risk_signals_value_hash", "risk_signals", ["value_hash"])

    # 7. risk_cases
    op.create_table(
        "risk_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_number", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("product_account_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("rule_name", sa.String(length=128), nullable=False),
        sa.Column("details_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_account_id"], ["product_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_number"),
    )
    op.create_index("ix_risk_cases_case_number", "risk_cases", ["case_number"])
    op.create_index("ix_risk_cases_status", "risk_cases", ["status"])
    op.create_index("ix_risk_cases_severity", "risk_cases", ["severity"])
    op.create_index("ix_risk_cases_user_id", "risk_cases", ["user_id"])

    # 8. notification_templates
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("subject_template", sa.String(length=255), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_key", "channel", "locale", "version", name="uq_notification_template_version"),
    )
    op.create_index("ix_notification_templates_template_key", "notification_templates", ["template_key"])

    # 9. notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])

    # 10. reconciliation_runs
    op.create_table(
        "reconciliation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("discrepancy_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("details_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliation_runs_run_type", "reconciliation_runs", ["run_type"])

    # 11. audit_logs (insert-only, Invariant I2)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("diff_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    attach_forbid_mutation_trigger(op, "audit_logs")


def downgrade() -> None:
    detach_forbid_mutation_trigger(op, "audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("reconciliation_runs")
    op.drop_table("notifications")
    op.drop_table("notification_templates")
    op.drop_table("risk_cases")
    op.drop_table("risk_signals")
    op.drop_table("approvals")
    op.drop_table("payouts")
    op.drop_table("payout_methods")
    op.drop_table("credit_refunds")
    op.drop_table("credit_reservations")
