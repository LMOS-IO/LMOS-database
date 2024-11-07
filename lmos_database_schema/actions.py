from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .tables import APIKey, Model, User
from .redis_access import get_api_key, set_api_key, delete_api_key

async def create_user(session: AsyncSession, username: str, password_hash: str):
    # TODO resume implementing tomorrow morning

async def get_model_by_name(session: AsyncSession, model_name: str):
    result = await session.execute(select(Model).where(Model.name == model_name))
    return result.scalar_one_or_none()

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

async def check_model_access(session: AsyncSession, key_hash: str, model_name: str):
    permissions = await get_api_key_permissions(session, key_hash)
    if permissions is None:
        return False
    
    model = await get_model_by_name(session, model_name)
    if model is None:
        return False
    
    return bool(permissions & (1 << model.permission_bit))

async def grant_model_access(session: AsyncSession, key_hash: str, model_name: str):
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    model = await get_model_by_name(session, model_name)
    
    if api_key and model:
        api_key.model_permissions |= (1 << model.permission_bit)
        await session.commit()
        
        # Update cache
        await set_api_key(key_hash, api_key.model_permissions)
        return True
    
    return False

async def revoke_model_access(session: AsyncSession, key_hash: str, model_name: str):
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    
    model = await get_model_by_name(session, model_name)
    
    if api_key and model:
        api_key.model_permissions &= ~(1 << model.permission_bit)
        await session.commit()
        
        # Update cache
        await set_api_key(key_hash, api_key.model_permissions)
        return True
    
    return False

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

async def get_all_models(session: AsyncSession):
    result = await session.execute(select(Model))
    return result.scalars().all()

async def create_model(session: AsyncSession, name: str, permission_bit: int):
    new_model = Model(name=name, permission_bit=permission_bit)
    session.add(new_model)
    await session.commit()
    return new_model