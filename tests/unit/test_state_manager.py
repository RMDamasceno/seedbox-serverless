"""Testes unitários para StateManager."""

import json

import pytest
from moto import mock_aws

from backend.lambda_.api.state_manager import (
    ItemNotFoundError,
    LockConflictError,
    StateManager,
    StateMismatchError,
)
from tests.unit.conftest import BUCKET, put_item_to_s3


@mock_aws
class TestStateManagerCRUD:
    """Testes de operações CRUD básicas."""

    def setup_method(self):
        import boto3
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket=BUCKET)
        self.sm = StateManager(bucket=BUCKET)

    def test_put_and_get_item(self, sample_item):
        # Arrange & Act
        self.sm.put_item(sample_item, "pending")
        item, etag = self.sm.get_item(sample_item["id"], "pending")

        # Assert
        assert item["id"] == sample_item["id"]
        assert item["status"] == "pending"
        assert etag is not None

    def test_get_item_not_found(self):
        # Act & Assert
        with pytest.raises(ItemNotFoundError):
            self.sm.get_item("nonexistent-id", "pending")

    def test_find_item_across_statuses(self, sample_item):
        # Arrange
        sample_item["status"] = "completed"
        self.sm.put_item(sample_item, "completed")

        # Act
        item, etag, status = self.sm.find_item(sample_item["id"])

        # Assert
        assert status == "completed"
        assert item["id"] == sample_item["id"]

    def test_find_item_not_found(self):
        # Act & Assert
        with pytest.raises(ItemNotFoundError):
            self.sm.find_item("nonexistent-id")

    def test_delete_item(self, sample_item):
        # Arrange
        self.sm.put_item(sample_item, "pending")

        # Act
        self.sm.delete_item(sample_item["id"], "pending")

        # Assert
        with pytest.raises(ItemNotFoundError):
            self.sm.get_item(sample_item["id"], "pending")

    def test_list_items(self, sample_item):
        # Arrange
        self.sm.put_item(sample_item, "pending")

        # Act
        items = self.sm.list_items("pending")

        # Assert
        assert len(items) == 1
        assert items[0]["id"] == sample_item["id"]

    def test_list_items_empty(self):
        # Act
        items = self.sm.list_items("pending")

        # Assert
        assert items == []

    def test_get_index_none_when_missing(self):
        # Act
        index = self.sm.get_index()

        # Assert
        assert index is None

    def test_update_index(self, sample_item):
        # Act
        self.sm.update_index(sample_item)
        index = self.sm.get_index()

        # Assert
        assert index is not None
        assert len(index["items"]) == 1
        assert index["items"][0]["id"] == sample_item["id"]
        assert index["updatedAt"] is not None


@mock_aws
class TestStateManagerTransition:
    """Testes de transição de estado com ETag."""

    def setup_method(self):
        import boto3
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket=BUCKET)
        self.sm = StateManager(bucket=BUCKET)

    def test_successful_transition_pending_to_processing(self, sample_item):
        # Arrange
        self.sm.put_item(sample_item, "pending")
        worker_id = "i-abc123"

        # Act
        result = self.sm.transition_state(
            sample_item["id"], "pending", "processing", worker_id, {"transmissionId": 42}
        )

        # Assert
        assert result is not None
        assert result["status"] == "processing"
        assert result["workerId"] == worker_id
        assert result["version"] == 2
        assert result["transmissionId"] == 42

        # Item não existe mais em pending
        with pytest.raises(ItemNotFoundError):
            self.sm.get_item(sample_item["id"], "pending")

        # Item existe em processing
        item, _ = self.sm.get_item(sample_item["id"], "processing")
        assert item["status"] == "processing"

    def test_transition_processing_to_completed(self, sample_item):
        # Arrange
        sample_item["status"] = "processing"
        sample_item["workerId"] = "i-abc123"
        self.sm.put_item(sample_item, "processing")

        # Act
        result = self.sm.transition_state(
            sample_item["id"], "processing", "completed", "i-abc123",
            {"completedAt": "2026-04-22T11:00:00Z", "progressPercent": 100.0}
        )

        # Assert
        assert result["status"] == "completed"
        assert result["workerId"] is None
        assert result["progressPercent"] == 100.0

    def test_lock_conflict_raises_error(self, sample_item):
        # Arrange
        sample_item["workerId"] = "i-other-worker"
        sample_item["status"] = "processing"
        self.sm.put_item(sample_item, "processing")

        # Act & Assert
        with pytest.raises(LockConflictError):
            self.sm.transition_state(
                sample_item["id"], "processing", "completed", "i-my-worker", {}
            )

    def test_state_mismatch_raises_error(self, sample_item):
        # Arrange
        sample_item["status"] = "completed"
        self.sm.put_item(sample_item, "pending")

        # Act & Assert
        with pytest.raises(StateMismatchError):
            self.sm.transition_state(
                sample_item["id"], "pending", "processing", "i-abc123", {}
            )

    def test_version_increments(self, sample_item):
        # Arrange
        sample_item["version"] = 5
        self.sm.put_item(sample_item, "pending")

        # Act
        result = self.sm.transition_state(
            sample_item["id"], "pending", "processing", "i-abc123", {}
        )

        # Assert
        assert result["version"] == 6

    def test_index_updated_after_transition(self, sample_item):
        # Arrange
        self.sm.put_item(sample_item, "pending")

        # Act
        self.sm.transition_state(
            sample_item["id"], "pending", "processing", "i-abc123", {}
        )
        index = self.sm.get_index()

        # Assert
        assert index is not None
        assert any(i["id"] == sample_item["id"] and i["status"] == "processing" for i in index["items"])

    def test_transition_not_found(self):
        # Act & Assert
        with pytest.raises(ItemNotFoundError):
            self.sm.transition_state("nonexistent", "pending", "processing", "i-abc", {})
