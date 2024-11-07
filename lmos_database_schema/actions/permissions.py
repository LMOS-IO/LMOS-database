from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio.client import Redis
from typing import Optional, Tuple, NamedTuple

from ..tables import APIKey, APIKeyModelRateLimit
from .apikey import get_api_key_permissions
from .model import get_model_by_name
from .redis_access import set_api_key, set_model_access, get_model_access

class ModelAccess(NamedTuple):
    has_permission: bool
    requests_per_minute: Optional[int] = None
    resource_quota_per_minute: Optional[int] = None

async def check_model_access(session: AsyncSession, redis_client: Redis, key_hash: str, model_name: str) -> ModelAccess:
    # Try to get cached model access first
    cached_access = await get_model_access(redis_client, key_hash, model_name)
    if cached_access is not None:
        return ModelAccess(
            has_permission=cached_access['has_permission'],
            requests_per_minute=cached_access.get('requests_per_minute'),
            resource_quota_per_minute=cached_access.get('resource_quota_per_minute')
        )
    
    # If not in cache, check permissions and rate limits from DB
    permissions = await get_api_key_permissions(session, redis_client, key_hash)
    if permissions is None:
        return ModelAccess(has_permission=False)
    
    model = await get_model_by_name(session, model_name)
    if model is None:
        return ModelAccess(has_permission=False)
    
    has_permission = bool(permissions & (1 << model.permission_bit))
    
    if not has_permission:
        access_data = {'has_permission': False}
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
        'has_permission': True,
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
):
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    model = await get_model_by_name(session, model_name)
    
    if api_key and model:
        # Set the permissions bit
        api_key.model_permissions |= (1 << model.permission_bit)
        
        # Create or update the rate limits
        result = await session.execute(
            select(APIKeyModelRateLimit).where(
                APIKeyModelRateLimit.api_key_hash == key_hash,
                APIKeyModelRateLimit.model_id == model.id
            )
        )
        rate_limit = result.scalar_one_or_none()
        
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
        
        await session.commit()
        
        # Update caches
        await set_api_key(redis_client, key_hash, api_key.model_permissions)
        await set_model_access(redis_client, key_hash, model_name, {
            'has_permission': True,
            'requests_per_minute': requests_per_minute,
            'resource_quota_per_minute': resource_quota_per_minute
        })
        return True
    
    return False

async def revoke_model_access(session: AsyncSession, redis_client: Redis, key_hash: str, model_name: str):
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    model = await get_model_by_name(session, model_name)
    
    if api_key and model:
        # Remove the permissions bit while keeping the rate limits
        api_key.model_permissions &= ~(1 << model.permission_bit)
        await session.commit()
        
        # Update caches
        await set_api_key(redis_client, key_hash, api_key.model_permissions)
        await set_model_access(redis_client, key_hash, model_name, {
            'has_permission': False
        })
        return True
    
    return False
