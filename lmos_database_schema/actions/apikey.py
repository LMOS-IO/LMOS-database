from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..tables import APIKey
from .redis_access import get_api_key, set_api_key, delete_api_key

async def get_api_key_permissions(session: AsyncSession, key_hash: str):
    # Try to get from cache first
    cached_permissions = await get_api_key(key_hash)
    if cached_permissions is not None:
        return int(cached_permissions)

    # If not in cache, query the database
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    if api_key:
        # Update cache
        await set_api_key(key_hash, api_key.model_permissions)
        return api_key.model_permissions
    
    return None

async def create_api_key(session: AsyncSession, user_id: int, api_hash: str):
    new_api_key = APIKey(user_id=user_id, key_hash=api_hash)
    session.add(new_api_key)
    await session.commit()
    
    # Add to cache
    await set_api_key(new_api_key.key_hash, new_api_key.model_permissions)
    return new_api_key

async def delete_api_key(session: AsyncSession, key_hash: str):
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    if api_key:
        await session.delete(api_key)
        await session.commit()
        
        # Remove from cache
        await delete_api_key(key_hash)
        return True
    
    return False
