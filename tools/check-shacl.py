#!/usr/bin/env python3
"""Exercise the STONEWORK SHACL validation profiles against fixture data.

STONEWORK's shape graphs are a *validation profile*, not the interoperability
contract. The contract is the ontology; shapes describe what a well-formed
record looks like for a given consumer. This harness therefore composes shape
graphs into named profiles and gates only on ``sh:Violation`` results --
``sh:Warning`` results are reported but do not fail the build.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "bin" / "shacl-validator"
SHAPES_DIR = ROOT / "ontologies" / "shapes"
FIXTURES = ROOT / "tests" / "fixtures"

CORE_SHAPES = SHAPES_DIR / "stonework-shapes.ttl"
FINANCIAL_SHAPES = SHAPES_DIR / "frameworks" / "financial-shapes.ttl"
STRICT_SHAPES = SHAPES_DIR / "stonework-strict-shapes.ttl"
FINANCIAL_EXAMPLE = ROOT / "examples" / "financial-follow-the-money.ttl"

# The ontology schemas are loaded as data so that sh:targetClass resolves
# through rdfs:subClassOf.
SCHEMAS = [ROOT / "ontologies" / "stonework.ttl", ROOT / "ontologies" / "categories.ttl"]

# Named profiles. Adapter-specific shape graphs are opt-in: a consumer that
# does not ingest financial records never loads the financial contract.
PROFILES: dict[str, list[Path]] = {
    "core": [CORE_SHAPES],
    "financial": [CORE_SHAPES, FINANCIAL_SHAPES],
    "strict": [CORE_SHAPES, STRICT_SHAPES],
    "financial-strict": [CORE_SHAPES, FINANCIAL_SHAPES, STRICT_SHAPES],
}

VIOLATION = "Violation"
WARNING = "Warning"


@dataclass
class Finding:
    severity: str
    message: str
    focus: str

    def __str__(self) -> str:
        return f"    [{self.severity}] {self.focus}\n      {self.message}"


class ValidatorError(RuntimeError):
    """The engine could not produce a report (bad shapes, bad data, crash)."""


def _severity(raw: str) -> str:
    """``<http://www.w3.org/ns/shacl#Warning>`` -> ``Warning``."""
    return raw.rstrip(">").rsplit("#", 1)[-1]


def _flatten(results: list[dict]) -> list[Finding]:
    findings = []
    for result in results:
        messages = result.get("messages") or ["(no message)"]
        findings.append(
            Finding(
                severity=_severity(result.get("severity", "")),
                # The engine's generic message comes first and any authored
                # sh:message last, so the last entry is the most specific.
                message=messages[-1],
                focus=result.get("focusNode", "?").strip("<>"),
            )
        )
    return findings


def validate(data: Path, profile: str) -> list[Finding]:
    shapes = PROFILES[profile]
    with tempfile.NamedTemporaryFile(
        "w", suffix=".ttl", delete=False, encoding="utf-8"
    ) as union:
        # The engine accepts a single shapes graph, so profiles are composed by
        # concatenation. Repeating @prefix directives is valid Turtle.
        for shape_file in shapes:
            union.write(shape_file.read_text(encoding="utf-8"))
            union.write("\n")
        union_path = Path(union.name)

    try:
        proc = subprocess.run(
            [
                str(VALIDATOR),
                "validate",
                str(union_path),
                *(str(schema) for schema in SCHEMAS),
                str(data),
                "--output-format",
                "json",
                "--diagnostics",
                "none",
            ],
            capture_output=True,
            text=True,
        )
    finally:
        union_path.unlink(missing_ok=True)

    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValidatorError(
            f"{data.name} under profile '{profile}': engine produced no report "
            f"(exit {proc.returncode})\n{proc.stderr.strip()}"
        ) from exc

    return _flatten(report.get("results", []))


def _report(label: str, findings: list[Finding]) -> None:
    for finding in findings:
        print(f"  {label}", file=sys.stderr)
        print(finding, file=sys.stderr)


def _advise(fixture: str, profile: str, warnings: list[Finding]) -> None:
    """Surface advisory findings without gating on them."""
    if not warnings:
        return
    print(f"  advisory ({profile}, {fixture}):")
    for warning in warnings:
        print(f"    {warning.message}")


def check_engine() -> int:
    if VALIDATOR.exists():
        return 0
    print(
        f"SHACL engine not found at {VALIDATOR.relative_to(ROOT)}.\n"
        "Run once to build it: bash tools/install-shacl-validator.sh",
        file=sys.stderr,
    )
    return 1


def check_no_closed_shapes() -> int:
    """STONEWORK never ships sh:closed.

    A closed shape rejects any predicate the shape author did not enumerate,
    which turns every downstream extension into a validation failure. Shapes
    constrain the properties they care about and ignore the rest.
    """
    needles = ("sh:closed", "<http://www.w3.org/ns/shacl#closed>")
    offenders = [
        path.relative_to(ROOT)
        for path in sorted(SHAPES_DIR.rglob("*.ttl"))
        if any(needle in path.read_text(encoding="utf-8") for needle in needles)
    ]
    if not offenders:
        return 0
    print("Shipped shape graphs must not use sh:closed:", file=sys.stderr)
    for path in offenders:
        print(f"  {path}", file=sys.stderr)
    print(
        "  Closing a shape rejects unknown predicates and breaks every "
        "downstream extension. Constrain the properties you care about and "
        "ignore the rest.",
        file=sys.stderr,
    )
    return 1


