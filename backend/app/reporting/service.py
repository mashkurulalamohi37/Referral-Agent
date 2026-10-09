"""Reporting, dashboard metrics, and daily product reconciliation service (§17.2, §17.3, ADR 0017)."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.commissions import service as commissions_service
from app.core import clock
from app.payouts import service as payouts_service
from app.referrals import service as referrals_service
from app.reporting.models import ReconciliationRun
from app.risk import service as risk_service
from app.subscriptions import service as subscriptions_service


async def get_admin_dashboard_metrics(
    session: AsyncSession,
    *,
    product_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Aggregates high-level metrics for the Admin Dashboard (§17.2)."""
    # 1. Total Clicks, Attributed Referrals & Conversions
    total_clicks, total_referrals, total_conversions = await referrals_service.get_referral_metrics(
        session, product_id=product_id
    )

    conversion_rate = (total_conversions / total_referrals * 100) if total_referrals > 0 else 0.0

    # 2. Revenue from referred payments
    gross_rev, net_rev, credit_redeemed = await subscriptions_service.get_revenue_metrics(
        session, product_id=product_id
    )

    # 3. Commission Breakdown
    comm_pending, comm_available = await commissions_service.get_commission_metrics(
        session, product_id=product_id
    )

    # 4. Total Paid Out
    total_paid_out = await payouts_service.get_total_paid_out(session)

    # 5. Open Risk Cases
    open_risk_cases = await risk_service.get_open_cases_count(session)

    return {
        "total_clicks": total_clicks,
        "total_referrals": total_referrals,
        "total_conversions": total_conversions,
        "conversion_rate_pct": round(conversion_rate, 2),
        "gross_revenue_minor": int(gross_rev),
        "net_revenue_minor": int(net_rev),
        "credit_redeemed_minor": int(credit_redeemed),
        "commission_pending_minor": comm_pending,
        "commission_available_minor": comm_available,
        "total_paid_out_minor": total_paid_out,
        "open_risk_cases": open_risk_cases,
    }


async def export_commissions_csv(
    session: AsyncSession,
    *,
    product_id: uuid.UUID | None = None,
) -> str:
    """Exports commission ledger report to CSV format (§17.3)."""
    commissions = await commissions_service.get_all_commissions(session, product_id=product_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Commission ID",
        "Payment ID",
        "Referral ID",
        "Referrer User ID",
        "Currency",
        "Amount (BDT)",
        "Reversed (BDT)",
        "State",
        "Created At",
    ])

    for c in commissions:
        writer.writerow([
            str(c.id),
            str(c.payment_id),
            str(c.attribution_id),
            str(c.referrer_user_id),
            c.currency,
            f"{c.amount_minor // 100}.{c.amount_minor % 100:02d}",
            f"{c.reversed_minor // 100}.{c.reversed_minor % 100:02d}",
            c.status,
            c.created_at.isoformat(),
        ])

    return output.getvalue()


async def process_daily_payment_reconciliation(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    business_date: date,
    payments: list[dict[str, Any]],
) -> ReconciliationRun:
    """Processes daily payment reconciliation to detect missed events or mismatches (ADR 0017, §20)."""
    submitted_count = len(payments)
    matched_count = 0
    missing_count = 0
    mismatch_count = 0
    mismatches: list[dict[str, Any]] = []

    for item in payments:
        pid = str(item.get("payment_id"))
        expected_amount = int(item.get("amount_net_paid", 0))

        record = await subscriptions_service.get_payment_fact(
            session, product_id=product_id, payment_id=pid
        )

        if not record:
            missing_count += 1
            mismatches.append({"payment_id": pid, "issue": "MISSING_ON_PLATFORM"})
        elif record.amount_net_paid != expected_amount:
            mismatch_count += 1
            mismatches.append({
                "payment_id": pid,
                "issue": "AMOUNT_MISMATCH",
                "expected": expected_amount,
                "recorded": record.amount_net_paid,
            })
        else:
            matched_count += 1

    run = ReconciliationRun(
        product_id=product_id,
        business_date=business_date,
        submitted_count=submitted_count,
        matched_count=matched_count,
        missing_count=missing_count,
        mismatch_count=mismatch_count,
        details_json={"mismatches": mismatches},
    )
    session.add(run)
    await session.flush()
    return run
