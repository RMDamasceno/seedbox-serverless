#!/bin/bash
set -euo pipefail

# Logging
exec > >(tee /var/log/seedbox-setup.log) 2>&1
echo "=== Seedbox Worker Setup - $(date) ==="

# Instalar dependências
dnf install -y transmission-daemon python3.12 python3-pip

# Instalar pacotes Python
pip3 install boto3 requests

# Instalar rclone
curl -s https://rclone.org/install.sh | bash

# Criar diretórios de dados
mkdir -p /data/downloads /data/incomplete /opt/seedbox

# Configurar Transmission
systemctl stop transmission-daemon || true

# Copiar configuração do Transmission (será substituída pelo worker no boot)
cat > /etc/transmission-daemon/settings.json << 'TRANSMISSION_CONFIG'
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
  "rpc-password": "${TRANSMISSION_PASSWORD}",
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
TRANSMISSION_CONFIG

systemctl enable transmission-daemon
systemctl start transmission-daemon

# Iniciar worker
echo "=== Setup completo - $(date) ==="
python3 /opt/seedbox/main.py &
