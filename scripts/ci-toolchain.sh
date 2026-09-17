#!/usr/bin/env bash
# Build only the pinned native Sun compiler and standard library needed by CI.
set -euo pipefail
cd "$(dirname "$0")/.."
source_dir="$PWD/.ci/sun-source"
build_dir="$PWD/.ci/sun-build"
install_dir="$PWD/.ci/toolchain"
expected=$(python3 -c 'import json; print(json.load(open("toolchain.lock.json"))["sun"]["revision"])')
[[ $(git -C "$source_dir" rev-parse HEAD) == "$expected" ]]
if [[ $(uname -s) == Darwin ]]; then
  llvm_prefix=$(brew --prefix llvm@20)
else
  llvm_prefix=/usr/lib/llvm-20
fi
cmake -S "$source_dir" -B "$build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DCMAKE_C_COMPILER="$llvm_prefix/bin/clang" \
  -DCMAKE_CXX_COMPILER="$llvm_prefix/bin/clang++" \
  -DLLVM_DIR="$llvm_prefix/lib/cmake/llvm" \
  -DSUN_CROSS_STDLIB_TARGETS=""
cmake --build "$build_dir" --target sun stdlib_moon --parallel 2
mkdir -p "$install_dir"
cp "$build_dir/sun" "$build_dir/stdlib.moon" "$install_dir/"
"$install_dir/sun" --version
