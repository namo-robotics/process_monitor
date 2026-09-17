#!/usr/bin/env bash
# Run unit tests and process-level integration checks.
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/build.sh
build/process_monitor_test
python3 tests/integration.py
