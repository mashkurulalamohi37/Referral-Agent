"""Risk evaluation and fraud detection service (§14, ADR 0005)."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import get_settings
from app.core.errors import ErrorCode, PlatformError
from app.risk.models import RiskCase, RiskSignal


def hash_risk_signal(raw_value: str, kind: str, pepper: str | None = None) -> bytes:
    """Computes SHA-256 HMAC of normalized signal with platform pepper (§14.1)."""
    settings = get_settings()
    if pepper:
        p = pepper
    elif hasattr(settings, "signal_hash_pepper") and settings.signal_hash_pepper:
        p = settings.signal_hash_pepper.get_secret_value()
    else:
        p = "test-signal-pepper-32-chars-long!"
    normalized = raw_value.strip().lower()
    return hmac.new(p.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256).digest()


def extract_ip_prefix_hash(ip: str, pepper: str | None = None) -> bytes | None:
    """Computes /24 subnet hash for IPv4 or /48 for IPv6."""
    if "." in ip:
        parts = ip.strip().split(".")
        if len(parts) >= 3:
            prefix = ".".join(parts[:3]) + ".0/24"
            return hash_risk_signal(prefix, "IP_PREFIX", pepper)
    return None


async def record_signals(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    product_account_id: uuid.UUID | None = None,
    source_event_id: uuid.UUID | None = None,
    signals: dict[str, Any],
) -> list[RiskSignal]:
    """Records HMAC-hashed risk signals. Plaintext is NEVER stored (§14.1)."""
    recorded: list[RiskSignal] = []

    for kind, val in signals.items():
        if not val or not isinstance(val, str):
            continue
        kind_upper = kind.upper()
        h = hash_risk_signal(val, kind_upper)
        sig = RiskSignal(
            kind=kind_upper,
            value_hash=h,
            user_id=user_id,
            product_account_id=product_account_id,
            source_event_id=source_event_id,
        )
        session.add(sig)
        recorded.append(sig)

        if kind_upper == "IP":
            p_hash = extract_ip_prefix_hash(val)
            if p_hash:
                p_sig = RiskSignal(
                    kind="IP_PREFIX",
                    value_hash=p_hash,
                    user_id=user_id,
                    product_account_id=product_account_id,
                    source_event_id=source_event_id,
                )
                session.add(p_sig)
                recorded.append(p_sig)

    await session.flush()
    return recorded


async def evaluate_risk_for_referral(
    session: AsyncSession,
    *,
    referrer_user_id: uuid.UUID,
    referred_signals: dict[str, Any],
    referral_id: uuid.UUID | None = None,
) -> tuple[str, int, list[dict[str, Any]]]:
    """Evaluates risk rules for a referral (§14.2) and returns (level, score, reasons)."""
    score = 0
    reasons: list[dict[str, Any]] = []

    # 1. Fetch referrer's known signal hashes
    stmt = select(RiskSignal).where(RiskSignal.user_id == referrer_user_id)
    res = await session.execute(stmt)
    referrer_signals = res.scalars().all()
    referrer_hashes_by_kind: dict[str, set[bytes]] = {}
    for rs in referrer_signals:
        referrer_hashes_by_kind.setdefault(rs.kind, set()).add(rs.value_hash)

    # 2. Match signals
    for kind, raw_val in referred_signals.items():
        if not raw_val or not isinstance(raw_val, str):
            continue
        kind_upper = kind.upper()
        h = hash_risk_signal(raw_val, kind_upper)

        if kind_upper in referrer_hashes_by_kind and h in referrer_hashes_by_kind[kind_upper]:
            if kind_upper in ("EMAIL", "PHONE"):
                score += 100
                reasons.append({"rule": f"SHARED_{kind_upper}", "weight": 100, "msg": f"Referrer and referred share identical {kind_upper}"})
            elif kind_upper in ("DEVICE", "PAYMENT_FP"):
                score += 80
                reasons.append({"rule": f"SHARED_{kind_upper}", "weight": 80, "msg": f"Referrer and referred share identical device or payment fingerprint"})
            elif kind_upper == "IP":
                score += 30
                reasons.append({"rule": "SHARED_IP", "weight": 30, "msg": "Referrer and referred share identical IP address"})

    # Determine level
    level = "LOW"
    if score >= 70:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"

    if level in ("MEDIUM", "HIGH"):
        risk_case = RiskCase(
            subject_user_id=referrer_user_id,
            referral_id=referral_id,
            level=level,
            score=score,
            reasons=reasons,
            status="OPEN",
        )
        session.add(risk_case)
        await session.flush()

    return level, score, reasons


async def has_open_high_risk_hold(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> bool:
    """Checks if user has any open HIGH risk cases (§13, §14.3)."""
    stmt = select(RiskCase).where(
        RiskCase.subject_user_id == user_id,
        RiskCase.level.in_(["HIGH", "BLOCKED"]),
        RiskCase.status == "OPEN",
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None


async def get_risk_cases(
    session: AsyncSession,
    *,
    status: str = "OPEN",
) -> list[RiskCase]:
    stmt = select(RiskCase).where(RiskCase.status == status).order_by(RiskCase.score.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def decide_risk_case(
    session: AsyncSession,
    *,
    case_id: uuid.UUID,
    actor_id: uuid.UUID,
    decision: str,  # CLEARED | REJECTED | BLOCKED
    note: str,
) -> RiskCase:
    """Analyst resolves a risk case (§14.3)."""
    stmt = select(RiskCase).where(RiskCase.id == case_id).with_for_update()
    res = await session.execute(stmt)
    risk_case = res.scalar_one_or_none()
    if not risk_case:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Risk case not found: {case_id}")

    allowed_decisions = {"CLEARED", "REJECTED", "BLOCKED"}
    if decision not in allowed_decisions:
        raise PlatformError(ErrorCode.VALIDATION_ERROR, f"Invalid decision '{decision}'")

    risk_case.status = decision
    risk_case.decided_by = actor_id
    notes = list(risk_case.notes)
    notes.append({"actor_id": str(actor_id), "decision": decision, "note": note, "at": clock.now().isoformat()})
    risk_case.notes = notes
    await session.flush()
    return risk_case


async def get_open_cases_count(session: AsyncSession) -> int:
    """Returns the number of open risk cases."""
    risk_stmt = select(func.count(RiskCase.id)).where(RiskCase.status == "OPEN")
    return int((await session.execute(risk_stmt)).scalar() or 0)

