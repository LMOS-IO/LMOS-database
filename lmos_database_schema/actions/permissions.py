from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..tables import APIKey
from .apikey import get_api_key_permissions
from .model import get_model_by_name
from .redis_access import set_api_key

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