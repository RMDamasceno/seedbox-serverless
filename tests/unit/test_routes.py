"""Testes unitários para rotas da API."""

import json
import uuid

import pytest
from moto import mock_aws

from backend.lambda_.api.routes import (
    cancel_download,
    create_download,
    delete_download,
    generate_upload_url,
    get_download,
    get_status,
    list_downloads,
    requeue_download,
    update_download,
)
from backend.lambda_.api.exceptions import BadRequestError, NotFoundError
from backend.lambda_.api.state_manager import StateManager
from tests.unit.conftest import BUCKET


@mock_aws
class TestCreateDownload:

    def setup_method(self):
        import boto3
        import backend.lambda_.api.routes as routes_mod
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket=BUCKET)
        routes_mod.state = StateManager(bucket=BUCKET)
        routes_mod.BUCKET = BUCKET
        routes_mod.WORKER_TRIGGER_FUNCTION = ""

    def test_create_magnet_download(self):
        body = {
            "clientRequestId": str(uuid.uuid4()),
            "type": "magnet",
            "magnetLink": "magnet:?xt=urn:btih:abc123",
            "name": "Test Download",
        }
        result, status_code = create_download(body)

        assert status_code == 201
        assert result["download"]["status"] == "pending"
        assert result["download"]["name"] == "Test Download"
        assert result["download"]["magnetLink"] == "magnet:?xt=urn:btih:abc123"

    def test_idempotent_create(self):
        client_id = str(uuid.uuid4())
        body = {
            "clientRequestId": client_id,
            "type": "magnet",
            "magnetLink": "magnet:?xt=urn:btih:abc123",
        }

        result1, code1 = create_download(body)
        result2, code2 = create_download(body)

        assert code1 == 201
        assert code2 == 200
        assert result1["download"]["id"] == result2["download"]["id"]

    def test_invalid_magnet_raises(self):
        body = {
            "clientRequestId": str(uuid.uuid4()),
            "type": "magnet",
            "magnetLink": "not-a-magnet",
        }
        with pytest.raises(Exception):
            create_download(body)


@mock_aws
class TestListAndGetDownloads:

    def setup_method(self):
        import boto3
        import backend.lambda_.api.routes as routes_mod
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket=BUCKET)
        routes_mod.state = StateManager(bucket=BUCKET)
        routes_mod.BUCKET = BUCKET
        routes_mod.WORKER_TRIGGER_FUNCTION = ""

    def _create_item(self, name="Test"):
        body = {
            "clientRequestId": str(uuid.uuid4()),
            "type": "magnet",
            "magnetLink": "magnet:?xt=urn:btih:abc",
            "name": name,
        }
        result, _ = create_download(body)
        return result["download"]

    def test_list_downloads_empty(self):
        result, code = list_downloads({})
        assert code == 200
        assert result["total"] == 0

    def test_list_downloads_with_items(self):
        self._create_item("A")
        self._create_item("B")
        result, code = list_downloads({})

        assert code == 200
        assert result["total"] == 2

    def test_list_downloads_filter_by_status(self):
        self._create_item()
        result, code = list_downloads({"status": "completed"})

        assert code == 200
        assert result["total"] == 0

    def test_get_download_found(self):
        item = self._create_item()
        result, code = get_download(item["id"])

        assert code == 200
        assert result["download"]["id"] == item["id"]

    def test_get_download_not_found(self):
        with pytest.raises(NotFoundError):
            get_download(str(uuid.uuid4()))


@mock_aws
class TestUpdateDeleteCancelRequeue:

    def setup_method(self):
        import boto3
        import backend.lambda_.api.routes as routes_mod
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket=BUCKET)
        self.sm = StateManager(bucket=BUCKET)
        routes_mod.state = self.sm
        routes_mod.BUCKET = BUCKET
        routes_mod.WORKER_TRIGGER_FUNCTION = ""

    def _create_item(self):
        body = {
            "clientRequestId": str(uuid.uuid4()),
            "type": "magnet",
            "magnetLink": "magnet:?xt=urn:btih:abc",
            "name": "Original",
        }
        result, _ = create_download(body)
        return result["download"]

    def test_update_name(self):
        item = self._create_item()
        result, code = update_download(item["id"], {"name": "New Name"})

        assert code == 200
        assert result["download"]["name"] == "New Name"

    def test_delete_download(self):
        item = self._create_item()
        _, code = delete_download(item["id"])

        assert code == 204
        with pytest.raises(NotFoundError):
            get_download(item["id"])

    def test_cancel_pending(self):
        item = self._create_item()
        result, code = cancel_download(item["id"])

        assert code == 200
        assert result["download"]["status"] == "cancelled"

    def test_cancel_completed_raises(self):
        item = self._create_item()
        self.sm.transition_state(item["id"], "pending", "processing", "i-abc", {})
        self.sm.transition_state(item["id"], "processing", "completed", "i-abc", {
            "completedAt": "2026-04-22T11:00:00Z"
        })

        with pytest.raises(BadRequestError):
            cancel_download(item["id"])

    def test_requeue_cancelled(self):
        item = self._create_item()
        self.sm.transition_state(item["id"], "pending", "cancelled", None, {
            "cancelledAt": "2026-04-22T11:00:00Z"
        })

        result, code = requeue_download(item["id"])
        assert code == 200
        assert result["download"]["status"] == "pending"
        assert result["download"]["retryCount"] == 0

    def test_requeue_non_cancelled_raises(self):
        item = self._create_item()
        with pytest.raises(BadRequestError, match="cancelled"):
            requeue_download(item["id"])


@mock_aws
class TestPresignedUrls:

    def setup_method(self):
        import boto3
        import backend.lambda_.api.routes as routes_mod
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket=BUCKET)
        routes_mod.state = StateManager(bucket=BUCKET)
        routes_mod.BUCKET = BUCKET
        routes_mod.WORKER_TRIGGER_FUNCTION = ""

    def test_generate_upload_url(self):
        result, code = generate_upload_url({"filename": "test.torrent", "sizeBytes": 5000})

        assert code == 200
        assert "uploadUrl" in result
        assert result["torrentS3Key"].endswith(".torrent")


@mock_aws
class TestGetStatus:

    def setup_method(self):
        import boto3
        import backend.lambda_.api.routes as routes_mod
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket=BUCKET)
        routes_mod.state = StateManager(bucket=BUCKET)
        routes_mod.BUCKET = BUCKET
        routes_mod.EC2_INSTANCE_ID = ""

    def test_status_empty(self):
        result, code = get_status()

        assert code == 200
        assert result["worker"]["status"] == "stopped"
        assert result["queue"]["pending"] == 0
