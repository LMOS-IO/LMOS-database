from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from functools import lru_cache

from ..tables import (
    Usage, LLMUsage, STTUsage, TTSUsage, ReRankerUsage, 
    Model, VoiceType
)

@lru_cache(maxsize=None)
async def _get_model_id_by_name(session: AsyncSession, model_name: str):
    result = await session.execute(select(Model).where(Model.name == model_name))
    model = result.scalar_one_or_none()
    return model.id if model else None

# LLM Usage functions
async def create_llm_usage(
    session: AsyncSession,
    model_name: str,
    api_key_hash: str,
    status_code: int,
    new_prompt_tokens: int,
    cache_prompt_tokens: int,
    generated_tokens: int,
    schema_gen_tokens: int
) -> Optional[LLMUsage]:
    model_id = await _get_model_id_by_name(session, model_name)
    if not model_id:
        return None
    
    new_usage = LLMUsage(
        model_id=model_id,
        api_key_hash=api_key_hash,
        status_code=status_code,
        new_prompt_tokens=new_prompt_tokens,
        cache_prompt_tokens=cache_prompt_tokens,
        generated_tokens=generated_tokens,
        schema_gen_tokens=schema_gen_tokens
    )
    session.add(new_usage)
    await session.commit()
    return new_usage

# STT Usage functions
async def create_stt_usage(
    session: AsyncSession,
    model_name: str,
    api_key_hash: str,
    status_code: int,
    audio_length: int
) -> Optional[STTUsage]:
    model_id = await _get_model_id_by_name(session, model_name)
    if not model_id:
        return None
    
    new_usage = STTUsage(
        model_id=model_id,
        api_key_hash=api_key_hash,
        status_code=status_code,
        audio_length=audio_length
    )
    session.add(new_usage)
    await session.commit()
    return new_usage

# TTS Usage functions
async def create_tts_usage(
    session: AsyncSession,
    model_name: str,
    api_key_hash: str,
    status_code: int,
    text_length: int,
    voice_name: str,
    audio_length: int
) -> Optional[TTSUsage]:
    model_id = await _get_model_id_by_name(session, model_name)
    if not model_id:
        return None
    
    # Get voice type id
    voice_result = await session.execute(
        select(VoiceType).where(VoiceType.name == voice_name)
    )
    voice = voice_result.scalar_one_or_none()
    if not voice:
        return None
    
    new_usage = TTSUsage(
        model_id=model_id,
        api_key_hash=api_key_hash,
        status_code=status_code,
        text_length=text_length,
        voice_type=voice.id,
        audio_length=audio_length
    )
    session.add(new_usage)
    await session.commit()
    return new_usage

# ReRanker Usage functions
async def create_reranker_usage(
    session: AsyncSession,
    model_name: str,
    api_key_hash: str,
    status_code: int,
    num_candidates: int,
    selected_candidate: int
) -> Optional[ReRankerUsage]:
    model_id = await _get_model_id_by_name(session, model_name)
    if not model_id:
        return None
    
    new_usage = ReRankerUsage(
        model_id=model_id,
        api_key_hash=api_key_hash,
        status_code=status_code,
        num_candidates=num_candidates,
        selected_candidate=selected_candidate
    )
    session.add(new_usage)
    await session.commit()
    return new_usage

# Generic usage query functions
async def get_usage_by_api_key(
    session: AsyncSession,
    api_key_hash: str,
    usage_type: Optional[str] = None
):
    query = select(Usage).where(Usage.api_key_hash == api_key_hash)
    if usage_type:
        query = query.where(Usage.type == usage_type)
    result = await session.execute(query)
    return result.scalars().all()

async def get_usage_by_model_and_api_key(
    session: AsyncSession,
    api_key_hash: str,
    model_name: str,
    usage_type: Optional[str] = None
):
    model_id = await _get_model_id_by_name(session, model_name)
    if not model_id:
        return []
        
    query = select(Usage).where(
        Usage.api_key_hash == api_key_hash,
        Usage.model_id == model_id
    )
    if usage_type:
        query = query.where(Usage.type == usage_type)
    result = await session.execute(query)
    return result.scalars().all()

async def get_usage_by_model(
    session: AsyncSession,
    model_name: str,
    usage_type: Optional[str] = None
):
    model_id = await _get_model_id_by_name(session, model_name)
    if not model_id:
        return []
    
    query = select(Usage).where(Usage.model_id == model_id)
    if usage_type:
        query = query.where(Usage.type == usage_type)
    result = await session.execute(query)
    return result.scalars().all()