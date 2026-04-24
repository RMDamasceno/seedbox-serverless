"""Loop principal do worker EC2 — polling S3, download e auto-shutdown."""

import json
import logging
import os
import signal
import subprocess
import sys
import time

import boto3

from .disk_manager import DiskManager
from .error_handler import build_error_updates
from .monitor import monitor_download
from .s3_client import WorkerS3Client
from .spot_handler import check_spot_interruption
from .transmission_client import TransmissionClient, TransmissionError
from .utils import get_instance_id, load_config, setup_logging

logger = logging.getLogger(__name__)


class Worker:
    """Worker principal que coordena polling, downloads e shutdown."""

    def __init__(self):
        self.config = load_config()
        self.worker_id = ""
        self.s3_client: WorkerS3Client | None = None
        self.transmission: TransmissionClient | None = None
        self.disk: DiskManager | None = None
        self._shutdown_requested = False

    def start(self) -> None:
        """Inicializa o worker e entra no loop principal."""
        self.worker_id = get_instance_id()
        setup_logging(self.worker_id)
        logger.info("Worker starting: %s", self.worker_id)

        self.s3_client = WorkerS3Client(self.config["s3_bucket"])
        self.disk = DiskManager(
            critical_gb=self.config["disk_critical_threshold_gb"],
            resume_gb=self.config["disk_resume_threshold_gb"],
        )

        # Obter credenciais do Transmission via Secrets Manager
        transmission_creds = self._get_transmission_creds()
        self.transmission = TransmissionClient(
            username=transmission_creds.get("username", "seedbox"),
            password=transmission_creds.get("password", ""),
        )

        # Signal handling
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self._main_loop()

    def _main_loop(self) -> None:
        """Loop principal: poll, process, shutdown."""
        idle_cycles = 0
        poll_interval = self.config["poll_interval_seconds"]
        max_idle = self.config["idle_cycles_before_shutdown"]

        while not self._shutdown_requested:
            # Verificar Spot interruption
            if check_spot_interruption():
                logger.warning("Spot interruption — initiating graceful shutdown")
                self._graceful_shutdown()
                return

            # Gerenciamento de disco
            self._check_disk()

            # Buscar próximo item
            item = self.s3_client.get_next_pending_item()

            if item:
                idle_cycles = 0
                self._process_item(item)
            else:
                idle_cycles += 1
                logger.info("Idle cycle %d/%d", idle_cycles, max_idle)
                if idle_cycles >= max_idle:
                    logger.info("Max idle cycles reached — shutting down")
                    self._graceful_shutdown()
                    return

            time.sleep(poll_interval)

    def _process_item(self, item: dict) -> None:
        """
        Processa um item: adquire lock, inicia download, monitora.

        Args:
            item: Dict do download pendente.
        """
        item_id = item["id"]
        logger.info("Processing item %s: %s", item_id, item.get("name", ""))

        # Verificar disco
        ok, error_msg = self.disk.check_before_start(item)
        if not ok:
            to_status, updates = build_error_updates(item, error_msg)
            self.s3_client.fail_item(item_id, self.worker_id, to_status, updates)
            return

        # Adquirir lock
        locked = self.s3_client.acquire_lock(item_id, self.worker_id)
        if not locked:
            logger.info("Failed to acquire lock for %s, skipping", item_id)
            return

        # Adicionar ao Transmission
        try:
            magnet_or_file = item.get("magnetLink") or self._download_torrent_file(item)
            transmission_id = self.transmission.add_torrent(magnet_or_file)
        except (TransmissionError, Exception) as e:
            logger.error("Failed to add torrent: %s", e)
            to_status, updates = build_error_updates(item, str(e))
            self.s3_client.fail_item(item_id, self.worker_id, to_status, updates)
            return

        # Atualizar transmissionId
        self.s3_client.update_progress(item_id, {"transmissionId": transmission_id})

        # Monitorar download
        monitor_download(
            locked, transmission_id, self.worker_id,
            self.s3_client, self.transmission, self.config["s3_bucket"],
        )

    def _download_torrent_file(self, item: dict) -> str:
        """Baixa arquivo .torrent do S3 para disco local."""
        s3_key = item.get("torrentS3Key")
        if not s3_key:
            raise ValueError("No torrent source available")

        local_path = f"/tmp/{item['id']}.torrent"
        s3 = boto3.client("s3")
        s3.download_file(self.config["s3_bucket"], s3_key, local_path)
        return local_path

    def _check_disk(self) -> None:
        """Verifica disco e pausa/retoma torrents conforme necessário."""
        if self.disk.check_critical():
            if not self.disk.is_paused_for_disk:
                self.transmission.stop_all()
                self.disk.is_paused_for_disk = True
                logger.warning("All torrents paused — disk critical")
        elif self.disk.check_resume():
            self.transmission.start_all()
            self.disk.is_paused_for_disk = False
            logger.info("Torrents resumed — disk recovered")

    def _graceful_shutdown(self) -> None:
        """Shutdown gracioso: para torrents, move itens para pending, desliga."""
        logger.info("Graceful shutdown initiated")

        try:
            self.transmission.stop_all()
        except TransmissionError:
            pass

        self.s3_client.move_processing_to_pending(self.worker_id)

        logger.info("Shutdown complete — powering off")
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)

    def _handle_signal(self, signum, frame) -> None:
        """Handler para SIGTERM/SIGINT."""
        logger.warning("Signal %d received — initiating graceful shutdown", signum)
        self._shutdown_requested = True
        self._graceful_shutdown()
        sys.exit(0)

    def _get_transmission_creds(self) -> dict:
        """Busca credenciais do Transmission no Secrets Manager."""
        client = boto3.client("secretsmanager")
        resp = client.get_secret_value(SecretId=self.config["transmission_secret_name"])
        return json.loads(resp["SecretString"])


def main():
    worker = Worker()
    worker.start()


if __name__ == "__main__":
    main()
