"""Utilidades do worker: IMDSv2, logging e configuração."""

import logging
import os

import requests

IMDS_BASE = "http://169.254.169.254"
IMDS_TOKEN_TTL = 21600


def get_instance_id() -> str:
    """
    Obtém o instance ID via IMDSv2 (token obrigatório).

    Returns:
        Instance ID (ex: i-0abc123def456).

    Raises:
        RuntimeError: Se falha ao acessar IMDS.
    """
    try:
        token_resp = requests.put(
            f"{IMDS_BASE}/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": str(IMDS_TOKEN_TTL)},
            timeout=2,
        )
        token_resp.raise_for_status()
        token = token_resp.text

        id_resp = requests.get(
            f"{IMDS_BASE}/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=2,
        )
        id_resp.raise_for_status()
        return id_resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to get instance ID via IMDSv2: {e}")


def setup_logging(worker_id: str = "") -> logging.Logger:
    """
    Configura logging estruturado com worker_id.

    Args:
        worker_id: ID da instância EC2.

    Returns:
        Logger configurado.
    """
    log_format = f"%(asctime)s [%(levelname)s] [worker:{worker_id}] %(name)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, force=True)
    return logging.getLogger("seedbox.worker")


def load_config() -> dict:
    """
    Carrega configuração do worker a partir de variáveis de ambiente.

    Returns:
        Dict com todas as configurações e seus defaults.
    """
    return {
        "s3_bucket": os.environ.get("S3_BUCKET", ""),
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
        "transmission_secret_name": os.environ.get("TRANSMISSION_SECRET_NAME", "seedbox/transmission"),
        "poll_interval_seconds": int(os.environ.get("POLL_INTERVAL_SECONDS", "60")),
        "idle_cycles_before_shutdown": int(os.environ.get("IDLE_CYCLES_BEFORE_SHUTDOWN", "3")),
        "disk_critical_threshold_gb": float(os.environ.get("DISK_CRITICAL_THRESHOLD_GB", "2")),
        "disk_resume_threshold_gb": float(os.environ.get("DISK_RESUME_THRESHOLD_GB", "5")),
        "max_torrent_size_gb": int(os.environ.get("MAX_TORRENT_SIZE_GB", "50")),
    }
