#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend/lambda"
BUILD_DIR="$PROJECT_ROOT/iac/terraform/modules/lambda/packages"

mkdir -p "$BUILD_DIR"
rm -f "$BUILD_DIR"/*.zip

build_lambda() {
    local name="$1"
    local src_dir="$2"
    shift 2
    local deps=("$@")

    echo "=== Building $name ==="
    local tmpdir
    tmpdir=$(mktemp -d)

    if [ ${#deps[@]} -gt 0 ]; then
        pip install "${deps[@]}" -t "$tmpdir" --quiet --no-cache-dir 2>/dev/null
    fi

    cp "$src_dir"/*.py "$tmpdir/" 2>/dev/null || true

    (cd "$tmpdir" && zip -r9 "$BUILD_DIR/${name}.zip" . -x '*.pyc' '*__pycache__*' '*.dist-info/*' > /dev/null)

    rm -rf "$tmpdir"
    echo "  -> ${name}.zip ($(du -h "$BUILD_DIR/${name}.zip" | cut -f1))"
}

build_lambda "api" "$BACKEND_DIR/api" pydantic PyJWT bcrypt
build_lambda "authorizer" "$BACKEND_DIR/authorizer" PyJWT
build_lambda "worker-trigger" "$BACKEND_DIR/worker-trigger"

echo "=== Build complete ==="
ls -lh "$BUILD_DIR"/*.zip
