"""Unit and compliance tests for Product Tickets and Bug Desk (§21, ADR 0016)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.core import clock
from app.core.db import Base
from app.core.errors import ErrorCode, PlatformError
from app.events.models import OutboxMessage
from app.models import import_all_models
from app.tickets import service as tickets_service
from app.tickets.schemas import ProductTicketCreate

import_all_models()


@pytest.fixture
async def async_session() -> AsyncSession:
    """Provides an in-memory SQLite async database session with full schema tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_pulsepos_ticket_creation_and_sla(async_session: AsyncSession) -> None:
    # 1. Setup product
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS",
        signup_url="https://pulsepos.example.com/signup",
        sensitive_category=False,
    )

    # 2. Create CRITICAL ticket (2h SLA)
    ticket_in = ProductTicketCreate(
        title="Offline POS batch sync failed",
        category="SYNC_FAILURE",
        severity="CRITICAL",
        description="Transactions between 2pm and 4pm failed with 504 Gateway Timeout during sync.",
        external_user_id="merchant_gulshan_01",
        system_diagnostics={
            "terminal_id": "POS-TERM-99",
            "app_version": "v3.2.0",
            "os": "Android 13",
        },
    )
    ticket = await tickets_service.create_product_ticket(
        async_session,
        product_slug="pulsepos",
        data=ticket_in,
    )

    assert ticket.ticket_number.startswith("TKT-PULSEPOS-")
    assert ticket.severity == "CRITICAL"
    assert ticket.status == "NEW"
    assert ticket.product_id == product.id
    # SLA due should be roughly now + 2 hours
    diff = ticket.sla_due_at - clock.now()
    assert 1.9 <= diff.total_seconds() / 3600 <= 2.1

    # 3. Check outbox entry was staged in the same transaction
    outbox_stmt = select(OutboxMessage).where(
        OutboxMessage.aggregate_id == ticket.id,
        OutboxMessage.event_type == "ticket.created",
    )
    outbox_row = (await async_session.execute(outbox_stmt)).scalar_one_or_none()
    assert outbox_row is not None
    assert outbox_row.payload["ticket_number"] == ticket.ticket_number


@pytest.mark.asyncio
async def test_healora_privacy_violation_rejection(async_session: AsyncSession) -> None:
    # 1. Setup sensitive product (Healora)
    await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
        sensitive_category=True,  # sensitive medical/telemed product
    )

    # 2. Attempt ticket with clinical/PHI keyword in description
    ticket_in_bad = ProductTicketCreate(
        title="Telemedicine audio drop issue",
        category="CRASH",
        severity="HIGH",
        description="The audio dropped while discussing patient diagnosis with Dr. Faruq.",
    )

    with pytest.raises(PlatformError) as exc:
        await tickets_service.create_product_ticket(
            async_session,
            product_slug="healora",
            data=ticket_in_bad,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    assert "diagnosis" in str(exc.value.message).lower()


@pytest.mark.asyncio
async def test_healora_privacy_clean_ticket_accepted(async_session: AsyncSession) -> None:
    await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
        sensitive_category=True,
    )

    # Clean technical report with no clinical data
    ticket_in_clean = ProductTicketCreate(
        title="WebRTC video buffer overflow on low bandwidth",
        category="CRASH",
        severity="HIGH",
        description="Room connection disconnects after 45 minutes on 3G connections. Error code ICE_FAILED.",
        system_diagnostics={
            "browser": "Chrome 128",
            "webrtc_version": "m128",
        },
    )

    ticket = await tickets_service.create_product_ticket(
        async_session,
        product_slug="healora",
        data=ticket_in_clean,
    )
    assert ticket.ticket_number.startswith("TKT-HEALORA-")
    assert ticket.status == "NEW"


