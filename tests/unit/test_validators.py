"""Testes unitários para validadores Pydantic."""

import uuid

import pytest
from pydantic import ValidationError

from backend.lambda_.api.validators import (
    CreateDownloadRequest,
    DownloadUrlRequest,
    LoginRequest,
    UpdateDownloadRequest,
    UploadUrlRequest,
)


class TestCreateDownloadRequest:

    def test_valid_magnet(self):
        req = CreateDownloadRequest(
            clientRequestId=str(uuid.uuid4()),
            type="magnet",
            magnetLink="magnet:?xt=urn:btih:abc123",
        )
        assert req.type == "magnet"

    def test_valid_torrent_file(self):
        req = CreateDownloadRequest(
            clientRequestId=str(uuid.uuid4()),
            type="torrent_file",
            torrentS3Key="torrents/abc.torrent",
        )
        assert req.type == "torrent_file"

    def test_invalid_uuid(self):
        with pytest.raises(ValidationError, match="UUID v4"):
            CreateDownloadRequest(
                clientRequestId="not-a-uuid",
                type="magnet",
                magnetLink="magnet:?xt=urn:btih:abc",
            )

    def test_invalid_magnet_link(self):
        with pytest.raises(ValidationError, match="magnet"):
            CreateDownloadRequest(
                clientRequestId=str(uuid.uuid4()),
                type="magnet",
                magnetLink="http://not-a-magnet",
            )

    def test_magnet_type_without_link(self):
        with pytest.raises(ValueError, match="magnetLink is required"):
            CreateDownloadRequest(
                clientRequestId=str(uuid.uuid4()),
                type="magnet",
            )

    def test_torrent_type_without_key(self):
        with pytest.raises(ValueError, match="torrentS3Key is required"):
            CreateDownloadRequest(
                clientRequestId=str(uuid.uuid4()),
                type="torrent_file",
            )

    def test_invalid_torrent_key_extension(self):
        with pytest.raises(ValidationError, match=".torrent"):
            CreateDownloadRequest(
                clientRequestId=str(uuid.uuid4()),
                type="torrent_file",
                torrentS3Key="torrents/abc.zip",
            )

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            CreateDownloadRequest(
                clientRequestId=str(uuid.uuid4()),
                type="magnet",
                magnetLink="magnet:?xt=urn:btih:abc",
                name="x" * 256,
            )

    def test_name_within_limit(self):
        req = CreateDownloadRequest(
            clientRequestId=str(uuid.uuid4()),
            type="magnet",
            magnetLink="magnet:?xt=urn:btih:abc",
            name="x" * 255,
        )
        assert len(req.name) == 255

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            CreateDownloadRequest(
                clientRequestId=str(uuid.uuid4()),
                type="invalid",
                magnetLink="magnet:?xt=urn:btih:abc",
            )


class TestUpdateDownloadRequest:

    def test_valid_name(self):
        req = UpdateDownloadRequest(name="New Name")
        assert req.name == "New Name"

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            UpdateDownloadRequest(name="")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            UpdateDownloadRequest(name="x" * 256)


class TestUploadUrlRequest:

    def test_valid_torrent(self):
        req = UploadUrlRequest(filename="test.torrent", sizeBytes=45000)
        assert req.filename == "test.torrent"

    def test_invalid_extension(self):
        with pytest.raises(ValidationError, match=".torrent"):
            UploadUrlRequest(filename="test.zip", sizeBytes=45000)

    def test_size_too_large(self):
        with pytest.raises(ValidationError):
            UploadUrlRequest(filename="test.torrent", sizeBytes=1_048_577)

    def test_size_zero(self):
        with pytest.raises(ValidationError):
            UploadUrlRequest(filename="test.torrent", sizeBytes=0)

    def test_case_insensitive_extension(self):
        req = UploadUrlRequest(filename="TEST.TORRENT", sizeBytes=1000)
        assert req.filename == "TEST.TORRENT"


class TestDownloadUrlRequest:

    def test_default_expires(self):
        req = DownloadUrlRequest()
        assert req.expiresIn == 3600

    def test_custom_expires(self):
        req = DownloadUrlRequest(expiresIn=86400)
        assert req.expiresIn == 86400

    def test_max_expires(self):
        req = DownloadUrlRequest(expiresIn=604800)
        assert req.expiresIn == 604800

    def test_exceeds_max_expires(self):
        with pytest.raises(ValidationError):
            DownloadUrlRequest(expiresIn=604801)

    def test_zero_expires(self):
        with pytest.raises(ValidationError):
            DownloadUrlRequest(expiresIn=0)


class TestLoginRequest:

    def test_valid(self):
        req = LoginRequest(password="mypassword")
        assert req.password == "mypassword"

    def test_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="")
