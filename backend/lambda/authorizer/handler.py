"""Lambda Authorizer — valida JWT e retorna policy Allow/Deny."""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
import jwt
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

AUTH_SECRET_NAME = os.environ.get("AUTH_SECRET_NAME", "seedbox/auth")
_cached_secret: dict | None = None


def _get_jwt_secret() -> str:
    global _cached_secret
    if _cached_secret is None:
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=AUTH_SECRET_NAME)
        _cached_secret = json.loads(response["SecretString"])
    return _cached_secret["jwtSecret"]


def handler(event, context):
    """
    Lambda Authorizer para API Gateway HTTP API (payload format 2.0).

    Extrai Bearer token do header Authorization, valida JWT e retorna
    simple response (isAuthorized: true/false).
    """
    token = _extract_token(event)
    if not token:
        logger.warning("Missing or malformed Authorization header")
        return {"isAuthorized": False}

    try:
        jwt_secret = _get_jwt_secret()
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp", "jti"]},
        )
        logger.info("Auth success", extra={"sub": payload.get("sub")})
        return {"isAuthorized": True, "context": {"sub": payload["sub"]}}

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return {"isAuthorized": False}
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", type(e).__name__)
        return {"isAuthorized": False}


def _extract_token(event: dict) -> str | None:
    headers = event.get("headers", {})
    auth = headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None
