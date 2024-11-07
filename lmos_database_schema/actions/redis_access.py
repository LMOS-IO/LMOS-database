import redis.asyncio as redis
from redis.asyncio.client import Redis

redis_client: Redis = None

# FIXME load from lmos_config
async def init_redis(host='localhost', port=6379, db=0):
    global redis_client
    redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

async def get_api_key(key_hash: str):
    return await redis_client.get(f"api_key:{key_hash}")

async def set_api_key(key_hash: str, permissions: int, ttl: int = 3600):
    await redis_client.set(f"api_key:{key_hash}", permissions, ex=ttl)

async def delete_api_key(key_hash: str):
    await redis_client.delete(f"api_key:{key_hash}")

async def close_redis():
    if redis_client:
        await redis_client.close()
