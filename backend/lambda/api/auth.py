"""Autenticação JWT com bcrypt e AWS Secrets Manager."""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import boto3
import jwt
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

AUTH_SECRET_NAME = os.environ.get("AUTH_SECRET_NAME", "seedbox/auth")

# Cache do secret em memória (reutilizado entre invocações Lambda)
_cached_secret: dict | None = None


def _get_auth_secret() -> dict:
    """
    Busca o secret de autenticação do Secrets Manager com cache em memória.

    Returns:
        Dict com passwordHash e jwtSecret.

    Raises:
        ClientError: Se falha ao acessar Secrets Manager.
    """
    global _cached_secret
    if _cached_secret is not None:
        return _cached_secret

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=AUTH_SECRET_NAME)
    _cached_secret = json.loads(response["SecretString"])
    return _cached_secret


def login(password: str) -> dict:
    """
    Valida senha e gera JWT.

    Args:
        password: Senha fornecida pelo usuário.

    Returns:
        Dict com token JWT e expiresAt.

    Raises:
        ValueError: Se senha inválida.
    """
    secret = _get_auth_secret()

    if not bcrypt.checkpw(password.encode(), secret["passwordHash"].encode()):
        raise ValueError("invalid_credentials")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=24)

    payload = {
        "sub": "seedbox-owner",
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }

    token = jwt.encode(payload, secret["jwtSecret"], algorithm="HS256")

    return {"token": token, "expiresAt": exp.isoformat()}


def verify_token(token: str) -> dict:
    """
    Decodifica e valida um JWT.

    Args:
        token: Token JWT.

    Returns:
        Payload decodificado.

    Raises:
        jwt.ExpiredSignatureError: Se token expirado.
        jwt.InvalidTokenError: Se token inválido.
    """
    secret = _get_auth_secret()
    return jwt.decode(
        token,
        secret["jwtSecret"],
        algorithms=["HS256"],
        options={"require": ["sub", "iat", "exp", "jti"]},
    )
