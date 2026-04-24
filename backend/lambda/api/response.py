"""Helpers para formatar HTTP responses."""

import json
import os

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


def success(body: dict, status_code: int = 200) -> dict:
    return {
        "statusCode": status_code,
        "headers": _headers(),
        "body": json.dumps(body, default=str),
    }


def error(message: str, status_code: int = 500) -> dict:
    return {
        "statusCode": status_code,
        "headers": _headers(),
        "body": json.dumps({"error": message}),
    }


def no_content() -> dict:
    return {"statusCode": 204, "headers": _headers()}


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
    }
