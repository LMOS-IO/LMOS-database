from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio.client import Redis
from typing import List

from ..tables import APIKey
from .redis_access_cache import delete_keycache_data

async def create_api_key(session: AsyncSession, user_id: int, api_hash: str) -> APIKey:
    new_api_key = APIKey(user_id=user_id, key_hash=api_hash)
    session.add(new_api_key)
    await session.commit()
    
    return new_api_key

async def get_api_keys_by_user(session: AsyncSession, user_id: int) -> List[APIKey]:
    result = await session.execute(select(APIKey).where(APIKey.user_id == user_id))
    api_keys = result.scalars().all()
    return api_keys

async def delete_api_key_by_hash(
        session: AsyncSession, redis_client: Redis, key_hash: str
) -> bool:
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    if api_key:
        await session.delete(api_key)
        await session.commit()
        
        # Remove from cache
        await delete_keycache_data(redis_client, key_hash)
        return True
    
    return False

async def disable_api_key_by_hash(
        session: AsyncSession, redis_client: Redis, key_hash: str
) -> bool:
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    if api_key:
        api_key.disabled = True
        await session.commit()
        
        # Remove from cache
        await delete_keycache_data(redis_client, key_hash)
        return True
    
    return False