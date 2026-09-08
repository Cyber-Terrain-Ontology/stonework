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
SCHEMAS = [
    str(ROOT / "ontologies" / "stonework.ttl"),
    str(ROOT / "ontologies" / "categories.ttl"),
]


def validate(
    fixture: str, shapes: Path = BASELINE_SHAPES
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            *JAVA_COMMAND,
            str(shapes),
            *SCHEMAS,
            str(ROOT / "tests" / "fixtures" / fixture),
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
