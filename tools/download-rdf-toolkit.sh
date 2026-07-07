#!/usr/bin/env bash
# Download the rdf-toolkit.jar used by the pre-commit TTL formatting hook.
# Run this once after cloning: bash tools/download-rdf-toolkit.sh
set -euo pipefail

RDF_TOOLKIT_VERSION="2.0"
JAR_URL="https://github.com/edmcouncil/rdf-toolkit/releases/download/v${RDF_TOOLKIT_VERSION}/rdf-toolkit.jar"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="$SCRIPT_DIR/rdf-toolkit.jar"

if [ -f "$JAR" ]; then
    echo "rdf-toolkit.jar v${RDF_TOOLKIT_VERSION} already present — nothing to do."
else
    echo "Downloading rdf-toolkit.jar v${RDF_TOOLKIT_VERSION}..."
    curl -L -o "$JAR" "$JAR_URL"
    echo "Done: $JAR"
fi