def expect_clean(fixture: str, profile: str, why: str) -> int:
    """Fixture must produce no violations under this profile.

    Warnings are surfaced but do not gate, consistent with the severity
    contract: a conforming record may still be incomplete.
    """
    findings = validate(_path(fixture), profile)
    violations = [f for f in findings if f.severity == VIOLATION]
    _advise(fixture, profile, [f for f in findings if f.severity == WARNING])
    if not violations:
        return 0
    print(f"{why} (profile '{profile}', {fixture}):", file=sys.stderr)
    _report("unexpected violation:", violations)
    return 1


def expect_violation(fixture: str, profile: str, why: str) -> int:
    findings = validate(_path(fixture), profile)
    if any(f.severity == VIOLATION for f in findings):
        return 0
    print(f"{why} (profile '{profile}', {fixture}):", file=sys.stderr)
    print("  expected at least one sh:Violation, got:", file=sys.stderr)
    if findings:
        _report("", findings)
    else:
        print("    (nothing)", file=sys.stderr)
    return 1


def expect_warning(fixture: str, profile: str, why: str) -> int:
    """Fixture is incomplete, not malformed: warnings only, no violations."""
    findings = validate(_path(fixture), profile)
    violations = [f for f in findings if f.severity == VIOLATION]
    warnings = [f for f in findings if f.severity == WARNING]
    if warnings and not violations:
        _advise(fixture, profile, warnings)
        return 0
    print(f"{why} (profile '{profile}', {fixture}):", file=sys.stderr)
    if violations:
        print("  expected warnings only, but got violations:", file=sys.stderr)
        _report("", violations)
    else:
        print("  expected at least one sh:Warning, got nothing", file=sys.stderr)
    return 1


def _path(fixture: str) -> Path:
    candidate = FIXTURES / fixture
    return candidate if candidate.exists() else ROOT / fixture


def main() -> int:
    if check_engine():
        return 1

    failures = check_no_closed_shapes()

    try:
        # Conforming records must raise no violations under the profile that
        # governs them.
        failures += expect_clean(
            "shacl-valid.ttl", "core", "Conforming fixture was rejected"
        )
        failures += expect_clean(
            "shacl-valid-external-relationship.ttl",
            "core",
            "Core profile rejected an external relationship without normalized provenance",
        )
        failures += expect_clean(
            "shacl-valid-financial.ttl",
            "financial",
            "Conforming financial fixture was rejected",
        )
        failures += expect_clean(
            str(FINANCIAL_EXAMPLE.relative_to(ROOT)),
            "financial",
            "Financial worked example failed the financial profile",
        )

        # Malformed records: the value is wrong, not merely absent.
        for fixture in (
            "shacl-invalid.ttl",
            "shacl-invalid-ordering.ttl",
            "shacl-invalid-actuator.ttl",
            "shacl-invalid-multiple-actuators.ttl",
            "shacl-invalid-monetary-amount.ttl",
        ):
            failures += expect_violation(
                fixture, "core", "Malformed fixture was accepted"
            )
        failures += expect_violation(
            "shacl-invalid-normalized-valuation.ttl",
            "financial",
            "Malformed fixture was accepted",
        )

        # Incomplete records: advisory, so they must not gate the build.
        failures += expect_warning(
            "shacl-warning-actuation-target.ttl",
            "core",
            "An actuation with no resolved target should warn, not fail",
        )
        failures += expect_warning(
            "shacl-warning-currency-exchange.ttl",
            "financial",
            "A partially mapped currency exchange should warn, not fail",
        )

        # The strict overlay is additive: it is unioned with the core profile
        # rather than replacing it.
        failures += expect_clean(
            "shacl-valid.ttl",
            "strict",
            "Conforming fixture was rejected by the strict profile",
        )
        failures += expect_clean(
            "shacl-valid-financial.ttl",
            "financial-strict",
            "Conforming financial fixture was rejected by the strict profile",
        )
        failures += expect_clean(
            str(FINANCIAL_EXAMPLE.relative_to(ROOT)),
            "financial-strict",
            "Financial worked example failed the strict provenance profile",
        )
        failures += expect_violation(
            "shacl-valid-external-relationship.ttl",
            "strict",
            "Strict profile accepted a qualified assertion without provenance",
        )
    except ValidatorError as exc:
        print(f"SHACL engine error: {exc}", file=sys.stderr)
        return 1

    if failures:
        print(f"\n{failures} SHACL profile check(s) failed.", file=sys.stderr)
        return 1

    print(
        f"SHACL validation checks passed ({len(PROFILES)} profiles: "
        f"{', '.join(PROFILES)}; violations gate, warnings advise)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
