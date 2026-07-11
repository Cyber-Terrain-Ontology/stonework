#!/usr/bin/env bash
# Canonicalize staged Turtle files using rdf-toolkit.
# Also strips Protégé's injected default ':' prefix when present.
# Called by pre-commit for every staged *.ttl file.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
JAR="$REPO_ROOT/tools/rdf-toolkit.jar"

if [ ! -f "$JAR" ]; then
    echo "ERROR: rdf-toolkit.jar not found at $JAR"
    echo "Run once to download: bash tools/download-rdf-toolkit.sh"
    exit 1
fi

for f in "$@"; do
    # Strip Protégé's default ':' prefix (duplicates a named prefix)
    if grep -qE '^@prefix[[:space:]]+:[[:space:]]+<[^>]+>[[:space:]]*\.$' "$f"; then
        sed -i '/^@prefix[[:space:]]\+:[[:space:]]\+<[^>]*>[[:space:]]*\.$/d' "$f"
        echo "format-ttl: removed default ':' prefix from $f"
    fi

    # Canonicalize via rdf-toolkit (temp file avoids in-place read/write race)
    TMPFILE="$(mktemp)"
    java -jar "$JAR" -sfmt turtle -tfmt turtle --inline-blank-nodes -s "$f" -t "$TMPFILE"
    mv "$TMPFILE" "$f"

    # Re-stage the reformatted file
    git add "$f"
done
