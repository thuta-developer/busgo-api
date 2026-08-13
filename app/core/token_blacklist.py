import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def _seconds_until_expiry(payload: Dict[str, Any]) -> int:
    exp = payload.get("exp")
    if exp is None:
        return 0

    if isinstance(exp, datetime):
        expires_at = exp
    else:
        expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)

    return max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))


async def revoke_token(payload: Dict[str, Any]) -> bool:
    jti: Optional[str] = payload.get("jti")
    ttl = _seconds_until_expiry(payload)
    if not jti or ttl <= 0:
        return False

    try:
        redis = get_redis_client()
        await redis.setex(f"jwt:blacklist:{jti}", ttl, "1")
        return True
    except Exception as exc:
        logger.error(f"Redis revoke_token failed: {exc}")
        return False


async def is_token_revoked(payload: Dict[str, Any]) -> bool:
    jti: Optional[str] = payload.get("jti")
    if not jti:
        return False

    try:
        redis = get_redis_client()
        return bool(await redis.exists(f"jwt:blacklist:{jti}"))
    except Exception as exc:
        logger.warning(f"Redis is_token_revoked check failed (fail-open): {exc}")
        return False