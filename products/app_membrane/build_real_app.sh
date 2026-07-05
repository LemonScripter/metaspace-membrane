#!/usr/bin/env bash
# Build the REAL app (Rust -> wasm32-wasip1) and copy the module next to the demo.
# Requires: rustup + the wasm32-wasip1 target.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/real_app"
cargo build --release --target wasm32-wasip1
cp "target/wasm32-wasip1/release/real_app.wasm" "$HERE/real_app.wasm"
echo "built: $HERE/real_app.wasm"
