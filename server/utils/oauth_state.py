import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

SIGNED_STATE_PREFIX = "gmv2"
SIGNED_STATE_KEY_PREFIX = "github:oauth:state"
DEFAULT_LARK_BIND_TTL_SECONDS = 24 * 60 * 60


def _b64_encode(content: bytes) -> str:
    return base64.urlsafe_b64encode(content).decode("utf-8").rstrip("=")


def _b64_decode(content: str) -> bytes:
    padding = "=" * ((4 - len(content) % 4) % 4)
    return base64.urlsafe_b64decode((content + padding).encode("utf-8"))


def _get_oauth_state_secret() -> bytes | None:
    secret = (
        os.environ.get("OAUTH_STATE_SECRET")
        or os.environ.get("SECRET_KEY")
        or os.environ.get("GITHUB_CLIENT_SECRET")
    )
    if not secret:
        return None
    return secret.encode("utf-8")


def _get_signed_state_storage_key(jti: str) -> str:
    return f"{SIGNED_STATE_KEY_PREFIX}:{jti}"


def _get_redis_client():
    from utils.redis import get_client

    return get_client(decode_responses=True)


def _resolve_lark_bind_ttl(ttl_seconds: int | None = None) -> int:
    if ttl_seconds and ttl_seconds > 0:
        return ttl_seconds

    try:
        ttl_from_env = int(
            os.environ.get("LARK_BIND_LINK_TTL_SECONDS", DEFAULT_LARK_BIND_TTL_SECONDS)
        )
        return ttl_from_env if ttl_from_env > 0 else DEFAULT_LARK_BIND_TTL_SECONDS
    except Exception:
        return DEFAULT_LARK_BIND_TTL_SECONDS


def is_signed_oauth_state(state: str | None) -> bool:
    return isinstance(state, str) and state.startswith(f"{SIGNED_STATE_PREFIX}.")


def issue_signed_oauth_state(payload: dict, ttl_seconds: int | None = None) -> str | None:
    if not isinstance(payload, dict):
        return None

    secret = _get_oauth_state_secret()
    if not secret:
        logging.warning("OAuth state secret missing, skip issuing signed state")
        return None

    ttl = _resolve_lark_bind_ttl(ttl_seconds)
    now = int(time.time())
    state_payload = dict(payload)
    state_payload.update(
        {
            "iat": now,
            "exp": now + ttl,
            "jti": secrets.token_urlsafe(16),
        }
    )

    encoded_payload = _b64_encode(
        json.dumps(state_payload, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        secret,
        encoded_payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    try:
        key = _get_signed_state_storage_key(state_payload["jti"])
        created = _get_redis_client().set(key, "1", ex=ttl, nx=True)
        if not created:
            logging.warning("Failed to reserve signed oauth state jti")
            return None
    except Exception as e:
        logging.exception("Failed to persist signed oauth state: %r", e)
        return None

    return f"{SIGNED_STATE_PREFIX}.{encoded_payload}.{signature}"


def decode_signed_oauth_state(state: str, consume: bool = False) -> tuple[dict | None, str | None]:
    if not is_signed_oauth_state(state):
        return None, "invalid_state_format"

    parts = state.split(".", 2)
    if len(parts) != 3:
        return None, "invalid_state_format"

    _, encoded_payload, signature = parts
    secret = _get_oauth_state_secret()
    if not secret:
        return None, "secret_missing"

    expected_signature = hmac.new(
        secret,
        encoded_payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None, "invalid_signature"

    try:
        payload = json.loads(_b64_decode(encoded_payload).decode("utf-8"))
    except Exception:
        return None, "invalid_payload"

    if not isinstance(payload, dict):
        return None, "invalid_payload"

    try:
        exp = int(payload.get("exp", 0))
    except Exception:
        return None, "invalid_payload"
    if exp <= int(time.time()):
        return None, "state_expired"

    jti = payload.get("jti")
    if not jti:
        return None, "invalid_payload"

    if consume:
        try:
            deleted = _get_redis_client().delete(_get_signed_state_storage_key(jti))
        except Exception as e:
            logging.exception("Failed to consume signed oauth state: %r", e)
            return None, "state_storage_error"
        if deleted != 1:
            return None, "state_used"

    return payload, None
