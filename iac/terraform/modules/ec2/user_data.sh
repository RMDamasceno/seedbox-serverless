#!/bin/bash
set -euo pipefail

exec > >(tee /var/log/seedbox-setup.log) 2>&1
echo "=== Seedbox Worker Setup - $(date) ==="

# Variáveis (injetadas pelo Terraform templatefile)
S3_BUCKET="${s3_bucket}"
AWS_REGION="${aws_region}"

# Instalar dependências do sistema
dnf install -y python3.12 python3-pip transmission-daemon

# Instalar pacotes Python
pip3 install boto3 requests bcrypt

# Instalar rclone
curl -s https://rclone.org/install.sh | bash

# Criar diretórios
mkdir -p /data/downloads /data/incomplete /opt/seedbox

# Baixar scripts do worker do S3
echo "=== Downloading worker scripts from S3 ==="
aws s3 sync "s3://$S3_BUCKET/worker/scripts/" /opt/seedbox/ --region "$AWS_REGION"
aws s3 sync "s3://$S3_BUCKET/worker/config/" /opt/seedbox/config/ --region "$AWS_REGION"

# Configurar rclone
mkdir -p /root/.config/rclone
cat > /root/.config/rclone/rclone.conf <<RCLONE
[s3]
type = s3
provider = AWS
env_auth = true
region = $AWS_REGION
RCLONE

# Configurar Transmission
systemctl stop transmission-daemon || true

# Obter senha do Transmission do Secrets Manager
TRANS_SECRET=$(aws secretsmanager get-secret-value --secret-id seedbox/transmission --region "$AWS_REGION" --query SecretString --output text)
TRANS_PASS=$(echo "$TRANS_SECRET" | python3 -c "import sys,json;print(json.load(sys.stdin)['password'])")

cat > /etc/transmission-daemon/settings.json <<TRANSMISSION
{
  "download-dir": "/data/downloads",
  "incomplete-dir": "/data/incomplete",
  "incomplete-dir-enabled": true,
  "rpc-enabled": true,
  "rpc-bind-address": "127.0.0.1",
  "rpc-port": 9091,
  "rpc-whitelist-enabled": false,
  "rpc-authentication-required": true,
  "rpc-username": "seedbox",
  "rpc-password": "$TRANS_PASS",
  "speed-limit-up": 10240,
  "speed-limit-up-enabled": true,
  "seed-queue-enabled": true,
  "seed-queue-size": 5,
  "ratio-limit": 2.0,
  "ratio-limit-enabled": true,
  "peer-limit-global": 200,
  "peer-limit-per-torrent": 50,
  "max-peers-global": 200,
  "upload-slots-per-torrent": 8,
  "cache-size-mb": 256
}
TRANSMISSION

systemctl enable transmission-daemon
systemctl start transmission-daemon

# Aguardar Transmission iniciar
sleep 5

# Iniciar worker
echo "=== Starting worker - $(date) ==="
export S3_BUCKET="$S3_BUCKET"
export AWS_REGION="$AWS_REGION"
export TRANSMISSION_SECRET_NAME="seedbox/transmission"

cd /opt/seedbox
python3 -m main &

echo "=== Setup complete - $(date) ==="
