#!/usr/bin/env python3
"""Exercise the STONEWORK SHACL profile against conforming and failing fixtures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JAVA_COMMAND = [
    "java",
    "-cp",
    str(ROOT / "tools" / "rdf-toolkit.jar"),
    str(ROOT / "tools" / "ShaclValidator.java"),
    str(ROOT / "ontologies" / "shapes" / "stonework-shapes.ttl"),
    str(ROOT / "ontologies" / "stonework.ttl"),
    str(ROOT / "ontologies" / "categories.ttl"),
]


def validate(fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*JAVA_COMMAND, str(ROOT / "tests" / "fixtures" / fixture)],
        capture_output=True,
        text=True,
    )


def main() -> int:
    valid = validate("shacl-valid.ttl")
    if valid.returncode:
        print("Conforming SHACL fixture was rejected:", file=sys.stderr)
        print(valid.stderr or valid.stdout, file=sys.stderr)
        return 1

    invalid_fixtures = ("shacl-invalid.ttl", "shacl-invalid-ordering.ttl")
    for fixture in invalid_fixtures:
        invalid = validate(fixture)
        if invalid.returncode == 0:
            print(f"Non-conforming SHACL fixture was accepted: {fixture}", file=sys.stderr)
            return 1

        if "SHACL validation failed" not in invalid.stderr:
            print(f"Non-conforming fixture failed unexpectedly: {fixture}", file=sys.stderr)
            print(invalid.stderr or invalid.stdout, file=sys.stderr)
            return 1

    print("SHACL validation checks passed (valid fixture accepted; invalid fixtures rejected).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
