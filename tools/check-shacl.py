#!/usr/bin/env python3
"""Exercise the STONEWORK SHACL profile against conforming and failing fixtures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STONEWORK = "https://cyberterrain.org/ns/stonework#"
JAVA_COMMAND = [
    "java",
    "-cp",
    str(ROOT / "tools" / "rdf-toolkit.jar"),
    str(ROOT / "tools" / "ShaclValidator.java"),
]
BASELINE_SHAPES = ROOT / "ontologies" / "shapes" / "stonework-shapes.ttl"
STRICT_SHAPES = ROOT / "ontologies" / "shapes" / "stonework-strict-shapes.ttl"
FIXTURES = ROOT / "tests" / "fixtures"
FINANCIAL_EXAMPLE = ROOT / "examples" / "financial-follow-the-money.ttl"
SCHEMAS = [
    str(ROOT / "ontologies" / "stonework.ttl"),
    str(ROOT / "ontologies" / "categories.ttl"),
]


def validate(
    data: str | Path, shapes: Path = BASELINE_SHAPES
) -> subprocess.CompletedProcess[str]:
    data_path = data if isinstance(data, Path) else FIXTURES / data
    return subprocess.run(
        [
            *JAVA_COMMAND,
            str(shapes),
            *SCHEMAS,
            str(data_path),
        ],
        capture_output=True,
        text=True,
    )


def main() -> int:
    valid = validate("shacl-valid.ttl")
    if valid.returncode:
        print("Conforming SHACL fixture was rejected:", file=sys.stderr)
        print(valid.stderr or valid.stdout, file=sys.stderr)
        return 1

    external_relationship = validate("shacl-valid-external-relationship.ttl")
    if external_relationship.returncode:
        print(
            "Baseline profile rejected an external relationship without normalized provenance:",
            file=sys.stderr,
        )
        print(
            external_relationship.stderr or external_relationship.stdout,
            file=sys.stderr,
        )
        return 1

    valid_financial = validate("shacl-valid-financial.ttl")
    if valid_financial.returncode:
        print("Conforming financial SHACL fixture was rejected:", file=sys.stderr)
        print(valid_financial.stderr or valid_financial.stdout, file=sys.stderr)
        return 1

    financial_example = validate(FINANCIAL_EXAMPLE)
    if financial_example.returncode:
        print("Financial worked example failed baseline SHACL:", file=sys.stderr)
        print(financial_example.stderr or financial_example.stdout, file=sys.stderr)
        return 1

    invalid_fixtures = {
        "shacl-invalid.ttl": (),
        "shacl-invalid-ordering.ttl": (),
        "shacl-invalid-actuator.ttl": (),
        "shacl-invalid-actuation-target.ttl": (),
        "shacl-invalid-multiple-actuators.ttl": (),
        "shacl-invalid-functional-records.ttl": (
            "assertionObject",
            "assertionRelationType",
            "assertionSubject",
            "boundTo",
            "boundToLiteral",
            "fromStep",
            "guardLiteralValue",
            "guardOperator",
            "guardType",
            "guardVariable",
            "installationOf",
            "installedOn",
            "predictedLiteral",
            "predictedType",
            "predictedValue",
            "predictsVariable",
            "sightedObject",
            "toStep",
            "versionOf",
        ),
        "shacl-invalid-monetary-amount.ttl": (),
        "shacl-invalid-normalized-valuation.ttl": (),
        "shacl-invalid-currency-exchange.ttl": (),
    }
    for fixture, expected_paths in invalid_fixtures.items():
        invalid = validate(fixture)
        if invalid.returncode == 0:
            print(f"Non-conforming SHACL fixture was accepted: {fixture}", file=sys.stderr)
            return 1

        if "SHACL validation failed" not in invalid.stderr:
            print(f"Non-conforming fixture failed unexpectedly: {fixture}", file=sys.stderr)
            print(invalid.stderr or invalid.stdout, file=sys.stderr)
            return 1

        report = invalid.stderr or invalid.stdout
        for path in expected_paths:
            result_path = f"{STONEWORK}{path}>"
            if result_path not in report:
                print(
                    f"Non-conforming fixture did not violate the {path} shape: {fixture}",
                    file=sys.stderr,
                )
                print(report, file=sys.stderr)
                return 1

    strict_valid = validate("shacl-valid.ttl", STRICT_SHAPES)
    if strict_valid.returncode:
        print("Conforming fixture was rejected by the strict SHACL overlay:", file=sys.stderr)
        print(strict_valid.stderr or strict_valid.stdout, file=sys.stderr)
        return 1

    strict_financial = validate("shacl-valid-financial.ttl", STRICT_SHAPES)
    if strict_financial.returncode:
        print(
            "Conforming financial fixture was rejected by the strict SHACL overlay:",
            file=sys.stderr,
        )
        print(strict_financial.stderr or strict_financial.stdout, file=sys.stderr)
        return 1

    strict_financial_example = validate(FINANCIAL_EXAMPLE, STRICT_SHAPES)
    if strict_financial_example.returncode:
        print(
            "Financial worked example failed the strict provenance profile:",
            file=sys.stderr,
        )
        print(
            strict_financial_example.stderr or strict_financial_example.stdout,
            file=sys.stderr,
        )
        return 1

    strict_external_relationship = validate(
        "shacl-valid-external-relationship.ttl", STRICT_SHAPES
    )
    if strict_external_relationship.returncode == 0:
        print(
            "Strict SHACL overlay accepted a qualified assertion without provenance.",
            file=sys.stderr,
        )
        return 1

    if "SHACL validation failed" not in strict_external_relationship.stderr:
        print(
            "Strict SHACL overlay failed unexpectedly:",
            file=sys.stderr,
        )
        print(
            strict_external_relationship.stderr or strict_external_relationship.stdout,
            file=sys.stderr,
        )
        return 1

    print(
        "SHACL validation checks passed "
        "(baseline interoperability and strict provenance profiles verified)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
