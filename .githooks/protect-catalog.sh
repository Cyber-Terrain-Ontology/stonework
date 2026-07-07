#!/usr/bin/env bash
# Keep ontologies/catalog-v001.xml read-only so Protégé cannot overwrite it on save.
REPO_ROOT="$(git rev-parse --show-toplevel)"
CATALOG="$REPO_ROOT/ontologies/catalog-v001.xml"
if [ -f "$CATALOG" ]; then
    chmod 444 "$CATALOG"
    echo "protect-catalog: set $CATALOG read-only"
fi
