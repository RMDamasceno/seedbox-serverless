"""Testes unitários para autenticação JWT."""

import json
from unittest.mock import patch

import bcrypt
import jwt
import pytest

from backend.lambda_.api.auth import login, verify_token


MOCK_PASSWORD = "test-password-123"
MOCK_HASH = bcrypt.hashpw(MOCK_PASSWORD.encode(), bcrypt.gensalt()).decode()
MOCK_JWT_SECRET = "test-jwt-secret-key-for-testing"
MOCK_SECRET = {"passwordHash": MOCK_HASH, "jwtSecret": MOCK_JWT_SECRET}


@pytest.fixture(autouse=True)
def _reset_cache():
    import backend.lambda_.api.auth as auth_module
    auth_module._cached_secret = None
    yield
    auth_module._cached_secret = None


@pytest.fixture
def mock_secrets_manager():
    with patch("backend.lambda_.api.auth.boto3") as mock_boto:
        client = mock_boto.client.return_value
        client.get_secret_value.return_value = {
            "SecretString": json.dumps(MOCK_SECRET)
        }
        yield client


class TestLogin:

    def test_valid_password_returns_token(self, mock_secrets_manager):
        result = login(MOCK_PASSWORD)

        assert "token" in result
        assert "expiresAt" in result
        payload = jwt.decode(result["token"], MOCK_JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "seedbox-owner"
        assert "jti" in payload

    def test_invalid_password_raises(self, mock_secrets_manager):
        with pytest.raises(ValueError, match="invalid_credentials"):
            login("wrong-password")

    def test_token_has_required_claims(self, mock_secrets_manager):
        result = login(MOCK_PASSWORD)
        payload = jwt.decode(result["token"], MOCK_JWT_SECRET, algorithms=["HS256"])

        assert "sub" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload


class TestVerifyToken:

    def test_valid_token(self, mock_secrets_manager):
        result = login(MOCK_PASSWORD)
        payload = verify_token(result["token"])

        assert payload["sub"] == "seedbox-owner"

    def test_expired_token(self, mock_secrets_manager):
        expired = jwt.encode(
            {"sub": "seedbox-owner", "iat": 0, "exp": 1, "jti": "test"},
            MOCK_JWT_SECRET, algorithm="HS256",
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_token(expired)

    def test_invalid_signature(self, mock_secrets_manager):
        bad_token = jwt.encode(
            {"sub": "seedbox-owner", "iat": 0, "exp": 9999999999, "jti": "test"},
            "wrong-secret", algorithm="HS256",
        )
        with pytest.raises(jwt.InvalidTokenError):
            verify_token(bad_token)

    def test_missing_claims(self, mock_secrets_manager):
        incomplete = jwt.encode(
            {"sub": "seedbox-owner"},
            MOCK_JWT_SECRET, algorithm="HS256",
        )
        with pytest.raises(jwt.InvalidTokenError):
            verify_token(incomplete)
