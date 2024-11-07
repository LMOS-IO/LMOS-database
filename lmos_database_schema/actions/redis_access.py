import redis.asyncio as redis
from redis.asyncio.client import Redis
from typing import Optional, Union

async def get_api_key(redis_client: Redis, key_hash: str) -> Optional[bytes]:
    try:
        return await redis_client.get(f"api_key:{key_hash}")
    except redis.RedisError as e:
        raise Exception(f"Redis error while getting API key: {str(e)}")

async def set_api_key(redis_client: Redis, key_hash: str, permissions, ttl: int = 3600) -> None:
    try:
        await redis_client.set(f"api_key:{key_hash}", str(permissions), ex=ttl)
    except redis.RedisError as e:
        raise Exception(f"Redis error while setting API key: {str(e)}")

async def delete_api_key(redis_client: Redis, key_hash: str) -> None:
    try:
        await redis_client.delete(f"api_key:{key_hash}")
    except redis.RedisError as e:
        raise Exception(f"Redis error while deleting API key: {str(e)}")

async def close_redis(redis_client: Optional[Redis]) -> None:
    if redis_client:
        try:
            await redis_client.close()
        except redis.RedisError as e:
            raise Exception(f"Redis error while closing connection: {str(e)}")