@pytest.mark.asyncio
async def test_ticket_conversation_and_internal_notes(async_session: AsyncSession) -> None:
    await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS",
        signup_url="https://pulsepos.example.com/signup",
    )
    ticket = await tickets_service.create_product_ticket(
        async_session,
        product_slug="pulsepos",
        data=ProductTicketCreate(
            title="Receipt printer disconnected",
            category="HARDWARE",
            severity="MEDIUM",
            description="USB thermal printer disconnected and won't reconnect without full restart.",
        ),
    )

    # 1. Add public reply
    await tickets_service.add_ticket_message(
        async_session,
        ticket_id=ticket.id,
        body="Have you verified the baud rate in Settings -> Hardware?",
        sender_type="SUPPORT_ENGINEER",
        sender_name="Karim (Support)",
        is_internal_note=False,
    )

    # 2. Add private internal dev note
    await tickets_service.add_ticket_message(
        async_session,
        ticket_id=ticket.id,
        body="Known issue in firmware v1.1.2; USB CDC driver resets on power spike.",
        sender_type="SUPPORT_ENGINEER",
        sender_name="Nafis (DevOps)",
        is_internal_note=True,
    )

    # 3. Client fetch (include_internal_notes=False) should only see public messages
    client_view = await tickets_service.get_ticket_by_id(
        async_session, ticket.id, include_internal_notes=False
    )
    assert client_view is not None
    assert len(client_view.messages) == 2  # initial description + public reply
    assert all(not m.is_internal_note for m in client_view.messages)

    # 4. Admin fetch (include_internal_notes=True) sees everything
    admin_view = await tickets_service.get_ticket_by_id(
        async_session, ticket.id, include_internal_notes=True
    )
    assert admin_view is not None
    assert len(admin_view.messages) == 3
    assert any(m.is_internal_note for m in admin_view.messages)


@pytest.mark.asyncio
async def test_ticket_triage_assignment_and_resolution(async_session: AsyncSession) -> None:
    await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS",
        signup_url="https://pulsepos.example.com/signup",
    )
    ticket = await tickets_service.create_product_ticket(
        async_session,
        product_slug="pulsepos",
        data=ProductTicketCreate(
            title="Payment gateway timeout",
            category="PAYMENT_FAILURE",
            severity="HIGH",
            description="bKash QR scanner times out after 30 seconds at checkout.",
        ),
    )
    assert ticket.status == "NEW"

    # 1. Assign agent -> transitions to TRIAGED
    agent_id = uuid.uuid4()
    ticket = await tickets_service.assign_ticket(
        async_session,
        ticket_id=ticket.id,
        agent_id=agent_id,
    )
    assert ticket.status == "TRIAGED"
    assert ticket.assigned_agent_id == agent_id

    # 2. Move to INVESTIGATING
    ticket = await tickets_service.update_ticket_status(
        async_session,
        ticket_id=ticket.id,
        new_status="INVESTIGATING",
    )
    assert ticket.status == "INVESTIGATING"

    # 3. Resolve with hotfix summary
    ticket = await tickets_service.update_ticket_status(
        async_session,
        ticket_id=ticket.id,
        new_status="RESOLVED",
        resolution_summary="bKash sandbox webhook latency fixed by increasing read timeout to 60s in v3.2.1.",
    )
    assert ticket.status == "RESOLVED"
    assert ticket.resolved_at is not None
    assert "timeout to 60s" in ticket.resolution_summary


@pytest.mark.asyncio
async def test_portal_user_tickets_lifecycle(async_session: AsyncSession) -> None:
    # 1. Setup product
    await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS",
        signup_url="https://pulsepos.example.com/signup",
    )

    portal_user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    # 2. Portal user submits a ticket
    ticket = await tickets_service.create_product_ticket(
        async_session,
        product_slug="pulsepos",
        data=ProductTicketCreate(
            title="Unable to download monthly report",
            category="REPORTING",
            severity="MEDIUM",
            description="The PDF report generator is stuck on loading.",
            external_user_id=f"user_{portal_user_id}",
        ),
        actor_id=portal_user_id,
    )
    assert ticket.ticket_number.startswith("TKT-PULSEPOS-")

    # 3. List tickets for portal user
    my_tickets = await tickets_service.list_tickets_for_user(async_session, user_id=portal_user_id)
    assert len(my_tickets) == 1
    assert my_tickets[0].id == ticket.id

    other_tickets = await tickets_service.list_tickets_for_user(async_session, user_id=other_user_id)
    assert len(other_tickets) == 0

    # 4. Portal user adds message
    msg = await tickets_service.add_ticket_message(
        async_session,
        ticket_id=ticket.id,
        body="It happened again today at 11 AM.",
        sender_type="PARTNER_PORTAL_USER",
        sender_user_id=portal_user_id,
        sender_name="Demo Partner",
    )
    assert msg.body == "It happened again today at 11 AM."

