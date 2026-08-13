import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core.redis_client import get_redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, requests_per_minute: int):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._fallback_hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"rate-limit:{client}"

        allowed = await self._allow_request(key)
        if not allowed:
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)

    async def _allow_request(self, key: str) -> bool:
        try:
            redis = get_redis_client()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
            return count <= self.requests_per_minute
        except Exception:
            return self._allow_request_in_memory(key)

    def _allow_request_in_memory(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - 60
        hits = self._fallback_hits[key]

        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.requests_per_minute:
            return False

        hits.append(now)
        return True
