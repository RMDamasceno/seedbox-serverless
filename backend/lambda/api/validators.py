"""Validadores Pydantic para requests da API."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class CreateDownloadRequest(BaseModel):
    clientRequestId: str = Field(..., description="UUID v4 para idempotência")
    type: Literal["magnet", "torrent_file"]
    magnetLink: str | None = Field(None, description="Magnet link")
    torrentS3Key: str | None = Field(None, description="Chave S3 do .torrent")
    name: str | None = Field(None, max_length=255)

    @field_validator("clientRequestId")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("clientRequestId must be a valid UUID v4")
        return v

    @field_validator("magnetLink")
    @classmethod
    def validate_magnet(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("magnet:?"):
            raise ValueError("magnetLink must start with 'magnet:?'")
        return v

    @field_validator("torrentS3Key")
    @classmethod
    def validate_torrent_key(cls, v: str | None) -> str | None:
        if v is not None and not v.endswith(".torrent"):
            raise ValueError("torrentS3Key must end with '.torrent'")
        return v

    def model_post_init(self, __context) -> None:
        if self.type == "magnet" and not self.magnetLink:
            raise ValueError("magnetLink is required when type is 'magnet'")
        if self.type == "torrent_file" and not self.torrentS3Key:
            raise ValueError("torrentS3Key is required when type is 'torrent_file'")


class UpdateDownloadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class UploadUrlRequest(BaseModel):
    filename: str
    sizeBytes: int = Field(..., gt=0, le=1_048_576)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v.lower().endswith(".torrent"):
            raise ValueError("filename must end with '.torrent'")
        return v


class DownloadUrlRequest(BaseModel):
    expiresIn: int = Field(default=3600, gt=0, le=604_800)
