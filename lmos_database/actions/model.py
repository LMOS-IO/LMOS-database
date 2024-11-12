from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional, Sequence

from ..tables import Model
from ..clients.database import db_manager

async def create_model(name: str, permission_bit: int) -> Model:
    with db_manager.Session() as session:
        new_model = Model(name=name, permission_bit=permission_bit)
        session.add(new_model)
        await session.commit()
    return new_model

async def get_model_by_name(model_name: str) -> Optional[Model]:
    with db_manager.Session() as session:
        result = await session.execute(select(Model).where(Model.name == model_name))
        response = result.scalar_one_or_none()
    return response

async def get_model_by_id(model_id: UUID) -> Optional[Model]:
    with db_manager.Session() as session:
        result = await session.execute(select(Model).where(Model.id == model_id))
        response = result.scalar_one_or_none()
    return response

async def get_all_models() -> Sequence[Model]:
    with db_manager.Session() as session:
        result = await session.execute(select(Model))
        response = result.scalars().all()
    return response

async def delete_model_by_id(model_id: UUID) -> bool:
    model = await get_model_by_id(model_id)
    if model:
        with db_manager.Session() as session:
            await session.delete(model)
            await session.commit()

    return bool(model)

async def delete_model_by_name(model_name: str) -> bool:
    model = await get_model_by_name(model_name)
    if model:
        with db_manager.Session() as session:
            await session.delete(model)
            await session.commit()

    return bool(model)