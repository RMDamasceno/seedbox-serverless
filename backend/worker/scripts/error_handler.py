"""Classificação de erros e política de retry com backoff exponencial."""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

RETRY_INTERVALS_SECONDS = [60, 300, 900]  # 1min, 5min, 15min

DEFINITIVE_PATTERNS = [
    "torrent not found",
    "invalid hash",
    "corrupted",
    "not valid torrent",
    "unregistered torrent",
    "info hash",
]

OPERATIONAL_PATTERNS = [
    "disk_space",
    "no space left",
    "size exceeds",
]


def classify_error(error_string: str) -> str:
    """
    Classifica um erro como temporary, definitive ou operational.

    Args:
        error_string: Mensagem de erro.

    Returns:
        Categoria: 'temporary', 'definitive' ou 'operational'.
    """
    lower = error_string.lower()

    for pattern in DEFINITIVE_PATTERNS:
        if pattern in lower:
            return "definitive"

    for pattern in OPERATIONAL_PATTERNS:
        if pattern in lower:
            return "operational"

    return "temporary"


def build_error_updates(item: dict, error_string: str) -> tuple[str, dict]:
    """
    Determina o estado destino e campos de atualização baseado no erro.

    Args:
        item: Dict do download atual.
        error_string: Mensagem de erro.

    Returns:
        Tupla (to_status, updates_dict).
    """
    category = classify_error(error_string)
    retry_count = item.get("retryCount", 0)

    logger.info("Error classified as %s: %s", category, error_string[:100])

    if category == "definitive" or retry_count >= len(RETRY_INTERVALS_SECONDS):
        return "cancelled", {
            "cancelledAt": datetime.now(timezone.utc).isoformat(),
            "errorMessage": error_string,
        }

    if category == "operational":
        # Não consome retry
        return "pending", {
            "errorMessage": error_string,
            "workerId": None,
        }

    # Temporário: backoff exponencial
    retry_after = (
        datetime.now(timezone.utc) + timedelta(seconds=RETRY_INTERVALS_SECONDS[retry_count])
    ).isoformat()

    return "pending", {
        "retryCount": retry_count + 1,
        "retryAfter": retry_after,
        "errorMessage": error_string,
        "workerId": None,
    }
