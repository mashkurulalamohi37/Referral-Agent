"""Events and Subscriptions schema tables (§21, Phase 4).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.core.migration_helpers import attach_forbid_mutation_trigger, detach_forbid_mutation_trigger

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. inbound_events (insert-only, ADR 0006)
    op.create_table(
        "inbound_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_sha256", sa.LargeBinary(length=32), nullable=False),
        sa.Column("raw_payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_inbound_events_product_id_products"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inbound_events")),
    )
    op.create_index(
        "ix_inbound_events_product_event_unique",
        "inbound_events",
        ["product_id", "event_id"],
        unique=True,
    )
    op.create_index(op.f("ix_inbound_events_product_id"), "inbound_events", ["product_id"])
    op.create_index(op.f("ix_inbound_events_event_type"), "inbound_events", ["event_type"])
    op.create_index(op.f("ix_inbound_events_occurred_at"), "inbound_events", ["occurred_at"])
    op.create_index(op.f("ix_inbound_events_status"), "inbound_events", ["status"])

    # 2. outbox
    op.create_table(
        "outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox")),
    )
    op.create_index(op.f("ix_outbox_aggregate_type"), "outbox", ["aggregate_type"])
    op.create_index(op.f("ix_outbox_aggregate_id"), "outbox", ["aggregate_id"])
    op.create_index(op.f("ix_outbox_event_type"), "outbox", ["event_type"])
    op.create_index(op.f("ix_outbox_status"), "outbox", ["status"])
    op.create_index(op.f("ix_outbox_scheduled_at"), "outbox", ["scheduled_at"])

    # 3. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_account_id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.String(length=255), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_subscriptions_product_id_products"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_account_id"], ["product_accounts.id"], name=op.f("fk_subscriptions_product_account_id_product_accounts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
    )
    op.create_index(
        "ix_subscriptions_product_sub_unique",
        "subscriptions",
        ["product_id", "subscription_id"],
        unique=True,
    )
    op.create_index(op.f("ix_subscriptions_product_id"), "subscriptions", ["product_id"])
    op.create_index(op.f("ix_subscriptions_product_account_id"), "subscriptions", ["product_account_id"])
    op.create_index(op.f("ix_subscriptions_external_user_id"), "subscriptions", ["external_user_id"])
    op.create_index(op.f("ix_subscriptions_status"), "subscriptions", ["status"])

    # 4. payment_facts (insert-only, ADR 0006)
    op.create_table(
        "payment_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.String(length=255), nullable=False),
        sa.Column("subscription_id", sa.String(length=255), nullable=True),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=True),
        sa.Column("billing_reason", sa.String(length=32), server_default="initial", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("amount_gross", sa.BigInteger(), nullable=False),
        sa.Column("discount_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("tax_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("credit_applied_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("credit_reservation_id", sa.Uuid(), nullable=True),
        sa.Column("amount_net_paid", sa.BigInteger(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payment_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_payment_facts_product_id_products"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_facts")),
    )
    op.create_index(
        "ix_payment_facts_product_payment_unique",
        "payment_facts",
        ["product_id", "payment_id"],
        unique=True,
    )
    op.create_index(op.f("ix_payment_facts_product_id"), "payment_facts", ["product_id"])
    op.create_index(op.f("ix_payment_facts_payment_id"), "payment_facts", ["payment_id"])
    op.create_index(op.f("ix_payment_facts_subscription_id"), "payment_facts", ["subscription_id"])
    op.create_index(op.f("ix_payment_facts_external_user_id"), "payment_facts", ["external_user_id"])
    attach_forbid_mutation_trigger(op, "payment_facts")

    # 5. refund_facts (insert-only, ADR 0006)
    op.create_table(
        "refund_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("refund_id", sa.String(length=255), nullable=False),
        sa.Column("payment_id", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BDT", nullable=False),
        sa.Column("amount_refunded", sa.BigInteger(), nullable=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_refund_facts_product_id_products"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refund_facts")),
    )
    op.create_index(
        "ix_refund_facts_product_refund_unique",
        "refund_facts",
        ["product_id", "refund_id"],
        unique=True,
    )
    op.create_index(op.f("ix_refund_facts_product_id"), "refund_facts", ["product_id"])
    op.create_index(op.f("ix_refund_facts_refund_id"), "refund_facts", ["refund_id"])
    op.create_index(op.f("ix_refund_facts_payment_id"), "refund_facts", ["payment_id"])
    attach_forbid_mutation_trigger(op, "refund_facts")


def downgrade() -> None:
    detach_forbid_mutation_trigger(op, "refund_facts")
    op.drop_index(op.f("ix_refund_facts_payment_id"), table_name="refund_facts")
    op.drop_index(op.f("ix_refund_facts_refund_id"), table_name="refund_facts")
    op.drop_index(op.f("ix_refund_facts_product_id"), table_name="refund_facts")
    op.drop_index("ix_refund_facts_product_refund_unique", table_name="refund_facts")
    op.drop_table("refund_facts")

    detach_forbid_mutation_trigger(op, "payment_facts")
    op.drop_index(op.f("ix_payment_facts_external_user_id"), table_name="payment_facts")
    op.drop_index(op.f("ix_payment_facts_subscription_id"), table_name="payment_facts")
    op.drop_index(op.f("ix_payment_facts_payment_id"), table_name="payment_facts")
    op.drop_index(op.f("ix_payment_facts_product_id"), table_name="payment_facts")
    op.drop_index("ix_payment_facts_product_payment_unique", table_name="payment_facts")
    op.drop_table("payment_facts")

    op.drop_index(op.f("ix_subscriptions_status"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_external_user_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_product_account_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_product_id"), table_name="subscriptions")
    op.drop_index("ix_subscriptions_product_sub_unique", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index(op.f("ix_outbox_scheduled_at"), table_name="outbox")
    op.drop_index(op.f("ix_outbox_status"), table_name="outbox")
    op.drop_index(op.f("ix_outbox_event_type"), table_name="outbox")
    op.drop_index(op.f("ix_outbox_aggregate_id"), table_name="outbox")
    op.drop_index(op.f("ix_outbox_aggregate_type"), table_name="outbox")
    op.drop_table("outbox")

    op.drop_index(op.f("ix_inbound_events_status"), table_name="inbound_events")
    op.drop_index(op.f("ix_inbound_events_occurred_at"), table_name="inbound_events")
    op.drop_index(op.f("ix_inbound_events_event_type"), table_name="inbound_events")
    op.drop_index(op.f("ix_inbound_events_product_id"), table_name="inbound_events")
    op.drop_index("ix_inbound_events_product_event_unique", table_name="inbound_events")
    op.drop_table("inbound_events")
