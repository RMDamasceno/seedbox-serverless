#!/bin/bash
set -euo pipefail

BUCKET="${1:?Usage: deploy-frontend.sh <bucket-name>}"
FRONTEND_DIR="$(cd "$(dirname "$0")/../../frontend" && pwd)"

echo "=== Building frontend ==="
cd "$FRONTEND_DIR"
npm ci
npm run build

echo "=== Deploying to s3://$BUCKET ==="

# Assets com cache longo (hash no nome)
aws s3 sync dist/assets/ "s3://$BUCKET/assets/" \
  --cache-control "max-age=31536000,public,immutable" \
  --delete

# index.html sem cache
aws s3 cp dist/index.html "s3://$BUCKET/index.html" \
  --cache-control "no-cache,no-store,must-revalidate"

# Demais arquivos
aws s3 sync dist/ "s3://$BUCKET/" \
  --exclude "assets/*" \
  --exclude "index.html" \
  --cache-control "max-age=3600,public" \
  --delete

echo "=== Deploy complete ==="
