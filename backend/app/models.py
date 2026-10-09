"""Imports every module's ORM models so Alembic and tests see the full metadata."""

from __future__ import annotations

import importlib
import pkgutil

DOMAIN_MODULES = (
    "identity",
    "catalog",
    "referrals",
    "events",
    "subscriptions",
    "commissions",
    "ledger",
    "credits",
    "payouts",
    "campaigns",
    "partners",
    "risk",
    "notifications",
    "reporting",
    "admin",
)


def import_all_models() -> None:
    for module in DOMAIN_MODULES:
        package = importlib.import_module(f"app.{module}")
        names = {m.name for m in pkgutil.iter_modules(package.__path__)}
        if "models" in names:
            importlib.import_module(f"app.{module}.models")


__all__ = ["DOMAIN_MODULES", "import_all_models"]
