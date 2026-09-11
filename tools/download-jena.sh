#!/usr/bin/env bash
# Download the pinned Apache Jena distribution used by tools/check-shacl.py.
# Run this once after cloning: bash tools/download-jena.sh
#
# Jena 6 requires Java 21+. rdf-toolkit still runs on Java 11, but the
# combined local toolchain is therefore Java 21.
set -euo pipefail

JENA_VERSION="6.2.0"
# archive.apache.org keeps every release; dlcdn.apache.org only keeps current.
TARBALL="apache-jena-${JENA_VERSION}.tar.gz"
TARBALL_URL="https://archive.apache.org/dist/jena/binaries/${TARBALL}"
# https://archive.apache.org/dist/jena/binaries/apache-jena-6.2.0.tar.gz.sha512
TARBALL_SHA512="2b467d2ff940c207aea935e012ecbb0f0ab3e6bf59b3fc4b3fbc6cf9cea11f1428e97882ec078a5ffc57e114e0f5c88ea98c4575e687cc1dd232f99324b7b2a2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$SCRIPT_DIR/apache-jena-${JENA_VERSION}"

if [ -x "$DEST/bin/shacl" ] && [ -x "$DEST/bin/riot" ]; then
    echo "Apache Jena ${JENA_VERSION} already present — nothing to do."
    exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl not found on PATH." >&2
    exit 1
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
ARCHIVE="$TMPDIR/$TARBALL"

echo "Downloading Apache Jena ${JENA_VERSION}..."
curl -fsSL -o "$ARCHIVE" "$TARBALL_URL"

if command -v sha512sum >/dev/null 2>&1; then
    echo "${TARBALL_SHA512}  ${ARCHIVE}" | sha512sum -c - >/dev/null
elif command -v shasum >/dev/null 2>&1; then
    echo "${TARBALL_SHA512}  ${ARCHIVE}" | shasum -a 512 -c - >/dev/null
else
    echo "ERROR: neither sha512sum nor shasum found; cannot verify Jena tarball." >&2
    exit 1
fi

# Replace a partial extract from a previous interrupted download.
rm -rf "$DEST"
tar -xzf "$ARCHIVE" -C "$SCRIPT_DIR"

if [ ! -x "$DEST/bin/shacl" ] || [ ! -x "$DEST/bin/riot" ]; then
    echo "ERROR: Apache Jena ${JENA_VERSION} extracted without bin/shacl or bin/riot." >&2
    exit 1
fi

echo "Done: $DEST"
