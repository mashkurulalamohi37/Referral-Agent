"""CLI tool to create or update a Super Admin account.

Usage:
    python -m app.create_admin --email admin@pulsepos.com --password YourSecurePassword123!
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import delete, select

from app.core.config import Settings
from app.core.db import create_engine, create_session_factory
from app.identity.models import User, UserRole
from app.identity.service import hash_password


async def create_or_update_admin(
    email: str,
    password: str,
    display_name: str = "System Administrator",
) -> None:
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    clean_email = email.lower().strip()
    pw_hash = hash_password(password)

    async with session_factory() as session:
        # Check if user already exists
        stmt = select(User).where(User.email == clean_email)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        admin_roles = ["SUPER_ADMIN", "ADMIN", "PARTNER", "CUSTOMER"]

        if user:
            print(f"User with email '{clean_email}' already exists. Updating credentials and assigning admin roles...")
            user.password_hash = pw_hash
            user.display_name = display_name
            user.status = "ACTIVE"
            session.add(user)
            await session.flush()

            # Ensure roles are present
            role_stmt = select(UserRole.role).where(UserRole.user_id == user.id)
            existing_roles = set((await session.execute(role_stmt)).scalars().all())

            for role in admin_roles:
                if role not in existing_roles:
                    session.add(UserRole(user_id=user.id, role=role))
            await session.commit()
            print(f"Successfully updated user '{clean_email}' with SUPER_ADMIN privileges!")
        else:
            print(f"Creating new Super Admin user '{clean_email}'...")
            user = User(
                display_name=display_name,
                email=clean_email,
                email_verified=True,
                password_hash=pw_hash,
                status="ACTIVE",
                kyc_status="VERIFIED",
                agent_type="COMPANY",
                company_name="PulsePOS Core Engineering",
            )
            session.add(user)
            await session.flush()

            for role in admin_roles:
                session.add(UserRole(user_id=user.id, role=role))
            await session.commit()
            print(f"Successfully created Super Admin user '{clean_email}'!")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Create or update platform Super Admin")
    parser.add_argument("--email", default="admin@pulsepos.com", help="Admin email address")
    parser.add_argument("--password", default="Admin@PulsePOS2026!", help="Admin password")
    parser.add_argument("--name", default="System Administrator", help="Display name")
    args = parser.parse_args()

    asyncio.run(create_or_update_admin(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
