"""Detecção de Spot interruption via metadata endpoint IMDSv2."""

import logging

import requests

logger = logging.getLogger(__name__)

IMDS_BASE = "http://169.254.169.254"
IMDS_TOKEN_TTL = 21600


def check_spot_interruption() -> bool:
    """
    Verifica se há interrupção Spot iminente via metadata endpoint.

    Usa IMDSv2 com token obrigatório.

    Returns:
        True se interrupção detectada, False caso contrário.
    """
    try:
        token_resp = requests.put(
            f"{IMDS_BASE}/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": str(IMDS_TOKEN_TTL)},
            timeout=2,
        )
        token_resp.raise_for_status()
        token = token_resp.text

        resp = requests.get(
            f"{IMDS_BASE}/latest/meta-data/spot/instance-action",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=2,
        )

        if resp.status_code == 200:
            logger.warning("Spot interruption detected: %s", resp.text)
            return True

        return False

    except requests.RequestException:
        return False
