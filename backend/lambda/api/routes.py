"""Rotas da API — CRUD de downloads, pre-signed URLs e status."""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .auth import login
from .exceptions import BadRequestError, ConflictError, NotFoundError
from .state_manager import ItemNotFoundError, StateManager
from .validators import (
    CreateDownloadRequest,
    DownloadUrlRequest,
    LoginRequest,
    UpdateDownloadRequest,
    UploadUrlRequest,
)

logger = logging.getLogger(__name__)

state = StateManager()
s3_presign = boto3.client("s3", config=Config(signature_version="s3v4"))
ec2 = boto3.client("ec2")
lambda_client = boto3.client("lambda")

BUCKET = os.environ.get("S3_BUCKET", "")
EC2_INSTANCE_ID = os.environ.get("EC2_INSTANCE_ID", "")
WORKER_TRIGGER_FUNCTION = os.environ.get("WORKER_TRIGGER_FUNCTION", "")

# Transições permitidas por status
ALLOWED_TRANSITIONS = {
    "pending": {"cancelled"},
    "processing": {"completed", "cancelled", "pending"},
    "completed": set(),
    "cancelled": {"pending"},
}


# ─── POST /auth/login ───


def handle_login(body: dict) -> tuple[dict, int]:
    """
    Autentica usuário e retorna JWT.

    Args:
        body: Dict com campo password.

    Returns:
        Tupla (response_body, status_code).
    """
    req = LoginRequest(**body)
    try:
        result = login(req.password)
        return result, 200
    except ValueError:
        raise BadRequestError("invalid_credentials")


# ─── POST /downloads ───


def create_download(body: dict) -> tuple[dict, int]:
    """
    Cria novo download com idempotência via clientRequestId.

    Args:
        body: Dict com clientRequestId, type, magnetLink/torrentS3Key, name.

    Returns:
        Tupla (response_body, status_code). 201 se criado, 200 se já existia.
    """
    req = CreateDownloadRequest(**body)
    idempotency_key = f"idempotency/{req.clientRequestId}"

    # Verificar idempotência
    try:
        resp = state.s3.get_object(Bucket=BUCKET, Key=idempotency_key)
        existing = json.loads(resp["Body"].read())
        item, _, _ = state.find_item(existing["itemId"])
        return {"download": item}, 200
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchKey":
            raise
    except ItemNotFoundError:
        pass

    # Criar item
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": str(uuid.uuid4()),
        "clientRequestId": req.clientRequestId,
        "name": req.name or "",
        "status": "pending",
        "type": req.type,
        "magnetLink": req.magnetLink,
        "torrentS3Key": req.torrentS3Key,
        "transmissionId": None,
        "sizeBytes": None,
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
        "createdAt": now,
        "updatedAt": now,
        "startedAt": None,
        "completedAt": None,
        "cancelledAt": None,
        "s3Key": None,
        "s3SizeBytes": None,
    }

    state.put_item(item, "pending")

    # Registrar idempotência
    state.s3.put_object(
        Bucket=BUCKET,
        Key=idempotency_key,
        Body=json.dumps({"itemId": item["id"], "createdAt": now}),
        ContentType="application/json",
    )

    state.update_index(item)
    _trigger_worker_if_stopped()

    return {"download": item}, 201


# ─── GET /downloads ───


def list_downloads(params: dict) -> tuple[dict, int]:
    """
    Lista downloads com filtro por status e paginação.

    Args:
        params: Query params (status, page, limit).

    Returns:
        Tupla (response_body, status_code).
    """
    status_filter = params.get("status")
    page = int(params.get("page", 1))
    limit = int(params.get("limit", 50))

    index = state.get_index()
    if index:
        items = index.get("items", [])
    else:
        items = []
        for s in ("pending", "processing", "completed", "cancelled"):
            items.extend(
                {"id": i["id"], "name": i.get("name", ""), "status": i["status"],
                 "progressPercent": i.get("progressPercent", 0),
                 "sizeBytes": i.get("sizeBytes"), "updatedAt": i.get("updatedAt")}
                for i in state.list_items(s)
            )

    if status_filter:
        items = [i for i in items if i["status"] == status_filter]

    total = len(items)
    start = (page - 1) * limit
    paged = items[start : start + limit]

    return {"items": paged, "total": total, "page": page}, 200


