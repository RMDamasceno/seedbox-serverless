"""Monitoramento de progresso de um download ativo."""

import logging
import time
from datetime import datetime, timezone

from .error_handler import build_error_updates
from .s3_client import WorkerS3Client
from .sync import finalize_download
from .transmission_client import TransmissionClient, TransmissionError

logger = logging.getLogger(__name__)

MONITOR_INTERVAL_SECONDS = 10


def monitor_download(
    item: dict,
    transmission_id: int,
    worker_id: str,
    s3_client: WorkerS3Client,
    transmission: TransmissionClient,
    bucket: str,
) -> None:
    """
    Monitora progresso de um download até conclusão, erro ou cancelamento.

    Loop a cada 10 segundos:
    1. Verifica cancelRequested
    2. Obtém stats do Transmission
    3. Atualiza progresso no S3 (throttled)
    4. Detecta conclusão (seeding) ou erro

    Args:
        item: Dict do download.
        transmission_id: ID do torrent no Transmission.
        worker_id: ID da instância EC2.
        s3_client: Cliente S3 do worker.
        transmission: Cliente Transmission RPC.
        bucket: Nome do bucket S3.
    """
    item_id = item["id"]

    while True:
        # 1. Verificar cancelamento
        if s3_client.check_cancel_requested(item_id):
            logger.info("Cancel requested for %s", item_id)
            try:
                transmission.stop_torrent(transmission_id)
                transmission.remove_torrent(transmission_id, delete_data=True)
            except TransmissionError:
                pass
            s3_client.fail_item(item_id, worker_id, "cancelled", {
                "cancelledAt": datetime.now(timezone.utc).isoformat(),
                "errorMessage": "cancelled_by_user",
            })
            return

        # 2. Obter stats
        try:
            stats = transmission.get_torrent(transmission_id)
        except TransmissionError as e:
            logger.error("Failed to get torrent stats: %s", e)
            to_status, updates = build_error_updates(item, str(e))
            s3_client.fail_item(item_id, worker_id, to_status, updates)
            return

        progress = stats["percentDone"] * 100

        # 3. Atualizar progresso (throttled pelo s3_client)
        s3_client.update_progress(item_id, {
            "progressPercent": round(progress, 1),
            "downloadSpeedBps": stats.get("rateDownload", 0),
            "uploadSpeedBps": stats.get("rateUpload", 0),
            "eta": stats.get("eta"),
            "sizeBytesDownloaded": int(stats.get("sizeWhenDone", 0) * stats["percentDone"]),
            "sizeBytes": stats.get("sizeWhenDone"),
        })

        # 4. Verificar conclusão (status 6 = seeding)
        if stats.get("status") == 6:
            logger.info("Download complete for %s, starting sync", item_id)
            finalize_download(item, transmission_id, worker_id, s3_client, transmission, bucket)
            return

        # 5. Verificar erro do Transmission
        if stats.get("error", 0) != 0:
            error_str = stats.get("errorString", "unknown_transmission_error")
            logger.error("Transmission error for %s: %s", item_id, error_str)
            to_status, updates = build_error_updates(item, error_str)
            s3_client.fail_item(item_id, worker_id, to_status, updates)
            try:
                transmission.remove_torrent(transmission_id, delete_data=True)
            except TransmissionError:
                pass
            return

        time.sleep(MONITOR_INTERVAL_SECONDS)
