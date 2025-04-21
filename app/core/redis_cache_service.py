import json
from typing import Any, Optional
import redis
from app.config import settings


class RedisCacheService:

    def __init__(self, default_ttl: int = 3600):

        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        value = self.redis_client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if ttl is None:
            ttl = self.default_ttl

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.redis_client.setex(key, ttl, value)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        return bool(self.redis_client.delete(key))

    def flush_all(self) -> bool:
        return self.redis_client.flushdb()
