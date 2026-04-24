"""Finalização de download: sync para S3 via rclone."""

import logging
import subprocess

import boto3
from botocore.exceptions import ClientError

from .error_handler import build_error_updates
from .transmission_client import TransmissionClient, TransmissionError

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "/data/downloads"


def finalize_download(
    item: dict,
    transmission_id: int,
    worker_id: str,
    s3_client,
    transmission: TransmissionClient,
    bucket: str,
) -> None:
    """
    Sincroniza arquivo concluído para S3 e transiciona para completed.

    1. rclone move do diretório local para S3
    2. Verifica tamanho no S3
    3. Remove torrent do Transmission
    4. Transição processing → completed

    Args:
        item: Dict do download.
        transmission_id: ID do torrent no Transmission.
        worker_id: ID da instância EC2.
        s3_client: Cliente S3 do worker.
        transmission: Cliente Transmission RPC.
        bucket: Nome do bucket S3.
    """
    item_id = item["id"]
    name = item.get("name", item_id)
    local_path = f"{DOWNLOAD_DIR}/{name}"
    s3_dest = f"s3:{bucket}/downloads/completed/{item_id}/"

    logger.info("Starting rclone sync for %s: %s → %s", item_id, local_path, s3_dest)

    result = subprocess.run(
        [
            "rclone", "move", local_path, s3_dest,
            "--s3-storage-class", "INTELLIGENT_TIERING",
            "--transfers", "4",
            "--checksum",
            "--config", "/opt/seedbox/rclone.conf",
        ],
        capture_output=True, text=True, timeout=7200,
    )

    if result.returncode != 0:
        error_msg = f"rclone_failed: {result.stderr[:500]}"
        logger.error("rclone failed for %s: %s", item_id, error_msg)
        to_status, updates = build_error_updates(item, error_msg)
        s3_client.fail_item(item_id, worker_id, to_status, updates)
        return

    # Obter tamanho total no S3
    s3_key = f"downloads/completed/{item_id}/"
    s3_size = _get_prefix_size(bucket, s3_key)

    # Remover torrent do Transmission (dados já movidos)
    try:
        transmission.remove_torrent(transmission_id, delete_data=False)
    except TransmissionError:
        logger.warning("Failed to remove torrent %d from Transmission", transmission_id)

    # Transição para completed
    s3_client.complete_item(item_id, worker_id, s3_key, s3_size)
    logger.info("Download %s completed, %d bytes synced to S3", item_id, s3_size)


def _get_prefix_size(bucket: str, prefix: str) -> int:
    """Calcula tamanho total de objetos sob um prefixo S3."""
    s3 = boto3.client("s3")
    total = 0
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                total += obj.get("Size", 0)
    except ClientError:
        logger.warning("Failed to calculate S3 size for %s", prefix)
    return total
