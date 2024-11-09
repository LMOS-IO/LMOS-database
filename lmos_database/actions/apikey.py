from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from redis.asyncio.client import Redis

from ..tables import APIKey, Model
from .redis_access import get_api_key, set_api_key, delete_api_key, delete_model_access

async def get_api_key_permissions(session: AsyncSession, redis_client: Redis, key_hash: str):
    # Try to get from cache first
    cached_permissions = await get_api_key(redis_client, key_hash)
    if cached_permissions is not None:
        return int(cached_permissions)

    # If not in cache, query the database
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()

    if api_key:
        # Update cache
        await set_api_key(redis_client, key_hash, api_key.model_permissions)
        return api_key.model_permissions

    return None

async def create_api_key(session: AsyncSession, redis_client: Redis, user_id: int, api_hash: str):
    new_api_key = APIKey(user_id=user_id, key_hash=api_hash)
    session.add(new_api_key)
    await session.commit()
    
    # Add to cache
    await set_api_key(redis_client, str(new_api_key.key_hash), new_api_key.model_permissions)
    return new_api_key

async def get_api_keys_by_user(session: AsyncSession, user_id: int):
    result = await session.execute(select(APIKey).where(APIKey.user_id == user_id))
    api_keys = result.scalars().all()
    return api_keys

async def delete_api_key_by_hash(session: AsyncSession, redis_client: Redis, key_hash: str):
    # Query to get the APIKey instance if it exists
    result = await session.execute(
    select(APIKey)
    .options(selectinload(APIKey.models))
    .where(APIKey.key_hash == key_hash)
)
    api_key = result.scalar_one_or_none()

    if not api_key:
        # Return False if the API key doesn't exist
        return False

    # Fetch the associated models through the APIKeyModel relationship
    model_associations = api_key.model_associations
    print(model_associations)

    print(f"Found {len(model_associations)} associations to delete for API key: {key_hash}")
    
    # Now iterate over the APIKeyModel associations and remove the access entries from Redis cache for each model
    for api_key_model in model_associations:
        print(f"Deleting access for model ID: {api_key_model.model_id}")
        model_name_result = await session.execute(select(Model.name).where(Model.id == api_key_model.model_id))
        model_name = model_name_result.scalar_one_or_none()
        
        if model_name:
            print(f"Deleting access for model: {model_name}")
            await delete_model_access(redis_client, model_name)

    # At this point, we've handled model cache removals; now delete the APIKey
    await session.delete(api_key)
    
    # Commit changes to the database
    await session.commit()

    # Remove from Redis cache
    await delete_api_key(redis_client, key_hash)

    return True