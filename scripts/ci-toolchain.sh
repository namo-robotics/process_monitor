#!/usr/bin/env bash
# Install the checksum-pinned release compiler and stdlibs without source builds.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/install-sun.py
