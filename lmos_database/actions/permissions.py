from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio.client import Redis
from typing import Optional

from ..tables import APIKey, APIKeyModelRateLimit, APIKeyModel
from .model import get_model_by_name
from .redis_access_cache import CachedAPIHash, get_keycache_data, build_set_keycache_data

async def get_api_permissions(
        session: AsyncSession, redis_client: Redis, key_hash: str
) -> Optional[CachedAPIHash]:
    # check cache
    keycache_data = await get_keycache_data(redis_client, key_hash)
    if keycache_data:
        return keycache_data
    
    # If cache miss, then use build_set_keycache_data to attempt to collect it

    keycache_data = await build_set_keycache_data(session, redis_client, key_hash)

    # If we have a hit, return the CachedAPIHash
    return keycache_data

async def grant_model_access(
    session: AsyncSession, 
    redis_client: Redis, 
    key_hash: str, 
    model_name: str,
    requests_per_minute: int,
    resource_quota_per_minute: int
) -> bool:
    # Fetch the API key from the database
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    # Validate the API key
    if api_key is None or not api_key.enabled:
        # TODO Log when key is disabled
        return False  # Invalid or disabled key API key

    # Fetch the model by name
    model = await get_model_by_name(session, model_name)
    
    # Validate the model
    if not model:
        return False  # Invalid model
    
    # Set the model permission using the permission bit
    api_key.model_permissions |= (1 << model.permission_bit)
    
    # Create the model association if it doesn't exist
    result = await session.execute(
        select(APIKeyModel).where(
            APIKeyModel.api_key_hash == key_hash,
            APIKeyModel.model_id == model.id
        )
    )
    model_association = result.scalar_one_or_none()
    
    if model_association is None:
        model_association = APIKeyModel(
            api_key_hash=key_hash,
            model_id=model.id
        )
        session.add(model_association)
    
    # Create or update the rate limits for the key and model
    result = await session.execute(
        select(APIKeyModelRateLimit).where(
            APIKeyModelRateLimit.api_key_hash == key_hash,
            APIKeyModelRateLimit.model_id == model.id
        )
    )
    rate_limit = result.scalar_one_or_none()
    
    # Update or create a new rate limit record
    if rate_limit is None:
        rate_limit = APIKeyModelRateLimit(
            api_key_hash=key_hash,
            model_id=model.id,
            requests_per_minute=requests_per_minute,
            resource_quota_per_minute=resource_quota_per_minute
        )
        session.add(rate_limit)
    else:
        rate_limit.requests_per_minute = requests_per_minute
        rate_limit.resource_quota_per_minute = resource_quota_per_minute
    
    # Commit the changes to the database
    await session.commit()
    
    # rebuild cache for the key
    await build_set_keycache_data(session, redis_client, key_hash)
    return True

async def revoke_model_access(session: AsyncSession, redis_client: Redis, key_hash: str, model_name: str) -> bool:
    # Fetch the API key from the database
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    # Validate the API key
    if api_key is None:
        return False  # Invalid API key
    
    # Fetch the model by name
    model = await get_model_by_name(session, model_name)
    
    # Validate the model
    if not model:
        return False  # Invalid model

    # Remove the permission bit for the particular model
    api_key.model_permissions &= ~(1 << model.permission_bit)
    
    # Commit the changes to the database
    await session.commit()

    # rebuild cache for the key
    await build_set_keycache_data(session, redis_client, key_hash)
    return True
    
    