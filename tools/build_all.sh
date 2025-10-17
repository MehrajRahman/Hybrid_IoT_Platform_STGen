#!/usr/bin/env bash
set -e

echo "=== Building all C protocol plugins ==="

for dir in protocols/*/; do
    if [[ -f "$dir/Makefile" ]]; then
        echo "Building $(basename $dir)..."
        make -C "$dir"
    fi
done

echo "=== Build complete ==="
ls -lh bin/