# ─── GET /downloads/{id} ───


def get_download(item_id: str) -> tuple[dict, int]:
    """
    Obtém detalhes de um download.

    Args:
        item_id: UUID do download.

    Returns:
        Tupla (response_body, status_code).

    Raises:
        NotFoundError: Se item não existe.
    """
    try:
        item, _, _ = state.find_item(item_id)
        return {"download": item}, 200
    except ItemNotFoundError:
        raise NotFoundError()


# ─── PATCH /downloads/{id} ───


def update_download(item_id: str, body: dict) -> tuple[dict, int]:
    """
    Edita o nome de um download (único campo editável).

    Args:
        item_id: UUID do download.
        body: Dict com campo name.

    Returns:
        Tupla (response_body, status_code).
    """
    req = UpdateDownloadRequest(**body)

    try:
        item, etag, status = state.find_item(item_id)
    except ItemNotFoundError:
        raise NotFoundError()

    item["name"] = req.name
    item["updatedAt"] = datetime.now(timezone.utc).isoformat()
    item["version"] = item.get("version", 0) + 1

    state.put_item(item, status)
    state.update_index(item)

    return {"download": item}, 200


# ─── DELETE /downloads/{id} ───


def delete_download(item_id: str) -> tuple[None, int]:
    """
    Remove permanentemente um download e seus arquivos.

    Args:
        item_id: UUID do download.

    Returns:
        Tupla (None, 204).
    """
    try:
        item, _, status = state.find_item(item_id)
    except ItemNotFoundError:
        raise NotFoundError()

    # Remover arquivo S3 se completed
    if status == "completed" and item.get("s3Key"):
        state.delete_s3_prefix(item["s3Key"])

    state.delete_item(item_id, status)

    # Remover do index
    index = state.get_index()
    if index:
        index["items"] = [i for i in index["items"] if i["id"] != item_id]
        index["updatedAt"] = datetime.now(timezone.utc).isoformat()
        state.s3.put_object(
            Bucket=BUCKET,
            Key="queue/index.json",
            Body=json.dumps(index, default=str),
            ContentType="application/json",
        )

    return None, 204


# ─── POST /downloads/{id}/cancel ───


def cancel_download(item_id: str) -> tuple[dict, int]:
    """
    Cancela um download. Se processing, seta flag cancelRequested.

    Args:
        item_id: UUID do download.

    Returns:
        Tupla (response_body, status_code).
    """
    try:
        item, _, status = state.find_item(item_id)
    except ItemNotFoundError:
        raise NotFoundError()

    if status not in ("pending", "processing"):
        raise BadRequestError(f"Cannot cancel download in status '{status}'")

    now = datetime.now(timezone.utc).isoformat()

    if status == "pending":
        result = state.transition_state(item_id, "pending", "cancelled", None, {
            "cancelledAt": now,
        })
    else:
        # Processing: setar flag para worker detectar
        item["cancelRequested"] = True
        item["updatedAt"] = now
        item["version"] = item.get("version", 0) + 1
        state.put_item(item, "processing")
        state.update_index(item)
        result = item

    if result is None:
        raise ConflictError("State changed concurrently, retry")

    return {"download": result}, 200


# ─── POST /downloads/{id}/requeue ───


def requeue_download(item_id: str) -> tuple[dict, int]:
    """
    Recoloca um download cancelado na fila.

    Args:
        item_id: UUID do download.

    Returns:
        Tupla (response_body, status_code).
    """
    try:
        item, _, status = state.find_item(item_id)
    except ItemNotFoundError:
        raise NotFoundError()

    if status != "cancelled":
        raise BadRequestError("Only cancelled downloads can be requeued")

    result = state.transition_state(item_id, "cancelled", "pending", None, {
        "retryCount": 0,
        "retryAfter": None,
        "errorMessage": None,
        "cancelledAt": None,
        "cancelRequested": False,
        "progressPercent": 0.0,
        "sizeBytesDownloaded": 0,
    })

    if result is None:
        raise ConflictError("State changed concurrently, retry")

    _trigger_worker_if_stopped()

    return {"download": result}, 200


# ─── POST /downloads/upload-url ───


