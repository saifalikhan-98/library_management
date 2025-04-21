from fastapi import Request
import time
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.config import settings


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
)

class GlobalRateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp):

        super().__init__(app)
        self.__redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):

        client_ip = get_remote_address(request)
        redis_key = f"global_ratelimit:{client_ip}"
        first_request_key = f"global_ratelimit:first:{client_ip}"

        current_time = int(time.time())
        if not self.__redis_client.exists(first_request_key):
            self.__redis_client.set(first_request_key, current_time, ex=60)

        request_count = self.__redis_client.incr(redis_key)
        if request_count == 1:
            self.__redis_client.expire(redis_key, 60)


        GLOBAL_RATE_LIMIT = 100

        if request_count > GLOBAL_RATE_LIMIT:
            reset_time = self.__redis_client.ttl(redis_key)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Global rate limit exceeded: {GLOBAL_RATE_LIMIT} requests per minute allowed",
                    "limit": GLOBAL_RATE_LIMIT,
                    "reset_in_seconds": reset_time
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(GLOBAL_RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(max(0, GLOBAL_RATE_LIMIT - request_count))
        response.headers["X-RateLimit-Reset"] = str(self.__redis_client.ttl(redis_key))

        return response
