"""Handler principal da Lambda API — roteamento por método+path."""

import json
import logging
import re

from .exceptions import ApiError, BadRequestError, NotFoundError, UnauthorizedError
from .response import error, no_content, success
from .routes import (
    cancel_download,
    create_download,
    delete_download,
    generate_download_url,
    generate_upload_url,
    get_download,
    get_status,
    handle_login,
    list_downloads,
    requeue_download,
    update_download,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Regex para extrair {id} das rotas
ID_PATTERN = re.compile(
    r"^/downloads/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)


def handler(event, context):
    """
    Handler principal — extrai método e path do event (API Gateway HTTP API
    format 2.0) e despacha para a função correta.
    """
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    method = http.get("method", event.get("httpMethod", "GET")).upper()
    path = http.get("path", event.get("rawPath", "/"))

    logger.info("Request: %s %s", method, path)

    try:
        body = _parse_body(event)
        params = event.get("queryStringParameters") or {}
        result, status_code = _route(method, path, body, params)

        if result is None:
            return no_content()
        return success(result, status_code)

    except ApiError as e:
        return error(e.message, e.status_code)
    except (ValueError, TypeError) as e:
        return error(str(e), 400)
    except Exception:
        logger.exception("Unhandled error")
        return error("internal_server_error", 500)


def _route(method: str, path: str, body: dict, params: dict) -> tuple:
    """Despacha request para a função correta baseado em método+path."""

    # POST /auth/login
    if method == "POST" and path == "/auth/login":
        return handle_login(body)

    # GET /status
    if method == "GET" and path == "/status":
        return get_status()

    # POST /downloads/upload-url
    if method == "POST" and path == "/downloads/upload-url":
        return generate_upload_url(body)

    # POST /downloads
    if method == "POST" and path == "/downloads":
        return create_download(body)

    # GET /downloads
    if method == "GET" and path == "/downloads":
        return list_downloads(params)

    # Rotas com {id}
    match = ID_PATTERN.match(path)
    if match:
        item_id = match.group(1)
        suffix = path[match.end():]

        if method == "GET" and suffix == "":
            return get_download(item_id)
        if method == "PATCH" and suffix == "":
            return update_download(item_id, body)
        if method == "DELETE" and suffix == "":
            return delete_download(item_id)
        if method == "POST" and suffix == "/cancel":
            return cancel_download(item_id)
        if method == "POST" and suffix == "/requeue":
            return requeue_download(item_id)
        if method == "POST" and suffix == "/download-url":
            return generate_download_url(item_id, body)

    raise NotFoundError(f"Route not found: {method} {path}")


def _parse_body(event: dict) -> dict:
    """Extrai e parseia o body JSON do event."""
    body = event.get("body")
    if not body:
        return {}
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise BadRequestError("Invalid JSON body")
    return body
