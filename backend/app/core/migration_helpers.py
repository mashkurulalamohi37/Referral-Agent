"""Helpers used by Alembic migrations.

Insert-only tables (I2, ADR 0006) get `forbid_mutation` triggers that reject UPDATE, DELETE and
TRUNCATE. The application connects as a non-owner role, so it cannot disable the triggers.
"""

from __future__ import annotations

from typing import Final

FORBID_MUTATION_FUNCTION_SQL: Final = """
CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'table % is insert-only (attempted %)', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$;
"""

DROP_FORBID_MUTATION_FUNCTION_SQL: Final = "DROP FUNCTION IF EXISTS forbid_mutation();"

INSERT_ONLY_TRIGGER_PREFIX: Final = "trg_insert_only_"


def _quote_ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        msg = f"unsafe identifier {name!r}"
        raise ValueError(msg)
    return f'"{name}"'


def insert_only_sql(table: str) -> list[str]:
    """Statements that make `table` insert-only."""
    t = _quote_ident(table)
    row_trigger = _quote_ident(f"{INSERT_ONLY_TRIGGER_PREFIX}{table}")
    stmt_trigger = _quote_ident(f"{INSERT_ONLY_TRIGGER_PREFIX}{table}_truncate")
    return [
        f"CREATE TRIGGER {row_trigger} BEFORE UPDATE OR DELETE ON {t} "
        "FOR EACH ROW EXECUTE FUNCTION forbid_mutation();",
        f"CREATE TRIGGER {stmt_trigger} BEFORE TRUNCATE ON {t} "
        "FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();",
    ]


def drop_insert_only_sql(table: str) -> list[str]:
    t = _quote_ident(table)
    return [
        f"DROP TRIGGER IF EXISTS {_quote_ident(INSERT_ONLY_TRIGGER_PREFIX + table)} ON {t};",
        f"DROP TRIGGER IF EXISTS {_quote_ident(INSERT_ONLY_TRIGGER_PREFIX + table + '_truncate')} "
        f"ON {t};",
    ]


# Tables that must be insert-only (ADR 0006). Phase migrations add them; a test checks that
# every table listed here that exists in the database carries both triggers.
INSERT_ONLY_TABLES: Final = (
    "ledger_entries",
    "journal_transactions",
    "audit_logs",
    "inbound_events",
    "event_processing_log",
    "commission_reversals",
    "commission_state_transitions",
    "risk_signals",
)
