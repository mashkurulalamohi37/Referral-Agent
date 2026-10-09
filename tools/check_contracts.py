"""Validate the Phase 0 contract documents.

- Every event JSON Schema is a valid Draft 2020-12 schema.
- Every example under docs/events/examples/valid validates against the envelope.
- Every example under docs/events/examples/invalid is rejected.
- docs/openapi.yaml is a valid OpenAPI 3.1 document.

Usage: python tools/check_contracts.py   (from the repo root)
Requires: jsonschema, referencing, openapi-spec-validator, pyyaml, rfc3339-validator
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate as validate_openapi
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "docs" / "events"


def load_registry() -> tuple[Registry, dict[str, dict]]:
    schemas: dict[str, dict] = {}
    for path in EVENTS.rglob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schemas[schema["$id"]] = schema
    registry = Registry().with_resources(
        (sid, Resource.from_contents(s)) for sid, s in schemas.items()
    )
    return registry, schemas


def main() -> int:
    failures: list[str] = []
    registry, schemas = load_registry()
    envelope = next(s for s in schemas.values() if s["$id"].endswith("/envelope.schema.json"))
    validator = Draft202012Validator(envelope, registry=registry, format_checker=FormatChecker())

    for path in sorted((EVENTS / "examples" / "valid").glob("*.json")):
        errors = list(validator.iter_errors(json.loads(path.read_text(encoding="utf-8"))))
        if errors:
            failures.append(f"valid example rejected: {path.name}: {errors[0].message}")
    for path in sorted((EVENTS / "examples" / "invalid").glob("*.json")):
        if validator.is_valid(json.loads(path.read_text(encoding="utf-8"))):
            failures.append(f"invalid example accepted: {path.name}")

    spec = yaml.safe_load((ROOT / "docs" / "openapi.yaml").read_text(encoding="utf-8"))
    try:
        validate_openapi(spec, base_uri=(ROOT / "docs" / "openapi.yaml").as_uri())
    except Exception as exc:  # report, don't crash, so all failures are listed
        failures.append(f"openapi.yaml invalid: {exc}")

    for line in failures:
        print("FAIL", line)
    print(f"{len(schemas)} schemas checked, {'FAILED' if failures else 'OK'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
