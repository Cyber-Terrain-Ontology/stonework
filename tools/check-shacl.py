#!/usr/bin/env python3
"""Exercise the STONEWORK SHACL validation profiles against fixture data.

STONEWORK's shape graphs are a *validation profile*, not the interoperability
contract. The contract is the ontology; shapes describe what a well-formed
record looks like for a given consumer. This harness therefore composes shape
graphs into named profiles and gates only on ``sh:Violation`` results --
``sh:Warning`` results are reported but do not fail the build.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JENA_HOME = ROOT / "tools" / "apache-jena-6.2.0"
SHACL = JENA_HOME / "bin" / "shacl"
RIOT = JENA_HOME / "bin" / "riot"
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

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
SHACL_NS = "http://www.w3.org/ns/shacl#"
VALIDATION_RESULT = f"{SHACL_NS}ValidationResult"
RESULT_SEVERITY = f"{SHACL_NS}resultSeverity"
RESULT_MESSAGE = f"{SHACL_NS}resultMessage"
FOCUS_NODE = f"{SHACL_NS}focusNode"

VIOLATION = "Violation"
WARNING = "Warning"

# Jena's shacl command always exits 0 when it can produce a report, including
# non-conforming data. Non-zero means the engine itself failed.
_NT_TRIPLE = re.compile(r"^(\S+)\s+(\S+)\s+(.*)\s+\.\s*$")


@dataclass
class Finding:
    severity: str
    message: str
    focus: str

    def __str__(self) -> str:
        return f"    [{self.severity}] {self.focus}\n      {self.message}"


class ValidatorError(RuntimeError):
    """The engine could not produce a report (bad shapes, bad data, crash)."""


def _jena_env() -> dict[str, str]:
    env = os.environ.copy()
    env["JENA_HOME"] = str(JENA_HOME)
    return env


def _unquote_iri(term: str) -> str:
    return term[1:-1] if term.startswith("<") and term.endswith(">") else term


def _literal_text(term: str) -> str:
    """Pull the lexical form out of an N-Triples literal."""
    if not term.startswith('"'):
        return term
    out: list[str] = []
    i = 1
    while i < len(term):
        ch = term[i]
        if ch == "\\":
            if i + 1 >= len(term):
                break
            nxt = term[i + 1]
            escapes = {"t": "\t", "n": "\n", "r": "\r", '"': '"', "\\": "\\"}
            out.append(escapes.get(nxt, nxt))
            i += 2
            continue
        if ch == '"':
            break
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_ntriples(report: str) -> list[Finding]:
    """Collect sh:ValidationResult rows from a Jena N-Triples report."""
    triples: dict[str, dict[str, list[str]]] = {}
    for raw in report.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _NT_TRIPLE.match(line)
        if match is None:
            raise ValidatorError(f"unreadable N-Triples line: {line}")
        subject, predicate, obj = (
            _unquote_iri(match.group(1)),
            _unquote_iri(match.group(2)),
            match.group(3),
        )
        triples.setdefault(subject, {}).setdefault(predicate, []).append(obj)

    findings: list[Finding] = []
    for props in triples.values():
        types = [_unquote_iri(value) for value in props.get(RDF_TYPE, [])]
        if VALIDATION_RESULT not in types:
            continue
        severity_raw = props.get(RESULT_SEVERITY, [""])[0]
        messages = props.get(RESULT_MESSAGE, [])
        focus_raw = props.get(FOCUS_NODE, ["?"])[0]
        findings.append(
            Finding(
                severity=_unquote_iri(severity_raw).rsplit("#", 1)[-1],
                message=_literal_text(messages[-1]) if messages else "(no message)",
                focus=_unquote_iri(focus_raw),
            )
        )
    return findings


def validate(data: Path, profile: str) -> list[Finding]:
    shapes = PROFILES[profile]
    with tempfile.NamedTemporaryFile(
        "w", suffix=".ttl", delete=False, encoding="utf-8"
    ) as union:
        # Profiles are composed by concatenating Turtle. Repeating @prefix
        # directives is valid, and a single --shapes argument keeps the
        # union graph explicit in the report's sourceShape.
        for shape_file in shapes:
            union.write(shape_file.read_text(encoding="utf-8"))
            union.write("\n")
        union_path = Path(union.name)

    try:
        env = _jena_env()
        command = [
            str(SHACL),
            "validate",
            "--shapes",
            str(union_path),
        ]
        for schema in SCHEMAS:
            command.extend(["--data", str(schema)])
        command.extend(["--data", str(data)])
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
        )
        if proc.returncode != 0:
            raise ValidatorError(
                f"{data.name} under profile '{profile}': engine failed "
                f"(exit {proc.returncode})\n{proc.stderr.strip() or proc.stdout.strip()}"
            )
        riot = subprocess.run(
            [str(RIOT), "--syntax=ttl", "--output=ntriples"],
            input=proc.stdout,
            capture_output=True,
            text=True,
            env=env,
        )
        if riot.returncode != 0:
            raise ValidatorError(
                f"{data.name} under profile '{profile}': riot could not "
                f"canonicalize the report\n{riot.stderr.strip()}"
            )
        return _parse_ntriples(riot.stdout)
    finally:
        union_path.unlink(missing_ok=True)


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
    if SHACL.is_file() and RIOT.is_file():
        return 0
    print(
        f"Apache Jena not found at {JENA_HOME.relative_to(ROOT)}.\n"
        "Run once to download it: bash tools/download-jena.sh",
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
