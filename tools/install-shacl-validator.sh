#!/usr/bin/env bash
# Install the pinned shacl-validator binary used by tools/check-shacl.py.
# Run this once after cloning: bash tools/install-shacl-validator.sh
#
# shacl-cli publishes no prebuilt binaries, so the binary is built from the
# pinned crates.io release with a Rust toolchain. The build is cached in
# tools/bin/ (gitignored), mirroring tools/download-rdf-toolkit.sh.
set -euo pipefail

SHACL_CLI_VERSION="0.2.11"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
BINARY="$BIN_DIR/shacl-validator"

if [ -x "$BINARY" ]; then
    # Probe must not be fatal under `set -e -o pipefail`: a corrupt or
    # partially restored binary has to fall through to a rebuild, not abort.
    installed="$("$BINARY" capabilities 2>/dev/null | sed -n 's/.*"version":"\([^"]*\)".*/\1/p' || true)"
    if [ "$installed" = "$SHACL_CLI_VERSION" ]; then
        echo "shacl-validator v${SHACL_CLI_VERSION} already present — nothing to do."
        exit 0
    fi
    echo "Replacing shacl-validator v${installed:-unknown} with v${SHACL_CLI_VERSION}..."
    FORCE=(--force)
else
    FORCE=()
fi

if ! command -v cargo >/dev/null 2>&1; then
    echo "ERROR: cargo not found on PATH." >&2
    echo "shacl-cli is built from source; install Rust via https://rustup.rs and retry." >&2
    exit 1
fi

echo "Building shacl-cli v${SHACL_CLI_VERSION} (this takes about 30 seconds)..."
cargo install shacl-cli \
    --version "$SHACL_CLI_VERSION" \
    --locked \
    --root "$SCRIPT_DIR" \
    --quiet \
    "${FORCE[@]}"

echo "Done: $BINARY"
