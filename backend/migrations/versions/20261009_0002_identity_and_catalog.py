"""Identity and catalog schema tables (§21, Phase 2).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.core.migration_helpers import attach_forbid_mutation_trigger, detach_forbid_mutation_trigger

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("phone_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("locale", sa.String(10), server_default="en", nullable=False),
        sa.Column("time_zone", sa.String(64), server_default="Asia/Dhaka", nullable=False),
        sa.Column("status", sa.String(32), server_default="ACTIVE", nullable=False),
        sa.Column("kyc_status", sa.String(32), server_default="NONE", nullable=False),
        sa.Column("totp_secret_enc", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_users_email_lower_unique",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL AND deleted_at IS NULL"),
    )

    # 2. user_roles
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(32), primary_key=True),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. refresh_tokens [Insert-Only]
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), unique=True, nullable=False),
        sa.Column("replaced_by", sa.Uuid(), sa.ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    # 4. products
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), server_default="ACTIVE", nullable=False),
        sa.Column("signup_url", sa.Text(), nullable=False),
        sa.Column("allowed_redirect_hosts", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("attribution_window_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("attribution_grace_minutes", sa.Integer(), server_default="1440", nullable=False),
        sa.Column("conversion_window_days", sa.Integer(), server_default="90", nullable=False),
        sa.Column("refund_window_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("confirmation_days", sa.Integer(), server_default="14", nullable=False),
        sa.Column("referrer_visibility", sa.String(32), server_default="MASKED", nullable=False),
        sa.Column("sensitive_category", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("accepts_cross_product_credit", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("credit_max_invoice_pct", sa.Integer(), server_default="100", nullable=False),
        sa.Column("referral_code_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("theme", sa.JSON(), nullable=True),
        sa.Column("outbound_webhook_url", sa.Text(), nullable=True),
        sa.Column("outbound_signing_secret_enc", sa.LargeBinary(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_products_slug", "products", ["slug"])

    # 5. plans
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), server_default="ACTIVE", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_id", "plan_code", name="uq_plans_product_id_plan_code"),
    )
    op.create_index("ix_plans_product_id", "plans", ["product_id"])

    # 6. api_clients
    op.create_table(
        "api_clients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_id", sa.String(64), unique=True, nullable=False),
        sa.Column("scopes", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_clients_product_id", "api_clients", ["product_id"])
    op.create_index("ix_api_clients_key_id", "api_clients", ["key_id"])

    # 7. api_client_secrets
    op.create_table(
        "api_client_secrets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("api_client_id", sa.Uuid(), sa.ForeignKey("api_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("secret_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("signing_secret_enc", sa.LargeBinary(), nullable=True),
        sa.Column("status", sa.String(32), server_default="ACTIVE", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_client_secrets_api_client_id", "api_client_secrets", ["api_client_id"])

    # 8. product_accounts
    op.create_table(
        "product_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_id", "external_user_id", name="uq_product_accounts_product_external_user"),
    )
    op.create_index("ix_product_accounts_product_id", "product_accounts", ["product_id"])
    op.create_index("ix_product_accounts_user_id", "product_accounts", ["user_id"])

    # 9. auth_handoff_tokens [Insert-Only]
    op.create_table(
        "auth_handoff_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.LargeBinary(32), unique=True, nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_account_id", sa.Uuid(), sa.ForeignKey("product_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auth_handoff_tokens_product_id", "auth_handoff_tokens", ["product_id"])
    op.create_index("ix_auth_handoff_tokens_product_account_id", "auth_handoff_tokens", ["product_account_id"])

    # 10. otp_challenges [Insert-Only]
    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("destination_hash", sa.String(128), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_otp_challenges_destination_hash", "otp_challenges", ["destination_hash"])


def downgrade() -> None:
    op.drop_table("otp_challenges")
    op.drop_table("auth_handoff_tokens")
    op.drop_table("product_accounts")
    op.drop_table("api_client_secrets")
    op.drop_table("api_clients")
    op.drop_table("plans")
    op.drop_table("products")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("users")
