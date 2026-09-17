#!/usr/bin/env bash
# Verify target code generation; native runtime validation is a separate stage.
set -euo pipefail
cd "$(dirname "$0")/.."
SUN_BIN=${SUN_BIN:-sun}
SUN_LIB_ROOT=${SUN_LIB_ROOT:-/usr/lib/sun}
mkdir -p build
for target in aarch64-linux-gnu arm64-apple-darwin; do
  "$SUN_BIN" --emit-obj --target "$target" --lib-path "$SUN_LIB_ROOT/$target" \
    -o "build/process_monitor-$target.o" src/main.sun
done
