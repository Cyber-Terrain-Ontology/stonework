#!/usr/bin/env bash
# Build the single-file merge of the STONEWORK core and its categories module.
#
# The repo keeps the vocabulary split for modularity:
#   ontologies/stonework.ttl   - core classes and properties
#   ontologies/categories.ttl  - Category/Role subclasses, SKOS concept schemes,
#                                and ~230 controlled-vocabulary individuals
#                                (malware types, currencies, markings, ...)
#
# But a client that dereferences the namespace IRI expects every stonework:
# term in one document. This script produces that document — it is what gets
# published as cyberterrain.org/ns/stonework.ttl (deployed from the separate
# cyberterrain-website repo). The WIDOCO documentation at /ns/stonework/doc/ is
# also generated from this merged file so it covers the vocabulary individuals.
#
# Usage:
#   bash tools/build-merged.sh [OUTPUT]
# OUTPUT defaults to build/stonework-merged.ttl (gitignored).
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
CORE="$REPO_ROOT/ontologies/stonework.ttl"
CATEGORIES="$REPO_ROOT/ontologies/categories.ttl"
JAR="$REPO_ROOT/tools/rdf-toolkit.jar"
OUT="${1:-$REPO_ROOT/build/stonework-merged.ttl}"

CORE_IRI="https://cyberterrain.org/ns/stonework#"

if [ ! -f "$JAR" ]; then
    echo "ERROR: rdf-toolkit.jar not found at $JAR" >&2
    echo "Run once: bash tools/download-rdf-toolkit.sh" >&2
    exit 1
fi

mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp)"
trap 'rm -f "$TMP" "$TMP.canon"' EXIT

# 1. Core, verbatim (keeps its @prefix block — a superset of the categories one —
#    and its single owl:Ontology header at the core IRI).
cat "$CORE" > "$TMP"

# 2. Categories body only: everything from its first "stonework:" subject to EOF.
#    Drops the leading "# imports:" comment, the duplicate @prefix lines, and the
#    <.../ns/stonework/categories#> a owl:Ontology ... . block. No line-count
#    assumption — the first line beginning "stonework:" marks the body start.
if ! grep -q '^stonework:' "$CATEGORIES"; then
    echo "ERROR: no 'stonework:' subject found in $CATEGORIES; header-strip heuristic is broken" >&2
    exit 1
fi
sed -n '/^stonework:/,$p' "$CATEGORIES" >> "$TMP"

# 3. Canonicalize the concatenation (sorts every subject into one ordering,
#    reconciles prefixes, normalizes formatting). rdf-toolkit fails non-zero on
#    a parse error, which would mean the two files disagree about some subject.
java -jar "$JAR" -sfmt turtle -tfmt turtle --inline-blank-nodes -s "$TMP" -t "$TMP.canon"
python3 - "$TMP.canon" "$OUT" <<'PY'
import sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.write_text(src.read_text(encoding="utf-8").rstrip() + "\n", encoding="utf-8")
PY

# 4. Sanity checks — fail loudly rather than publish a broken merge.
errors=0
check() { if ! eval "$2"; then echo "  FAIL: $1" >&2; errors=$((errors + 1)); fi; }

ont_headers="$(grep -c '^	a owl:Ontology' "$OUT" || true)"
check "exactly one owl:Ontology header (found $ont_headers)" "[ \"$ont_headers\" -eq 1 ]"
check "ontology IRI is <$CORE_IRI>" "grep -qxF '<$CORE_IRI>' \"$OUT\""
check "no residual categories ontology declaration" "! grep -q 'ns/stonework/categories#>' \"$OUT\""
check "owl:versionInfo present" "grep -q 'owl:versionInfo' \"$OUT\""
check "core term present (stonework:FinancialAccount)" "grep -q '^stonework:FinancialAccount' \"$OUT\""
check "categories term present (stonework:Ransomware)" "grep -q '^stonework:Ransomware' \"$OUT\""

if [ "$errors" -ne 0 ]; then
    echo "build-merged: $errors check(s) failed; $OUT NOT trustworthy" >&2
    exit 1
fi

version="$(grep -oE 'owl:versionInfo "[^"]+"' "$OUT" | head -1 | sed 's/.*"\(.*\)"/\1/')"
subjects="$(grep -cE '^stonework:\S+ ?$|^stonework:\S+$' "$OUT" || true)"
echo "build-merged: wrote $OUT"
echo "  version $version | $subjects stonework: subjects | $(wc -l < "$OUT") lines"
