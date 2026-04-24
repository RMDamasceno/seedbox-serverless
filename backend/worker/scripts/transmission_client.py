"""Cliente para comunicação com Transmission daemon via JSON-RPC."""

import json
import logging

import requests

logger = logging.getLogger(__name__)

TRANSMISSION_URL = "http://127.0.0.1:9091/transmission/rpc"


class TransmissionError(Exception):
    """Erro de comunicação com o Transmission."""


class TransmissionClient:
    """Cliente JSON-RPC para o Transmission daemon."""

    def __init__(self, url: str = TRANSMISSION_URL, username: str = "", password: str = ""):
        self.url = url
        self.auth = (username, password) if username else None
        self.session_id = ""

    def _request(self, method: str, arguments: dict | None = None) -> dict:
        """
        Envia requisição RPC ao Transmission com retry de session ID.

        Args:
            method: Método RPC (ex: torrent-add, torrent-get).
            arguments: Argumentos do método.

        Returns:
            Dict com resultado da requisição.

        Raises:
            TransmissionError: Se falha na comunicação.
        """
        payload = {"method": method}
        if arguments:
            payload["arguments"] = arguments

        headers = {"X-Transmission-Session-Id": self.session_id}

        for attempt in range(2):
            try:
                resp = requests.post(
                    self.url, json=payload, headers=headers, auth=self.auth, timeout=30
                )

                if resp.status_code == 409:
                    self.session_id = resp.headers.get("X-Transmission-Session-Id", "")
                    headers["X-Transmission-Session-Id"] = self.session_id
                    continue

                resp.raise_for_status()
                data = resp.json()

                if data.get("result") != "success":
                    raise TransmissionError(f"RPC error: {data.get('result')}")

                return data.get("arguments", {})

            except requests.ConnectionError:
                raise TransmissionError("Transmission daemon not available")
            except requests.Timeout:
                raise TransmissionError("Transmission RPC timeout")

        raise TransmissionError("Failed after session ID retry")

    def add_torrent(self, magnet_or_file: str) -> int:
        """
        Adiciona torrent via magnet link ou caminho de arquivo.

        Args:
            magnet_or_file: Magnet link ou caminho local do .torrent.

        Returns:
            ID do torrent no Transmission.
        """
        if magnet_or_file.startswith("magnet:"):
            args = {"filename": magnet_or_file}
        else:
            args = {"filename": magnet_or_file}

        result = self._request("torrent-add", args)
        torrent = result.get("torrent-added") or result.get("torrent-duplicate")
        if not torrent:
            raise TransmissionError("No torrent returned from add")
        return torrent["id"]

    def get_torrent(self, torrent_id: int) -> dict:
        """
        Obtém status de um torrent.

        Args:
            torrent_id: ID do torrent no Transmission.

        Returns:
            Dict com percentDone, rateDownload, rateUpload, eta, error, errorString, status, sizeWhenDone.
        """
        result = self._request("torrent-get", {
            "ids": [torrent_id],
            "fields": [
                "percentDone", "rateDownload", "rateUpload", "eta",
                "error", "errorString", "status", "sizeWhenDone", "name",
            ],
        })
        torrents = result.get("torrents", [])
        if not torrents:
            raise TransmissionError(f"Torrent {torrent_id} not found")
        return torrents[0]

    def stop_torrent(self, torrent_id: int) -> None:
        """Pausa um torrent."""
        self._request("torrent-stop", {"ids": [torrent_id]})

    def start_torrent(self, torrent_id: int) -> None:
        """Retoma um torrent."""
        self._request("torrent-start", {"ids": [torrent_id]})

    def remove_torrent(self, torrent_id: int, delete_data: bool = False) -> None:
        """
        Remove um torrent do Transmission.

        Args:
            torrent_id: ID do torrent.
            delete_data: Se True, remove também os dados baixados.
        """
        self._request("torrent-remove", {
            "ids": [torrent_id],
            "delete-local-data": delete_data,
        })

    def stop_all(self) -> None:
        """Pausa todos os torrents."""
        self._request("torrent-stop")

    def start_all(self) -> None:
        """Retoma todos os torrents."""
        self._request("torrent-start")
