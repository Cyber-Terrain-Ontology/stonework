#!/usr/bin/env bash
# Canonicalize Turtle files using rdf-toolkit, or verify them with --check.
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

CHECK_ONLY=false
if [ "${1:-}" = "--check" ]; then
    CHECK_ONLY=true
    shift
fi

if [ "$CHECK_ONLY" = true ] && [ "$#" -eq 0 ]; then
    TTL_FILES=()
    while IFS= read -r -d '' rel; do
        TTL_FILES+=("$REPO_ROOT/$rel")
    done < <(git -C "$REPO_ROOT" ls-files -z -- '*.ttl')
    set -- "${TTL_FILES[@]}"
fi

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 [--check] FILE.ttl [...]" >&2
    exit 2
fi

STATUS=0

for f in "$@"; do
    # Strip Protégé's default ':' prefix (duplicates a named prefix)
    if grep -qE '^@prefix[[:space:]]+:[[:space:]]+<[^>]+>[[:space:]]*\.$' "$f"; then
        if [ "$CHECK_ONLY" = true ]; then
            echo "format-ttl: $f contains Protégé's noncanonical default ':' prefix" >&2
            STATUS=1
            continue
        fi
        sed -i '/^@prefix[[:space:]]\+:[[:space:]]\+<[^>]*>[[:space:]]*\.$/d' "$f"
        echo "format-ttl: removed default ':' prefix from $f"
    fi

    # Canonicalize via rdf-toolkit (temp file avoids in-place read/write race)
    TMPFILE="$(mktemp)"
    java -jar "$JAR" -sfmt turtle -tfmt turtle --inline-blank-nodes -s "$f" -t "$TMPFILE"
    # rdf-toolkit emits an extra blank line at EOF. Keep one final newline so
    # canonicalization also remains clean under `git diff --check`.
    python3 - "$TMPFILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.write_text(path.read_text().rstrip() + "\n")
PY

    if [ "$CHECK_ONLY" = true ]; then
        if ! cmp -s "$f" "$TMPFILE"; then
            echo "format-ttl: $f is not canonically formatted" >&2
            STATUS=1
        fi
        rm -f "$TMPFILE"
    else
        mv "$TMPFILE" "$f"

        # Re-stage the reformatted file
        git add "$f"
    fi
done

if [ "$CHECK_ONLY" = true ] && [ "$STATUS" -ne 0 ]; then
    echo "Run .githooks/format-ttl.sh on the reported files and commit the result." >&2
fi

exit "$STATUS"
