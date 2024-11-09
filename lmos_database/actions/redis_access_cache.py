import redis.asyncio as redis
from redis.asyncio.client import Redis
from typing import Optional, Union, Sequence
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from ..tables import APIKey

# TODO consider loading this from lmos_config
CACHE_TTL = 3600  # 1 hour in seconds

class ProvisionedModel(BaseModel):
    name: str
    access: bool
    requests_per_minute: Optional[int] = None
    resource_quota_per_minute: Optional[int] = None

class CachedAPIHash(BaseModel):
    models: Sequence[ProvisionedModel]

async def build_set_keycache_data(session: AsyncSession, redis_client: Redis, api_key_hash: str) -> Union[CachedAPIHash, None]:
    # Fetch the API key from the database with all necessary relationships
    result = await session.execute(
        select(APIKey)
        .where(APIKey.key_hash == api_key_hash)
        .options(
            selectinload(APIKey.models),
            selectinload(APIKey.rate_limits)
        )
    )

    api_key = result.scalar_one_or_none()

    if api_key is None or not api_key.enabled:
        # TODO Log if trying to build cache for a disabled API key
        return None # API key not found or disabled

    provisioned_models = []
    for model in api_key.models:
        # Find the rate limit for this model
        rate_limit = next(
            (rl for rl in api_key.rate_limits if rl.model_id == model.id),
            None
        )

        # Check if model is accessible based on permission bits
        has_access = bool(api_key.model_permissions & (1 << model.permission_bit))

        # build the provisioned model object
        provisioned_model = ProvisionedModel(
            name=model.name,
            access=has_access,
            requests_per_minute=rate_limit.requests_per_minute if rate_limit else None,
            resource_quota_per_minute=rate_limit.resource_quota_per_minute if rate_limit else None
        )
        provisioned_models.append(provisioned_model)

    # Create the CachedAPIHash object
    cached_api_hash = CachedAPIHash(models=provisioned_models)
    await set_keycache_data(redis_client, api_key_hash, cached_api_hash)
    return cached_api_hash

async def set_keycache_data(redis_client: Redis, api_hash: str, data: CachedAPIHash) -> bool:
    try:
        serialized_data = data.model_dump_json()
        await redis_client.set(api_hash, serialized_data, ex=CACHE_TTL)
        return True
    except redis.RedisError as e:
        raise Exception(f"Redis error while setting key data: {str(e)}")

async def get_keycache_data(redis_client: Redis, api_hash: str) -> Union[CachedAPIHash, None]:
    try:
        data = await redis_client.get(api_hash)
        if data:
            return CachedAPIHash.model_validate_json(data)
        return None
    except redis.RedisError as e:
        raise Exception(f"Redis error while getting key data: {str(e)}")
    
async def delete_keycache_data(redis_client: Redis, api_hash: str) -> bool:
    try:
        await redis_client.delete(api_hash)
        return True
    except redis.RedisError as e:
        raise Exception(f"Redis error while deleting key data: {str(e)}")
    


async def close_redis(redis_client: Optional[Redis]) -> None:
    if redis_client:
        try:
            await redis_client.close()
        except redis.RedisError as e:
            raise Exception(f"Redis error while closing connection: {str(e)}")