def generate_upload_url(body: dict) -> tuple[dict, int]:
    """
    Gera Pre-signed PUT URL para upload de arquivo .torrent.

    Args:
        body: Dict com filename e sizeBytes.

    Returns:
        Tupla (response_body, status_code).
    """
    req = UploadUrlRequest(**body)
    torrent_id = str(uuid.uuid4())
    s3_key = f"torrents/{torrent_id}.torrent"

    url = s3_presign.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET,
            "Key": s3_key,
            "ContentType": "application/x-bittorrent",
        },
        ExpiresIn=300,
    )

    return {"uploadUrl": url, "torrentS3Key": s3_key}, 200


# ─── POST /downloads/{id}/download-url ───


def generate_download_url(item_id: str, body: dict) -> tuple[dict, int]:
    """
    Gera Pre-signed GET URL para download de arquivo concluído.

    Args:
        item_id: UUID do download.
        body: Dict com expiresIn.

    Returns:
        Tupla (response_body, status_code).
    """
    req = DownloadUrlRequest(**body)

    try:
        item, _, status = state.find_item(item_id)
    except ItemNotFoundError:
        raise NotFoundError()

    if status != "completed":
        raise BadRequestError("download_not_completed")

    s3_key = item.get("s3Key")
    if not s3_key:
        raise BadRequestError("download_not_completed")

    url = s3_presign.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET,
            "Key": s3_key,
            "ResponseContentDisposition": f'attachment; filename="{item.get("name", "download")}"',
        },
        ExpiresIn=req.expiresIn,
    )

    size_bytes = item.get("s3SizeBytes", 0) or 0
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=req.expiresIn)

    return {
        "url": url,
        "filename": item.get("name", ""),
        "sizeBytes": size_bytes,
        "expiresAt": expires_at.isoformat(),
        "estimatedTransferCostUSD": round((size_bytes / 1e9) * 0.09, 4),
    }, 200


# ─── GET /status ───


def get_status() -> tuple[dict, int]:
    """
    Retorna status da infraestrutura e contadores de fila.

    Returns:
        Tupla (response_body, status_code).
    """
    # Status do worker
    worker = {"status": "stopped", "instanceId": None, "instanceType": None,
              "launchedAt": None, "uptimeSeconds": 0}

    if EC2_INSTANCE_ID:
        try:
            resp = ec2.describe_instances(InstanceIds=[EC2_INSTANCE_ID])
            reservations = resp.get("Reservations", [])
            if reservations and reservations[0].get("Instances"):
                inst = reservations[0]["Instances"][0]
                ec2_state = inst["State"]["Name"]
                worker["status"] = ec2_state
                worker["instanceId"] = EC2_INSTANCE_ID
                worker["instanceType"] = inst.get("InstanceType")
                launch_time = inst.get("LaunchTime")
                if launch_time:
                    worker["launchedAt"] = launch_time.isoformat()
                    if ec2_state == "running":
                        delta = datetime.now(timezone.utc) - launch_time.replace(tzinfo=timezone.utc)
                        worker["uptimeSeconds"] = int(delta.total_seconds())
        except ClientError:
            logger.warning("Failed to describe EC2 instance")

    # Contadores de fila
    index = state.get_index()
    queue = {"pending": 0, "processing": 0, "completed": 0, "cancelled": 0}
    index_info = {"updatedAt": None, "isStale": False}

    if index:
        for item in index.get("items", []):
            s = item.get("status")
            if s in queue:
                queue[s] += 1
        index_info["updatedAt"] = index.get("updatedAt")
        if index_info["updatedAt"]:
            try:
                updated = datetime.fromisoformat(index_info["updatedAt"].replace("Z", "+00:00"))
                stale_seconds = (datetime.now(timezone.utc) - updated).total_seconds()
                index_info["isStale"] = stale_seconds > 120
            except (ValueError, TypeError):
                index_info["isStale"] = True

    return {"worker": worker, "queue": queue, "index": index_info}, 200


# ─── Helpers ───


def _trigger_worker_if_stopped() -> None:
    """Invoca Lambda worker-trigger assincronamente se EC2 está parada."""
    if not WORKER_TRIGGER_FUNCTION:
        return
    try:
        lambda_client.invoke(
            FunctionName=WORKER_TRIGGER_FUNCTION,
            InvocationType="Event",
            Payload=json.dumps({"action": "start"}),
        )
    except ClientError:
        logger.warning("Failed to invoke worker trigger")
