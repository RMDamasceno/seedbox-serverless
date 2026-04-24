"""Gerenciamento de disco do worker."""

import logging
import shutil

logger = logging.getLogger(__name__)

DATA_PATH = "/data"


class DiskManager:
    """Monitora espaço em disco e pausa/retoma torrents conforme necessário."""

    def __init__(self, critical_gb: float = 2.0, resume_gb: float = 5.0):
        self.critical_gb = critical_gb
        self.resume_gb = resume_gb
        self._paused_for_disk = False

    def get_free_gb(self) -> float:
        """Retorna espaço livre em GB no volume de dados."""
        stat = shutil.disk_usage(DATA_PATH)
        return stat.free / 1e9

    def check_before_start(self, item: dict) -> tuple[bool, str | None]:
        """
        Verifica se há espaço suficiente antes de iniciar um download.

        Args:
            item: Dict do download com campo sizeBytes.

        Returns:
            Tupla (ok, error_message). ok=False se espaço insuficiente.
        """
        free_gb = self.get_free_gb()
        estimated_gb = (item.get("sizeBytes") or 0) / 1e9
        required_gb = max(estimated_gb * 1.1, 5.0)

        if free_gb < required_gb:
            msg = f"disk_space_insufficient: {free_gb:.1f}GB free, {required_gb:.1f}GB required"
            logger.warning(msg)
            return False, msg
        return True, None

    def check_critical(self) -> bool:
        """
        Verifica se disco está abaixo do threshold crítico.

        Returns:
            True se disco está em estado crítico (< critical_gb).
        """
        free_gb = self.get_free_gb()
        is_critical = free_gb < self.critical_gb
        if is_critical and not self._paused_for_disk:
            logger.warning("Disk critical: %.1fGB free (threshold: %.1fGB)",
                           free_gb, self.critical_gb)
        return is_critical

    def check_resume(self) -> bool:
        """
        Verifica se disco tem espaço suficiente para retomar.

        Returns:
            True se pode retomar (> resume_gb e estava pausado).
        """
        if not self._paused_for_disk:
            return False
        free_gb = self.get_free_gb()
        can_resume = free_gb >= self.resume_gb
        if can_resume:
            logger.info("Disk recovered: %.1fGB free, resuming", free_gb)
        return can_resume

    @property
    def is_paused_for_disk(self) -> bool:
        return self._paused_for_disk

    @is_paused_for_disk.setter
    def is_paused_for_disk(self, value: bool) -> None:
        self._paused_for_disk = value
