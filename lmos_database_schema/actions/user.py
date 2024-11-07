from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..tables import User

async def create_user(session: AsyncSession, username: str, email: str, password_hash: str, totp_secret=None):
    new_user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        totp_secret=totp_secret
    )
    session.add(new_user)
    await session.commit()
    return new_user

async def get_user_by_username(session: AsyncSession, username: str):
    query = select(User).where(User.username == username)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_email(session: AsyncSession, email: str):
    query = select(User).where(User.email == email)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_id(session: AsyncSession, user_id: int):
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def get_all_users(session: AsyncSession):
    query = select(User)
    result = await session.execute(query)
    return result.scalars().all()