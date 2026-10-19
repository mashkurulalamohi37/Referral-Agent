"""Privacy filters and health data protection (§15, ADR 0016)."""

from __future__ import annotations

import re
from typing import Any

from app.core.errors import ErrorCode, PlatformError

# Forbidden health/clinical keywords to prevent accidental PHI ingestion
FORBIDDEN_HEALTH_TERMS = {
    "diagnosis",
    "prescription",
    "icd-10",
    "icd10",
    "rx",
    "symptom",
    "symptoms",
    "treatment",
    "vital_sign",
    "lab_result",
    "clinical_note",
    "doctor_note",
    "patient_name",
    "patient_history",
    "medication",
    "dosage",
}

_HEALTH_REGEX = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in FORBIDDEN_HEALTH_TERMS) + r")\b",
    re.IGNORECASE,
)


def validate_product_ticket_privacy(
    *,
    is_sensitive_product: bool,
    title: str,
    description: str,
    diagnostics: dict[str, Any] | None = None,
) -> None:
    """Enforces zero-health-data invariant on sensitive products like Healora (§15)."""
    if not is_sensitive_product:
        return

    text_to_check = f"{title} {description}"
    if diagnostics:
        for k, v in diagnostics.items():
            text_to_check += f" {k}"
            if isinstance(v, str):
                text_to_check += f" {v}"

    match = _HEALTH_REGEX.search(text_to_check)
    if match:
        raise PlatformError(
            ErrorCode.VALIDATION_ERROR,
            f"Sensitive clinical term '{match.group(0)}' detected. Tickets for sensitive products must strictly omit clinical and PHI data (ADR 0016).",
        )
