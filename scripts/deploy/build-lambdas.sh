#!/bin/bash
set -euo pipefail

# Empacota as 3 Lambdas com dependências em zips para deploy.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend/lambda"
BUILD_DIR="$PROJECT_ROOT/iac/terraform/modules/lambda/packages"

rm -rf "$BUILD_DIR"/*.zip

echo "=== Building seedbox-api ==="
TMPDIR=$(mktemp -d)
pip install pydantic PyJWT bcrypt -t "$TMPDIR" --quiet --no-cache-dir
cp "$BACKEND_DIR/api/handler.py" "$TMPDIR/"
cp "$BACKEND_DIR/api/routes.py" "$TMPDIR/"
cp "$BACKEND_DIR/api/state_manager.py" "$TMPDIR/"
cp "$BACKEND_DIR/api/validators.py" "$TMPDIR/"
cp "$BACKEND_DIR/api/auth.py" "$TMPDIR/"
cp "$BACKEND_DIR/api/exceptions.py" "$TMPDIR/"
cp "$BACKEND_DIR/api/response.py" "$TMPDIR/"
cd "$TMPDIR" && zip -r9 "$BUILD_DIR/api.zip" . -x '*.pyc' '__pycache__/*' '*.dist-info/*' > /dev/null
rm -rf "$TMPDIR"
echo "  -> api.zip ($(du -h "$BUILD_DIR/api.zip" | cut -f1))"

echo "=== Building seedbox-authorizer ==="
TMPDIR=$(mktemp -d)
pip install PyJWT -t "$TMPDIR" --quiet --no-cache-dir
cp "$BACKEND_DIR/authorizer/handler.py" "$TMPDIR/"
cd "$TMPDIR" && zip -r9 "$BUILD_DIR/authorizer.zip" . -x '*.pyc' '__pycache__/*' '*.dist-info/*' > /dev/null
rm -rf "$TMPDIR"
echo "  -> authorizer.zip ($(du -h "$BUILD_DIR/authorizer.zip" | cut -f1))"

echo "=== Building seedbox-worker-trigger ==="
TMPDIR=$(mktemp -d)
cp "$BACKEND_DIR/worker-trigger/handler.py" "$TMPDIR/"
cd "$TMPDIR" && zip -r9 "$BUILD_DIR/worker-trigger.zip" . -x '*.pyc' '__pycache__/*' > /dev/null
rm -rf "$TMPDIR"
echo "  -> worker-trigger.zip ($(du -h "$BUILD_DIR/worker-trigger.zip" | cut -f1))"

echo "=== Build complete ==="
