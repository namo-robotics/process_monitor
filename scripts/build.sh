#!/usr/bin/env bash
# Build the monitor with the installed, pinned Sun toolchain.
set -euo pipefail
cd "$(dirname "$0")/.."
SUN_BIN=${SUN_BIN:-sun}
expected=$(python3 -c 'import json; print(json.load(open("toolchain.lock.json"))["sun"]["revision"][:12])')
if [[ "$($SUN_BIN --version)" != *"$expected"* && "${ALLOW_UNTESTED_SUN:-0}" != 1 ]]; then
  echo "Expected Sun revision $expected; set ALLOW_UNTESTED_SUN=1 to try another version." >&2
  exit 1
fi
link_flags=()
if [[ $(uname -s) == Darwin ]]; then link_flags+=(-lproc); fi
mkdir -p build
"$SUN_BIN" -c --dynamic -o build/process_monitor src/main.sun "${link_flags[@]}"
