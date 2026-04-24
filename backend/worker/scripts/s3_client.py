"""Cliente S3 do worker para operações de estado dos downloads."""

import json
import logging
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

PROGRESS_MIN_DELTA_PERCENT = 2.0
PROGRESS_MAX_INTERVAL_SECONDS = 30


class WorkerS3Client:
    """Gerencia estado dos downloads no S3 a partir do worker EC2."""

    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3 = boto3.client("s3")
        self._last_progress_update = 0.0
        self._last_progress_value = 0.0

    def get_next_pending_item(self) -> dict | None:
        """
        Busca o próximo item pendente disponível para processamento.

        Filtra itens cujo retryAfter já passou.

        Returns:
            Dict do item ou None se não há itens disponíveis.
        """
        prefix = "queue/pending/"
        now = datetime.now(timezone.utc)

        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    if not obj["Key"].endswith(".json"):
                        continue
                    try:
                        resp = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
                        item = json.loads(resp["Body"].read())

                        retry_after = item.get("retryAfter")
                        if retry_after:
                            retry_dt = datetime.fromisoformat(retry_after.replace("Z", "+00:00"))
                            if now < retry_dt:
                                continue

                        return item
                    except (ClientError, json.JSONDecodeError):
                        continue
        except ClientError:
            logger.warning("Failed to list pending items")
        return None

    def acquire_lock(self, item_id: str, worker_id: str) -> dict | None:
        """
        Adquire lock atômico via ETag para transição pending → processing.

        Args:
            item_id: UUID do download.
            worker_id: ID da instância EC2.

        Returns:
            Item atualizado ou None se outro worker ganhou a corrida.
        """
        source_key = f"queue/pending/{item_id}.json"
        dest_key = f"queue/processing/{item_id}.json"

        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=source_key)
            etag = resp["ETag"]
            item = json.loads(resp["Body"].read())
        except ClientError:
            return None

        if item.get("workerId") is not None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        item["status"] = "processing"
        item["workerId"] = worker_id
        item["startedAt"] = now
        item["updatedAt"] = now
        item["version"] = item.get("version", 0) + 1

        try:
            self.s3.copy_object(
                Bucket=self.bucket,
                CopySource={"Bucket": self.bucket, "Key": source_key},
                Key=dest_key,
                CopySourceIfMatch=etag,
                MetadataDirective="REPLACE",
                Metadata={"status": "processing"},
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "PreconditionFailed":
                logger.info("Lock race lost for %s", item_id)
                return None
            raise

        self.s3.put_object(
            Bucket=self.bucket, Key=dest_key,
            Body=json.dumps(item, default=str), ContentType="application/json",
        )
        self.s3.delete_object(Bucket=self.bucket, Key=source_key)
        self._update_index(item)

        logger.info("Lock acquired for %s", item_id)
        return item

    def update_progress(self, item_id: str, fields: dict) -> None:
        """
        Atualiza campos de progresso no S3 com throttle.

        Só faz PUT se delta de progresso > 2% ou > 30s desde última atualização.

        Args:
            item_id: UUID do download.
            fields: Dict com campos de progresso (progressPercent, speeds, eta, etc).
        """
        now = time.time()
        progress = fields.get("progressPercent", 0)
        delta = abs(progress - self._last_progress_value)
        elapsed = now - self._last_progress_update

        if delta < PROGRESS_MIN_DELTA_PERCENT and elapsed < PROGRESS_MAX_INTERVAL_SECONDS:
            return

        key = f"queue/processing/{item_id}.json"
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            item = json.loads(resp["Body"].read())
            item.update(fields)
            item["updatedAt"] = datetime.now(timezone.utc).isoformat()

            self.s3.put_object(
                Bucket=self.bucket, Key=key,
                Body=json.dumps(item, default=str), ContentType="application/json",
            )
            self._update_index(item)
            self._last_progress_update = now
            self._last_progress_value = progress
        except ClientError:
            logger.warning("Failed to update progress for %s", item_id)

    def complete_item(self, item_id: str, worker_id: str, s3_key: str, s3_size: int) -> dict | None:
        """
        Transiciona item de processing → completed.

        Args:
            item_id: UUID do download.
            worker_id: ID da instância EC2.
            s3_key: Chave S3 do arquivo concluído.
            s3_size: Tamanho total em bytes.

        Returns:
            Item atualizado ou None se falhou.
        """
        return self._transition(item_id, "processing", "completed", worker_id, {
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "progressPercent": 100.0,
            "s3Key": s3_key,
            "s3SizeBytes": s3_size,
            "errorMessage": None,
            "workerId": None,
        })

    def fail_item(self, item_id: str, worker_id: str, to_status: str, updates: dict) -> dict | None:
        """
        Move item para cancelled ou pending (retry).

        Args:
            item_id: UUID do download.
            worker_id: ID da instância EC2.
            to_status: Estado destino (cancelled ou pending).
            updates: Campos adicionais.

        Returns:
            Item atualizado ou None se falhou.
        """
        return self._transition(item_id, "processing", to_status, worker_id, updates)

    def check_cancel_requested(self, item_id: str) -> bool:
        """
        Verifica se o usuário solicitou cancelamento.

        Args:
            item_id: UUID do download.

        Returns:
            True se cancelRequested está setado.
        """
        key = f"queue/processing/{item_id}.json"
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            item = json.loads(resp["Body"].read())
            return bool(item.get("cancelRequested"))
        except ClientError:
            return False

    def move_processing_to_pending(self, worker_id: str) -> None:
        """
        Move todos os itens processing deste worker de volta para pending.

        Usado durante graceful shutdown.

        Args:
            worker_id: ID da instância EC2.
        """
        prefix = "queue/processing/"
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    if not obj["Key"].endswith(".json"):
                        continue
                    try:
                        resp = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
                        item = json.loads(resp["Body"].read())
                        if item.get("workerId") == worker_id:
                            item_id = item["id"]
                            self._transition(item_id, "processing", "pending", worker_id, {
                                "workerId": None,
                                "errorMessage": "worker_shutdown",
                            })
                            logger.info("Moved %s back to pending", item_id)
                    except (ClientError, json.JSONDecodeError):
                        continue
        except ClientError:
            logger.error("Failed to move processing items to pending")

    def _transition(self, item_id: str, from_status: str, to_status: str,
                    worker_id: str, updates: dict) -> dict | None:
        """Transição de estado genérica com ETag."""
        source_key = f"queue/{from_status}/{item_id}.json"
        dest_key = f"queue/{to_status}/{item_id}.json"

        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=source_key)
            etag = resp["ETag"]
            item = json.loads(resp["Body"].read())
        except ClientError:
            return None

        item.update(updates)
        item["status"] = to_status
        if to_status != "processing":
            item["workerId"] = None
        item["version"] = item.get("version", 0) + 1
        item["updatedAt"] = datetime.now(timezone.utc).isoformat()

        try:
            self.s3.copy_object(
                Bucket=self.bucket,
                CopySource={"Bucket": self.bucket, "Key": source_key},
                Key=dest_key, CopySourceIfMatch=etag,
                MetadataDirective="REPLACE",
                Metadata={"status": to_status},
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "PreconditionFailed":
                return None
            raise

        self.s3.put_object(
            Bucket=self.bucket, Key=dest_key,
            Body=json.dumps(item, default=str), ContentType="application/json",
        )
        self.s3.delete_object(Bucket=self.bucket, Key=source_key)
        self._update_index(item)
        return item

    def _update_index(self, item: dict) -> None:
        """Atualiza index.json com dados do item."""
        try:
            try:
                resp = self.s3.get_object(Bucket=self.bucket, Key="queue/index.json")
                index = json.loads(resp["Body"].read())
            except ClientError:
                index = {"updatedAt": None, "items": []}

            index["items"] = [i for i in index["items"] if i["id"] != item["id"]]
            index["items"].append({
                "id": item["id"],
                "name": item.get("name", ""),
                "status": item["status"],
                "progressPercent": item.get("progressPercent", 0),
                "sizeBytes": item.get("sizeBytes"),
                "updatedAt": item.get("updatedAt"),
            })
            index["updatedAt"] = datetime.now(timezone.utc).isoformat()

            self.s3.put_object(
                Bucket=self.bucket, Key="queue/index.json",
                Body=json.dumps(index, default=str), ContentType="application/json",
            )
        except ClientError:
            logger.warning("Failed to update index.json")
