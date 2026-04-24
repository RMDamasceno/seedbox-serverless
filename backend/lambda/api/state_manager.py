"""
Gerenciador de estado dos downloads no S3.

Implementa operações CRUD e transição de estado atômica via protocolo
COPY → VALIDATE → DELETE com ETag condicional.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

BUCKET = os.environ.get("S3_BUCKET", "")
STATUSES = ("pending", "processing", "completed", "cancelled")


class LockConflictError(Exception):
    """Item está bloqueado por outro worker."""


class StateMismatchError(Exception):
    """Estado atual do item não corresponde ao esperado."""


class ItemNotFoundError(Exception):
    """Item não encontrado no S3."""


class StateManager:
    """Gerencia estado de downloads via arquivos JSON no S3."""

    def __init__(self, bucket: str | None = None):
        self.bucket = bucket or BUCKET
        self.s3 = boto3.client("s3")

    def _key(self, item_id: str, status: str) -> str:
        return f"queue/{status}/{item_id}.json"

    def get_item(self, item_id: str, status: str) -> tuple[dict, str]:
        """
        Obtém um item do S3 com seu ETag.

        Args:
            item_id: UUID do download.
            status: Estado atual (pending, processing, completed, cancelled).

        Returns:
            Tupla (item_dict, etag).

        Raises:
            ItemNotFoundError: Se o item não existe.
        """
        key = self._key(item_id, status)
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            item = json.loads(response["Body"].read())
            return item, response["ETag"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ItemNotFoundError(f"Item {item_id} not found in {status}")
            raise

    def find_item(self, item_id: str) -> tuple[dict, str, str]:
        """
        Busca um item em todos os prefixos de status.

        Args:
            item_id: UUID do download.

        Returns:
            Tupla (item_dict, etag, status).

        Raises:
            ItemNotFoundError: Se o item não existe em nenhum status.
        """
        for status in STATUSES:
            try:
                item, etag = self.get_item(item_id, status)
                return item, etag, status
            except ItemNotFoundError:
                continue
        raise ItemNotFoundError(f"Item {item_id} not found in any status")

    def put_item(self, item: dict, status: str) -> None:
        """
        Persiste um item no S3.

        Args:
            item: Dicionário com dados do download.
            status: Estado destino.
        """
        key = self._key(item["id"], status)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(item, default=str),
            ContentType="application/json",
        )
        logger.info("Item persisted", extra={"item_id": item["id"], "status": status})

    def delete_item(self, item_id: str, status: str) -> None:
        """
        Remove um item do S3.

        Args:
            item_id: UUID do download.
            status: Estado atual do item.
        """
        key = self._key(item_id, status)
        self.s3.delete_object(Bucket=self.bucket, Key=key)
        logger.info("Item deleted", extra={"item_id": item_id, "status": status})

    def list_items(self, status: str) -> list[dict]:
        """
        Lista todos os itens de um determinado status.

        Args:
            status: Estado a listar (pending, processing, completed, cancelled).

        Returns:
            Lista de dicionários com dados dos downloads.
        """
        prefix = f"queue/{status}/"
        items = []
        paginator = self.s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".json"):
                    try:
                        resp = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
                        items.append(json.loads(resp["Body"].read()))
                    except ClientError:
                        logger.warning("Failed to read item", extra={"key": obj["Key"]})
        return items

    def get_index(self) -> dict | None:
        """
        Obtém o index.json consolidado.

        Returns:
            Dicionário do índice ou None se não existe.
        """
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key="queue/index.json")
            return json.loads(resp["Body"].read())
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def update_index(self, updated_item: dict) -> None:
        """
        Atualiza o index.json com dados de um item modificado.

        Args:
            updated_item: Item que foi atualizado.
        """
        index = self.get_index() or {"updatedAt": None, "items": []}

        existing = [i for i in index["items"] if i["id"] != updated_item["id"]]

        if updated_item["status"] != "cancelled" or True:
            existing.append({
                "id": updated_item["id"],
                "name": updated_item.get("name", ""),
                "status": updated_item["status"],
                "progressPercent": updated_item.get("progressPercent", 0),
                "sizeBytes": updated_item.get("sizeBytes"),
                "updatedAt": updated_item.get("updatedAt"),
            })

        index["items"] = existing
        index["updatedAt"] = datetime.now(timezone.utc).isoformat()

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key="queue/index.json",
                Body=json.dumps(index, default=str),
                ContentType="application/json",
            )
        except ClientError:
            logger.warning("Failed to update index.json — item state is still correct")

    def transition_state(
        self,
        item_id: str,
        from_status: str,
        to_status: str,
        worker_id: str | None,
        updates: dict,
    ) -> dict | None:
        """
        Transiciona um item entre estados com atomicidade via ETag.

        Implementa o protocolo COPY → VALIDATE → DELETE para evitar
        race conditions em operações concorrentes no S3.

        Args:
            item_id: UUID do download.
            from_status: Estado atual esperado.
            to_status: Estado destino.
            worker_id: ID da instância EC2 processando (None para liberar lock).
            updates: Campos adicionais a atualizar.

        Returns:
            Item atualizado ou None se ETag mismatch (outro processo ganhou).

        Raises:
            LockConflictError: Se item está bloqueado por outro worker.
            StateMismatchError: Se estado atual não corresponde ao esperado.
            ItemNotFoundError: Se item não existe.
        """
        source_key = self._key(item_id, from_status)
        dest_key = self._key(item_id, to_status)

        # 1. GET com ETag
        item, etag = self.get_item(item_id, from_status)

        # 2. VALIDATE
        current_worker = item.get("workerId")
        if current_worker is not None and current_worker != worker_id:
            raise LockConflictError(
                f"Item {item_id} locked by {current_worker}, caller is {worker_id}"
            )
        if item.get("status") != from_status:
            raise StateMismatchError(
                f"Expected {from_status}, got {item.get('status')}"
            )

        # 3. Preparar novo estado
        item.update(updates)
        item["status"] = to_status
        item["workerId"] = worker_id if to_status == "processing" else None
        item["version"] = item.get("version", 0) + 1
        item["updatedAt"] = datetime.now(timezone.utc).isoformat()

        # 4. COPY condicional (atomicidade)
        try:
            self.s3.copy_object(
                Bucket=self.bucket,
                CopySource={"Bucket": self.bucket, "Key": source_key},
                Key=dest_key,
                CopySourceIfMatch=etag,
                MetadataDirective="REPLACE",
                Metadata={"status": to_status, "version": str(item["version"])},
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "PreconditionFailed":
                logger.warning("ETag mismatch — another process won the race",
                               extra={"item_id": item_id})
                return None
            raise

        # 5. PUT com JSON atualizado
        self.s3.put_object(
            Bucket=self.bucket,
            Key=dest_key,
            Body=json.dumps(item, default=str),
            ContentType="application/json",
        )

        # 6. DELETE fonte
        self.s3.delete_object(Bucket=self.bucket, Key=source_key)

        # 7. Atualizar index.json
        self.update_index(item)

        logger.info(
            "State transition completed",
            extra={
                "item_id": item_id,
                "from": from_status,
                "to": to_status,
                "version": item["version"],
            },
        )
        return item

    def delete_s3_prefix(self, prefix: str) -> None:
        """
        Remove todos os objetos sob um prefixo S3.

        Args:
            prefix: Prefixo S3 a limpar (ex: downloads/completed/{id}/).
        """
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects:
                self.s3.delete_objects(
                    Bucket=self.bucket, Delete={"Objects": objects}
                )

    def get_s3_prefix_size(self, prefix: str) -> int:
        """
        Calcula o tamanho total de objetos sob um prefixo.

        Args:
            prefix: Prefixo S3.

        Returns:
            Tamanho total em bytes.
        """
        total = 0
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                total += obj.get("Size", 0)
        return total
