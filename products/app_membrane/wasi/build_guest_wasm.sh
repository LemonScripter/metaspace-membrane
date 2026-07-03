#!/usr/bin/env bash
# Build the WASI guest (Rust -> wasm32-wasip1) and copy the module next to the demo.
# Requires: rustup + the wasm32-wasip1 target (rustup target add wasm32-wasip1).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/guest"
cargo build --release --target wasm32-wasip1
cp "target/wasm32-wasip1/release/guest.wasm" "$HERE/guest.wasm"
echo "built: $HERE/guest.wasm"
