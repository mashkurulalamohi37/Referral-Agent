"""Commissions and Ledger schema tables (§21, Phase 5).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.core.migration_helpers import attach_forbid_mutation_trigger, detach_forbid_mutation_trigger

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. commission_rules
    op.create_table(
        "commission_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_name", sa.String(length=128), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("plan_code", sa.String(length=64), nullable=True),
        sa.Column("partner_type", sa.String(length=32), nullable=True),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("billing_reason", sa.String(length=32), nullable=True),
        sa.Column("commission_type", sa.String(length=32), server_default="PERCENTAGE", nullable=False),
        sa.Column("rate_bps", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("fixed_amount_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("tier_schedule", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("min_net_paid_minor", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("max_commission_minor", sa.BigInteger(), nullable=True),
        sa.Column("eligible_months_from_conversion", sa.Integer(), server_default="12", nullable=False),
        sa.Column("max_payments_per_referral", sa.Integer(), nullable=True),
        sa.Column("reward_split", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confirmation_days", sa.Integer(), server_default="14", nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_commission_rules_product_id_products"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["users.id"], name=op.f("fk_commission_rules_partner_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commission_rules")),
    )
    op.create_index(op.f("ix_commission_rules_product_id"), "commission_rules", ["product_id"])
    op.create_index(op.f("ix_commission_rules_plan_code"), "commission_rules", ["plan_code"])
    op.create_index(op.f("ix_commission_rules_partner_type"), "commission_rules", ["partner_type"])
    op.create_index(op.f("ix_commission_rules_partner_id"), "commission_rules", ["partner_id"])
    op.create_index(op.f("ix_commission_rules_campaign_id"), "commission_rules", ["campaign_id"])
    op.create_index(op.f("ix_commission_rules_billing_reason"), "commission_rules", ["billing_reason"])
    op.create_index(op.f("ix_commission_rules_status"), "commission_rules", ["status"])
    op.create_index(op.f("ix_commission_rules_effective_from"), "commission_rules", ["effective_from"])

    # 2. commissions
    op.create_table(
        "commissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("referrer_user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.String(length=255), nullable=False),
        sa.Column("attribution_id", sa.Uuid(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("confirmation_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculation_snapshot", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["commission_rules.id"], name=op.f("fk_commissions_rule_id_commission_rules"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["users.id"], name=op.f("fk_commissions_referrer_user_id_users"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_commissions_product_id_products"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attribution_id"], ["attributions.id"], name=op.f("fk_commissions_attribution_id_attributions"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commissions")),
    )
    op.create_index(
        "ix_commissions_product_payment_unique",
        "commissions",
        ["product_id", "payment_id"],
        unique=True,
    )
    op.create_index(op.f("ix_commissions_rule_id"), "commissions", ["rule_id"])
    op.create_index(op.f("ix_commissions_referrer_user_id"), "commissions", ["referrer_user_id"])
    op.create_index(op.f("ix_commissions_product_id"), "commissions", ["product_id"])
    op.create_index(op.f("ix_commissions_attribution_id"), "commissions", ["attribution_id"])
    op.create_index(op.f("ix_commissions_status"), "commissions", ["status"])
    op.create_index(op.f("ix_commissions_confirmation_due_at"), "commissions", ["confirmation_due_at"])

    # 3. ledger_accounts
    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_number", sa.String(length=128), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_ledger_accounts_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_ledger_accounts_product_id_products"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_accounts")),
    )
    op.create_index(op.f("ix_ledger_accounts_account_number"), "ledger_accounts", ["account_number"], unique=True)
    op.create_index(op.f("ix_ledger_accounts_account_type"), "ledger_accounts", ["account_type"])
    op.create_index(op.f("ix_ledger_accounts_user_id"), "ledger_accounts", ["user_id"])
    op.create_index(op.f("ix_ledger_accounts_product_id"), "ledger_accounts", ["product_id"])

    # 4. journal_transactions (insert-only, ADR 0006)
    op.create_table(
        "journal_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_type", sa.String(length=64), nullable=False),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_transactions")),
    )
    op.create_index(op.f("ix_journal_transactions_idempotency_key"), "journal_transactions", ["idempotency_key"], unique=True)
    op.create_index(op.f("ix_journal_transactions_transaction_type"), "journal_transactions", ["transaction_type"])
    op.create_index(op.f("ix_journal_transactions_reference_type"), "journal_transactions", ["reference_type"])
    op.create_index(op.f("ix_journal_transactions_reference_id"), "journal_transactions", ["reference_id"])
    attach_forbid_mutation_trigger(op, "journal_transactions")

    # 5. ledger_entries (insert-only, ADR 0006)
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["journal_transactions.id"], name=op.f("fk_ledger_entries_transaction_id_journal_transactions"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["account_id"], ["ledger_accounts.id"], name=op.f("fk_ledger_entries_account_id_ledger_accounts"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
    )
    op.create_index(op.f("ix_ledger_entries_transaction_id"), "ledger_entries", ["transaction_id"])
    op.create_index(op.f("ix_ledger_entries_account_id"), "ledger_entries", ["account_id"])
    attach_forbid_mutation_trigger(op, "ledger_entries")


def downgrade() -> None:
    detach_forbid_mutation_trigger(op, "ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_account_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_transaction_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")

    detach_forbid_mutation_trigger(op, "journal_transactions")
    op.drop_index(op.f("ix_journal_transactions_reference_id"), table_name="journal_transactions")
    op.drop_index(op.f("ix_journal_transactions_reference_type"), table_name="journal_transactions")
    op.drop_index(op.f("ix_journal_transactions_transaction_type"), table_name="journal_transactions")
    op.drop_index(op.f("ix_journal_transactions_idempotency_key"), table_name="journal_transactions")
    op.drop_table("journal_transactions")

    op.drop_index(op.f("ix_ledger_accounts_product_id"), table_name="ledger_accounts")
    op.drop_index(op.f("ix_ledger_accounts_user_id"), table_name="ledger_accounts")
    op.drop_index(op.f("ix_ledger_accounts_account_type"), table_name="ledger_accounts")
    op.drop_index(op.f("ix_ledger_accounts_account_number"), table_name="ledger_accounts")
    op.drop_table("ledger_accounts")

    op.drop_index(op.f("ix_commissions_confirmation_due_at"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_status"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_attribution_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_product_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_referrer_user_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_rule_id"), table_name="commissions")
    op.drop_index("ix_commissions_product_payment_unique", table_name="commissions")
    op.drop_table("commissions")

    op.drop_index(op.f("ix_commission_rules_effective_from"), table_name="commission_rules")
    op.drop_index(op.f("ix_commission_rules_status"), table_name="commission_rules")
    op.drop_index(op.f("ix_commission_rules_billing_reason"), table_name="commission_rules")
    op.drop_index(op.f("ix_commission_rules_campaign_id"), table_name="commission_rules")
    op.drop_index(op.f("ix_commission_rules_partner_id"), table_name="commission_rules")
    op.drop_index(op.f("ix_commission_rules_partner_type"), table_name="commission_rules")
    op.drop_index(op.f("ix_commission_rules_plan_code"), table_name="commission_rules")
    op.drop_index(op.f("ix_commission_rules_product_id"), table_name="commission_rules")
    op.drop_table("commission_rules")
