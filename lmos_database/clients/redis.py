from lmos_config import config
from redis.asyncio.client import Redis

class RedisClient:
    def load(self):
        self.redis_client = Redis.from_url(
            str(config.internal_configuration.redis.url),
            decode_responses=True
        )

redis_manager = RedisClient()
