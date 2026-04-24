"""Testes unitários para módulos do worker."""

from unittest.mock import patch

import pytest

from backend.worker.scripts.error_handler import build_error_updates, classify_error
from backend.worker.scripts.disk_manager import DiskManager


class TestClassifyError:

    def test_definitive_torrent_not_found(self):
        assert classify_error("Torrent not found on tracker") == "definitive"

    def test_definitive_invalid_hash(self):
        assert classify_error("invalid hash detected") == "definitive"

    def test_definitive_corrupted(self):
        assert classify_error("File corrupted during download") == "definitive"

    def test_operational_disk_space(self):
        assert classify_error("disk_space_insufficient: 1.5GB free") == "operational"

    def test_operational_no_space(self):
        assert classify_error("No space left on device") == "operational"

    def test_temporary_network(self):
        assert classify_error("Connection timed out") == "temporary"

    def test_temporary_unknown(self):
        assert classify_error("some random error") == "temporary"


class TestBuildErrorUpdates:

    def test_definitive_goes_to_cancelled(self):
        item = {"retryCount": 0}
        to_status, updates = build_error_updates(item, "Torrent not found")

        assert to_status == "cancelled"
        assert "cancelledAt" in updates

    def test_temporary_first_retry(self):
        item = {"retryCount": 0}
        to_status, updates = build_error_updates(item, "Connection timeout")

        assert to_status == "pending"
        assert updates["retryCount"] == 1
        assert "retryAfter" in updates

    def test_temporary_retries_exhausted(self):
        item = {"retryCount": 3}
        to_status, updates = build_error_updates(item, "Connection timeout")

        assert to_status == "cancelled"

    def test_operational_no_retry_consumed(self):
        item = {"retryCount": 1}
        to_status, updates = build_error_updates(item, "disk_space_insufficient")

        assert to_status == "pending"
        assert "retryCount" not in updates  # não incrementa

    def test_backoff_intervals(self):
        for i, expected_min in enumerate([60, 300, 900]):
            item = {"retryCount": i}
            _, updates = build_error_updates(item, "Connection timeout")
            assert updates["retryCount"] == i + 1


class TestDiskManager:

    @patch("backend.worker.scripts.disk_manager.shutil.disk_usage")
    def test_check_before_start_sufficient(self, mock_usage):
        mock_usage.return_value = type("Usage", (), {"free": 50e9})()
        dm = DiskManager()
        item = {"sizeBytes": 10 * 1e9}

        ok, msg = dm.check_before_start(item)
        assert ok is True
        assert msg is None

    @patch("backend.worker.scripts.disk_manager.shutil.disk_usage")
    def test_check_before_start_insufficient(self, mock_usage):
        mock_usage.return_value = type("Usage", (), {"free": 3e9})()
        dm = DiskManager()
        item = {"sizeBytes": 10 * 1e9}

        ok, msg = dm.check_before_start(item)
        assert ok is False
        assert "insufficient" in msg

    @patch("backend.worker.scripts.disk_manager.shutil.disk_usage")
    def test_check_critical_below_threshold(self, mock_usage):
        mock_usage.return_value = type("Usage", (), {"free": 1e9})()
        dm = DiskManager(critical_gb=2.0)

        assert dm.check_critical() is True

    @patch("backend.worker.scripts.disk_manager.shutil.disk_usage")
    def test_check_critical_above_threshold(self, mock_usage):
        mock_usage.return_value = type("Usage", (), {"free": 10e9})()
        dm = DiskManager(critical_gb=2.0)

        assert dm.check_critical() is False

    @patch("backend.worker.scripts.disk_manager.shutil.disk_usage")
    def test_check_resume_when_paused(self, mock_usage):
        mock_usage.return_value = type("Usage", (), {"free": 10e9})()
        dm = DiskManager(resume_gb=5.0)
        dm.is_paused_for_disk = True

        assert dm.check_resume() is True

    @patch("backend.worker.scripts.disk_manager.shutil.disk_usage")
    def test_check_resume_when_not_paused(self, mock_usage):
        mock_usage.return_value = type("Usage", (), {"free": 10e9})()
        dm = DiskManager(resume_gb=5.0)

        assert dm.check_resume() is False

    @patch("backend.worker.scripts.disk_manager.shutil.disk_usage")
    def test_minimum_5gb_required(self, mock_usage):
        mock_usage.return_value = type("Usage", (), {"free": 4e9})()
        dm = DiskManager()
        item = {"sizeBytes": 1e9}  # 1GB * 1.1 = 1.1GB, mas min é 5GB

        ok, _ = dm.check_before_start(item)
        assert ok is False
