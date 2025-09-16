import os
from typing import Optional, Any
import json
from upstash_redis import Redis

class RedisClient:
    def __init__(self):
        self.redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

        if not self.redis_url or not self.redis_token:
            print("Warning: Redis credentials not found. Redis features disabled.")
            self.client = None
        else:
            self.client = Redis(url=self.redis_url, token=self.redis_token)

    def is_available(self) -> bool:
        """Check if Redis is available and configured"""
        return self.client is not None

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration (seconds)"""
        if not self.is_available():
            return False

        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            if expire:
                return self.client.setex(key, expire, serialized_value)
            else:
                return self.client.set(key, serialized_value)
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key"""
        if not self.is_available():
            return None

        try:
            value = self.client.get(key)
            if value is None:
                return None

            # Try to parse as JSON, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key"""
        if not self.is_available():
            return False

        try:
            return self.client.delete(key) > 0
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.is_available():
            return False

        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False

    def ping(self) -> bool:
        """Test Redis connection"""
        if not self.is_available():
            return False

        try:
            response = self.client.ping()
            return response == "PONG"
        except Exception as e:
            print(f"Redis PING error: {e}")
            return False

# Global Redis client instance
redis_client = RedisClient()