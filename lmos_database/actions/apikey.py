from sqlalchemy.future import select
from redis.asyncio.client import Redis
from typing import Sequence

from ..tables import APIKey
from ..clients.database import db_manager
from .redis_access_cache import delete_keycache_data
from .hash import generate_api_key, hash_str

async def create_api_key(user_id: int) -> str:
    with db_manager.Session() as session:
        new_key = generate_api_key()
        api_hash = hash_str(new_key, is_api_key=True)
        new_api_key = APIKey(user_id=user_id, key_hash=api_hash)
        session.add(new_api_key)
        await session.commit()
    return new_key

async def get_api_keys_by_user(user_id: int, include_disabled=False) -> Sequence[APIKey]:
    with db_manager.Session() as session:
        if not include_disabled:
            query = select(APIKey).where(APIKey.user_id == user_id, APIKey.enabled)
        else:
            query = select(APIKey).where(APIKey.user_id == user_id)

        result = await session.execute(query)
        api_keys = result.scalars().all()
    return api_keys

async def delete_api_key_by_hash(redis_client: Redis, key_hash: str) -> bool:
    with db_manager.Session() as session:
        result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        api_key = result.scalar_one_or_none()
        
        if api_key:
            await session.delete(api_key)
            await session.commit()
            
            # Remove from cache
            await delete_keycache_data(redis_client, key_hash)

    return bool(api_key)

async def disable_api_key_by_hash(
        redis_client: Redis, key_hash: str
) -> bool:
    with db_manager.Session() as session:
        result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        api_key = result.scalar_one_or_none()
        
        if api_key:
            api_key.enabled = False
            await session.commit()
            
            # Remove from cache
            await delete_keycache_data(redis_client, key_hash)

    return bool(api_key)