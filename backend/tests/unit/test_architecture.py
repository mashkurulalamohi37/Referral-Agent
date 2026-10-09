"""Static architecture rules (§3 module boundaries, ADR 0003 no-float money)."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.models import DOMAIN_MODULES

APP = Path(__file__).resolve().parents[2] / "app"

# Modules whose code is a money path (§0.3). Phase 1 only has core/money.py; the domain
# modules are scanned as they gain code.
MONEY_PATHS = ("core/money.py", "commissions", "ledger", "credits", "payouts")


def _python_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    yield from sorted(root.rglob("*.py"))


def _imports(path: Path) -> Iterator[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.lineno, node.module
            for alias in node.names:
                yield node.lineno, f"{node.module}.{alias.name}"


def test_modules_only_import_each_others_service() -> None:
    violations: list[str] = []
    for module in DOMAIN_MODULES:
        for path in _python_files(APP / module):
            for lineno, name in _imports(path):
                parts = name.split(".")
                if len(parts) < 3 or parts[0] != "app" or parts[1] not in DOMAIN_MODULES:
                    continue
                other, sub = parts[1], parts[2]
                if other != module and sub != "service":
                    violations.append(f"{path.relative_to(APP)}:{lineno} imports {name}")
    assert not violations, "cross-module imports must go through service.py:\n" + "\n".join(violations)


def test_core_does_not_import_domain_modules() -> None:
    violations = [
        f"{path.relative_to(APP)}:{lineno} imports {name}"
        for path in _python_files(APP / "core")
        for lineno, name in _imports(path)
        if name.split(".")[:2][-1] in DOMAIN_MODULES and name.startswith("app.")
    ]
    assert not violations


def _float_uses(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            yield f"{path.relative_to(APP)}:{node.lineno} float literal {node.value!r}"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
            yield f"{path.relative_to(APP)}:{node.lineno} float() call"
        elif isinstance(node, ast.Name) and node.id == "float" and isinstance(node.ctx, ast.Load):
            yield f"{path.relative_to(APP)}:{getattr(node, 'lineno', 0)} float type"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            # True division produces floats on ints; money code must use Decimal or //.
            yield f"{path.relative_to(APP)}:{node.lineno} '/' division (use Decimal or mul_div_round)"


@pytest.mark.parametrize("target", MONEY_PATHS)
def test_no_float_in_money_paths(target: str) -> None:
    findings = [hit for path in _python_files(APP / target) for hit in _float_uses(path)]
    assert not findings, "\n".join(findings)
