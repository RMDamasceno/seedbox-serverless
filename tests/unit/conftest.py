"""Fixtures compartilhadas para testes unitários."""

import json
import os
import uuid

import boto3
import pytest
from moto import mock_aws

BUCKET = "seedbox-test-bucket"


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", BUCKET)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture
def s3_mock():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        yield s3


@pytest.fixture
def sample_item():
    return {
        "id": str(uuid.uuid4()),
        "clientRequestId": str(uuid.uuid4()),
        "name": "test-download",
        "status": "pending",
        "type": "magnet",
        "magnetLink": "magnet:?xt=urn:btih:abc123",
        "torrentS3Key": None,
        "transmissionId": None,
        "sizeBytes": 1073741824,
        "sizeBytesDownloaded": 0,
        "progressPercent": 0.0,
        "downloadSpeedBps": 0,
        "uploadSpeedBps": 0,
        "eta": None,
        "errorMessage": None,
        "retryCount": 0,
        "retryAfter": None,
        "workerId": None,
        "version": 1,
        "createdAt": "2026-04-22T10:00:00Z",
        "updatedAt": "2026-04-22T10:00:00Z",
        "startedAt": None,
        "completedAt": None,
        "cancelledAt": None,
        "s3Key": None,
        "s3SizeBytes": None,
    }


def put_item_to_s3(s3, item, status="pending"):
    key = f"queue/{status}/{item['id']}.json"
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(item), ContentType="application/json")
