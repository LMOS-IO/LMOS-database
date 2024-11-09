from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio.client import Redis
from typing import Optional, NamedTuple

from ..tables import APIKey, APIKeyModelRateLimit
from .apikey import get_api_key_permissions
from .model import get_model_by_name
from .redis_access import set_api_key, set_model_access, get_model_access

class ModelAccess(NamedTuple):
    valid_api_key: bool
    has_permission: bool
    model_exists: bool
    requests_per_minute: Optional[int] = None
    resource_quota_per_minute: Optional[int] = None

async def check_model_access(session: AsyncSession, redis_client: Redis, key_hash: str, model_name: str) -> ModelAccess:
    # Try to get cached model access first
    cached_access = await get_model_access(redis_client, key_hash, model_name)
    if cached_access is not None:
        return ModelAccess(
            valid_api_key=cached_access['valid_api_key'],
            has_permission=cached_access['has_permission'],
            model_exists=cached_access.get('model_exists'),
            requests_per_minute=cached_access.get('requests_per_minute'),
            resource_quota_per_minute=cached_access.get('resource_quota_per_minute')
        )
    
    # If not in cache, check permissions and rate limits from DB
    permissions = await get_api_key_permissions(session, redis_client, key_hash)
    if permissions is None:
        return ModelAccess(valid_api_key=False, has_permission=False, model_exists=False)
    
    model = await get_model_by_name(session, model_name)
    if model is None:
        return ModelAccess(valid_api_key=True, has_permission=False, model_exists=False)
    
    has_permission = bool(permissions & (1 << model.permission_bit))
    
    if not has_permission:
        access_data = {'valid_api_key': True, 'has_permission': False, 'model_exists': True}
        await set_model_access(redis_client, key_hash, model_name, access_data)
        return ModelAccess(has_permission=False)
    
    # If has permission, fetch rate limits
    result = await session.execute(
        select(APIKeyModelRateLimit).where(
            APIKeyModelRateLimit.api_key_hash == key_hash,
            APIKeyModelRateLimit.model_id == model.id
        )
    )
    rate_limit = result.scalar_one_or_none()
    
    access_data = {
        'valid_api_key': True,
        'has_permission': True,
        'model_exists': True,
        'requests_per_minute': rate_limit.requests_per_minute if rate_limit else None,
        'resource_quota_per_minute': rate_limit.resource_quota_per_minute if rate_limit else None
    }
    
    # Cache the results
    await set_model_access(redis_client, key_hash, model_name, access_data)
    
    return ModelAccess(
        has_permission=True,
        requests_per_minute=rate_limit.requests_per_minute if rate_limit else None,
        resource_quota_per_minute=rate_limit.resource_quota_per_minute if rate_limit else None
    )

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
    if not api_key:
        return False  # Invalid API key

    # Fetch the model by name
    model = await get_model_by_name(session, model_name)
    
    # Validate the model
    if not model:
        return False  # Invalid model
    
    # Set the model permission using the permission bit
    api_key.model_permissions |= (1 << model.permission_bit)
    
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
    
    # Update the API key cache
    await set_api_key(redis_client, key_hash, api_key.model_permissions)
    # Update model access cache
    await set_model_access(redis_client, key_hash, model_name, {
        'valid_api_key': True,
        'has_permission': True,
        'model_exists': True,
        'requests_per_minute': requests_per_minute,
        'resource_quota_per_minute': resource_quota_per_minute
    })

    return True


async def revoke_model_access(session: AsyncSession, redis_client: Redis, key_hash: str, model_name: str) -> bool:
    # Fetch the API key from the database
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    # Validate the API key
    if not api_key:
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

    # Update the API key permissions in the cache
    await set_api_key(redis_client, key_hash, api_key.model_permissions)
    
    # Update the model access cache to indicate the permission was revoked
    await set_model_access(redis_client, key_hash, model_name, {
        'valid_api_key': True,
        'has_permission': False,
        'model_exists': True
    })

    return True
