"""Referrals schema: codes, clicks, attributions (§21, Phase 3).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.core.migration_helpers import attach_forbid_mutation_trigger, detach_forbid_mutation_trigger

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. referral_codes
    op.create_table(
        "referral_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("is_vanity", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("attribution_window_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_referral_codes_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_referral_codes_product_id_products"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referral_codes")),
    )
    op.create_index(
        "ix_referral_codes_code_upper_unique",
        "referral_codes",
        [sa.text("upper(code)")],
        unique=True,
    )
    op.create_index(op.f("ix_referral_codes_user_id"), "referral_codes", ["user_id"])
    op.create_index(op.f("ix_referral_codes_product_id"), "referral_codes", ["product_id"])
    op.create_index(op.f("ix_referral_codes_campaign_id"), "referral_codes", ["campaign_id"])

    # 2. referral_clicks (insert-only, ADR 0006)
    op.create_table(
        "referral_clicks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("ip_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("user_agent_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("referer_url", sa.String(length=1024), nullable=True),
        sa.Column("campaign", sa.String(length=64), nullable=True),
        sa.Column("utm_source", sa.String(length=64), nullable=True),
        sa.Column("utm_medium", sa.String(length=64), nullable=True),
        sa.Column("utm_campaign", sa.String(length=64), nullable=True),
        sa.Column("utm_content", sa.String(length=64), nullable=True),
        sa.Column("utm_term", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["code_id"], ["referral_codes.id"], name=op.f("fk_referral_clicks_code_id_referral_codes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_referral_clicks_product_id_products"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referral_clicks")),
    )
    op.create_index(op.f("ix_referral_clicks_code_id"), "referral_clicks", ["code_id"])
    op.create_index(op.f("ix_referral_clicks_product_id"), "referral_clicks", ["product_id"])
    attach_forbid_mutation_trigger(op, "referral_clicks")

    # 3. attributions
    op.create_table(
        "attributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_account_id", sa.Uuid(), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("referrer_user_id", sa.Uuid(), nullable=False),
        sa.Column("code_id", sa.Uuid(), nullable=False),
        sa.Column("click_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="ATTRIBUTED", nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signals_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_attributions_product_id_products"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_account_id"], ["product_accounts.id"], name=op.f("fk_attributions_product_account_id_product_accounts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["users.id"], name=op.f("fk_attributions_referrer_user_id_users"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["code_id"], ["referral_codes.id"], name=op.f("fk_attributions_code_id_referral_codes"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["click_id"], ["referral_clicks.id"], name=op.f("fk_attributions_click_id_referral_clicks"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attributions")),
    )
    op.create_index(
        "ix_attributions_product_external_unique",
        "attributions",
        ["product_id", "external_user_id"],
        unique=True,
    )
    op.create_index(op.f("ix_attributions_product_id"), "attributions", ["product_id"])
    op.create_index(op.f("ix_attributions_product_account_id"), "attributions", ["product_account_id"])
    op.create_index(op.f("ix_attributions_referrer_user_id"), "attributions", ["referrer_user_id"])
    op.create_index(op.f("ix_attributions_code_id"), "attributions", ["code_id"])
    op.create_index(op.f("ix_attributions_click_id"), "attributions", ["click_id"])
    op.create_index(op.f("ix_attributions_external_user_id"), "attributions", ["external_user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_attributions_external_user_id"), table_name="attributions")
    op.drop_index(op.f("ix_attributions_click_id"), table_name="attributions")
    op.drop_index(op.f("ix_attributions_code_id"), table_name="attributions")
    op.drop_index(op.f("ix_attributions_referrer_user_id"), table_name="attributions")
    op.drop_index(op.f("ix_attributions_product_account_id"), table_name="attributions")
    op.drop_index(op.f("ix_attributions_product_id"), table_name="attributions")
    op.drop_index("ix_attributions_product_external_unique", table_name="attributions")
    op.drop_table("attributions")

    detach_forbid_mutation_trigger(op, "referral_clicks")
    op.drop_index(op.f("ix_referral_clicks_product_id"), table_name="referral_clicks")
    op.drop_index(op.f("ix_referral_clicks_code_id"), table_name="referral_clicks")
    op.drop_table("referral_clicks")

    op.drop_index(op.f("ix_referral_codes_campaign_id"), table_name="referral_codes")
    op.drop_index(op.f("ix_referral_codes_product_id"), table_name="referral_codes")
    op.drop_index(op.f("ix_referral_codes_user_id"), table_name="referral_codes")
    op.drop_index("ix_referral_codes_code_upper_unique", table_name="referral_codes")
    op.drop_table("referral_codes")
