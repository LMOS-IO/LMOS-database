from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..tables import Model

async def create_model(session: AsyncSession, name: str, permission_bit: int):
    new_model = Model(name=name, permission_bit=permission_bit)
    session.add(new_model)
    await session.commit()
    return new_model

async def get_model_by_name(session: AsyncSession, model_name: str):
    result = await session.execute(select(Model).where(Model.name == model_name))
    return result.scalar_one_or_none()

async def get_model_by_id(session: AsyncSession, model_id: int):
    result = await session.execute(select(Model).where(Model.id == model_id))
    return result.scalar_one_or_none()

async def get_all_models(session: AsyncSession):
    result = await session.execute(select(Model))
    return result.scalars().all()