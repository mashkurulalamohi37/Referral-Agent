"""Dynamic commission rules, agent types, and 4 products catalog expansion (§9, §21).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-22
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add agent_type and corporate organization fields to users table
    op.add_column("users", sa.Column("agent_type", sa.String(length=32), server_default="INDIVIDUAL", nullable=False))
    op.add_column("users", sa.Column("company_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("trade_license_number", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("tax_identification_number", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("representative_designation", sa.String(length=128), nullable=True))

    # 2. Seed / Upsert the 4 Core SaaS Products
    # Rename healora -> doctor-chamber if present
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE products 
            SET slug = 'doctor-chamber', name = 'Doctor Chamber' 
            WHERE slug = 'healora'
            """
        )
    )

    # Insert products if not existing
    products_to_seed = [
        ("pulsepos", "PulsePOS Enterprise", "http://pulsepos.local/signup"),
        ("doctor-chamber", "Doctor Chamber", "http://doctorchamber.local/signup"),
        ("ecommerce", "Omni E-Commerce Platform", "http://ecommerce.local/signup"),
        ("pharmacy-pos", "Pharmacy POS Care", "http://pharmacypos.local/signup"),
    ]

    for slug, name, signup_url in products_to_seed:
        product_id = uuid.uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO products (
                    id, slug, name, status, signup_url, allowed_redirect_hosts,
                    attribution_window_days, attribution_grace_minutes, conversion_window_days,
                    refund_window_days, confirmation_days, referrer_visibility,
                    sensitive_category, accepts_cross_product_credit, credit_max_invoice_pct,
                    referral_code_required, created_at, updated_at
                )
                VALUES (
                    :id, :slug, :name, 'ACTIVE', :signup_url, '[]'::json,
                    30, 1440, 90, 30, 14, 'MASKED',
                    false, true, 100, false, now(), now()
                )
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    updated_at = now();
                """
            ),
            {"id": product_id, "slug": slug, "name": name, "signup_url": signup_url},
        )

    # 3. Seed Default Dynamic Tiered Commission Rules for Individual & Company Agents
    # Fetch product IDs
    rows = conn.execute(sa.text("SELECT id, slug FROM products WHERE slug IN ('pulsepos', 'doctor-chamber', 'ecommerce', 'pharmacy-pos')")).fetchall()
    product_map = {r[1]: r[0] for r in rows}

    default_rules = [
        # PulsePOS Individual Progressive Tier (1-50 @ 10%, 51-100 @ 15% + 5000 bonus, 101+ @ 20%)
        {
            "id": uuid.uuid4(),
            "rule_name": "PulsePOS Individual Progressive Milestone",
            "product_id": product_map.get("pulsepos"),
            "partner_type": "INDIVIDUAL",
            "commission_type": "TIERED",
            "rate_bps": 1000,
            "tier_schedule": {
                "type": "PROGRESSIVE_VOLUME",
                "metric": "CONFIRMED_SALES_COUNT",
                "tiers": [
                    {"tier_number": 1, "tier_name": "Tier 1 (1-50 Sales)", "min_count": 1, "max_count": 50, "rate_bps": 1000, "fixed_bonus_minor": 0},
                    {"tier_number": 2, "tier_name": "Tier 2 (51-100 Sales)", "min_count": 51, "max_count": 100, "rate_bps": 1500, "fixed_bonus_minor": 500000},
                    {"tier_number": 3, "tier_name": "Tier 3 (101+ Sales Elite)", "min_count": 101, "max_count": None, "rate_bps": 2000, "fixed_bonus_minor": 1000000},
                ],
            },
            "priority": 10,
        },
        # PulsePOS Company Corporate Tier (1-50 @ 12%, 51+ @ 18% + 10000 bonus)
        {
            "id": uuid.uuid4(),
            "rule_name": "PulsePOS Company / Agency Corporate Tier",
            "product_id": product_map.get("pulsepos"),
            "partner_type": "COMPANY",
            "commission_type": "TIERED",
            "rate_bps": 1200,
            "tier_schedule": {
                "type": "PROGRESSIVE_VOLUME",
                "metric": "CONFIRMED_SALES_COUNT",
                "tiers": [
                    {"tier_number": 1, "tier_name": "Agency Tier 1 (1-50 Sales)", "min_count": 1, "max_count": 50, "rate_bps": 1200, "fixed_bonus_minor": 0},
                    {"tier_number": 2, "tier_name": "Agency Tier 2 (51+ Sales Volume)", "min_count": 51, "max_count": None, "rate_bps": 1800, "fixed_bonus_minor": 1000000},
                ],
            },
            "priority": 10,
        },
        # Doctor Chamber Standard Tiered Rule
        {
            "id": uuid.uuid4(),
            "rule_name": "Doctor Chamber Standard Referral Tier",
            "product_id": product_map.get("doctor-chamber"),
            "partner_type": None,
            "commission_type": "TIERED",
            "rate_bps": 1000,
            "tier_schedule": {
                "type": "PROGRESSIVE_VOLUME",
                "metric": "CONFIRMED_SALES_COUNT",
                "tiers": [
                    {"tier_number": 1, "tier_name": "Standard (1-30 Chambers)", "min_count": 1, "max_count": 30, "rate_bps": 1000, "fixed_bonus_minor": 0},
                    {"tier_number": 2, "tier_name": "Specialist Partner (31+ Chambers)", "min_count": 31, "max_count": None, "rate_bps": 1500, "fixed_bonus_minor": 300000},
                ],
            },
            "priority": 5,
        },
        # E-Commerce Standard Rule
        {
            "id": uuid.uuid4(),
            "rule_name": "E-Commerce Online Store Standard Tier",
            "product_id": product_map.get("ecommerce"),
            "partner_type": None,
            "commission_type": "PERCENTAGE",
            "rate_bps": 1000,
            "tier_schedule": None,
            "priority": 5,
        },
        # Pharmacy POS Standard Rule
        {
            "id": uuid.uuid4(),
            "rule_name": "Pharmacy POS Standard Tier",
            "product_id": product_map.get("pharmacy-pos"),
            "partner_type": None,
            "commission_type": "PERCENTAGE",
            "rate_bps": 1000,
            "tier_schedule": None,
            "priority": 5,
        },
    ]

    import json
    for r in default_rules:
        if r["product_id"]:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO commission_rules (
                        id, rule_name, product_id, partner_type, commission_type,
                        rate_bps, fixed_amount_minor, tier_schedule, currency,
                        min_net_paid_minor, eligible_months_from_conversion, reward_split,
                        confirmation_days, effective_from, priority, status,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :rule_name, :product_id, :partner_type, :commission_type,
                        :rate_bps, 0, :tier_schedule, 'BDT',
                        0, 12, '{"WALLET": 100}'::jsonb,
                        14, now(), :priority, 'ACTIVE',
                        now(), now()
                    )
                    ON CONFLICT DO NOTHING;
                    """
                ),
                {
                    "id": r["id"],
                    "rule_name": r["rule_name"],
                    "product_id": r["product_id"],
                    "partner_type": r["partner_type"],
                    "commission_type": r["commission_type"],
                    "rate_bps": r["rate_bps"],
                    "tier_schedule": json.dumps(r["tier_schedule"]) if r["tier_schedule"] else None,
                    "priority": r["priority"],
                },
            )


def downgrade() -> None:
    op.drop_column("users", "representative_designation")
    op.drop_column("users", "tax_identification_number")
    op.drop_column("users", "trade_license_number")
    op.drop_column("users", "company_name")
    op.drop_column("users", "agent_type")
