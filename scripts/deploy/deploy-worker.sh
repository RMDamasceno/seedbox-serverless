#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUCKET="${1:-seedbox-318940352257}"
REGION="${2:-us-east-1}"

echo "=== Deploying worker scripts to s3://$BUCKET/worker/ ==="

aws s3 sync "$PROJECT_ROOT/backend/worker/scripts/" "s3://$BUCKET/worker/scripts/" \
  --exclude '*.pyc' --exclude '__pycache__/*' --exclude '.gitkeep' \
  --region "$REGION" --delete

aws s3 sync "$PROJECT_ROOT/backend/worker/config/" "s3://$BUCKET/worker/config/" \
  --exclude '.gitkeep' \
  --region "$REGION" --delete

echo "=== Worker scripts deployed ==="
aws s3 ls "s3://$BUCKET/worker/" --recursive --region "$REGION"
