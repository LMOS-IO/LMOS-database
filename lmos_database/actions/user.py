from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import select

from ..tables import User
from ..clients.database import db_manager

async def create_user(username: str, email: str, password_hash: str, totp_secret=None):
    with db_manager.Session() as session:
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            totp_secret=totp_secret
        )
        session.add(new_user)
        await session.commit()
    return new_user

async def get_user_by_username(username: str):
    with db_manager.Session() as session:
        query = select(User).where(User.username == username)
        result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_email(email: str):
    with db_manager.Session() as session:
        query = select(User).where(User.email == email)
        result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_id(user_id: UUID):
    with db_manager.Session() as session:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        response = result.scalar_one_or_none()
    return response

async def get_all_users(session: AsyncSession):
    with db_manager.Session() as session:
        query = select(User)
        result = await session.execute(query)
        response = result.scalars().all()
    return response

async def delete_user_by_id(user_id: UUID):
    with db_manager.Session() as session:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            await session.delete(user)
            await session.commit()
            
    return bool(user)

async def delete_user_by_username(username: str):
    # First fetch the user
    with db_manager.Session() as session:
        query = select(User).where(User.username == username)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # Delete the user through the ORM to trigger cascades
            await session.delete(user)
            await session.commit()

    return bool(user)