import redis.asyncio as redis
from redis.asyncio.client import Redis
from typing import Optional, Dict, Any
import json

async def get_api_key(redis_client: Redis, key_hash: str) -> Optional[bytes]:
    try:
        return await redis_client.get(f"api_key:{key_hash}")
    except redis.RedisError as e:
        raise Exception(f"Redis error while getting API key: {str(e)}")

async def get_model_access(redis_client: Redis, key_hash: str, model_name: str) -> Optional[Dict[str, Any]]:
    try:
        data = await redis_client.get(f"model_access:{key_hash}:{model_name}")
        return json.loads(data) if data else None
    except redis.RedisError as e:
        raise Exception(f"Redis error while getting model access: {str(e)}")

async def set_model_access(
    redis_client: Redis, 
    key_hash: str, 
    model_name: str, 
    access_data: Dict[str, Any], 
    ttl: int = 3600
) -> None:
    try:
        await redis_client.set(
            f"model_access:{key_hash}:{model_name}",
            json.dumps(access_data),
            ex=ttl
        )
    except redis.RedisError as e:
        raise Exception(f"Redis error while setting model access: {str(e)}")

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