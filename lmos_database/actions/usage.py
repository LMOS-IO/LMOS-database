from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, with_polymorphic
from typing import Optional, Union, List, Dict
from collections import defaultdict
from pydantic import BaseModel

from ..tables import (
    Usage, LLMUsage, STTUsage, TTSUsage, ReRankerUsage, VoiceType
)

from .model import get_model_by_name

# Pydantic base models
class UsageBase(BaseModel):
    model_name: str 
    api_key_hash: str
    status_code: int

class LLMUsageEntry(UsageBase):
    new_prompt_tokens: int
    cache_prompt_tokens: int 
    generated_tokens: int
    schema_gen_tokens: int

class STTUsageEntry(UsageBase):
    audio_length: int

class TTSUsageEntry(UsageBase):
    text_length: int
    voice_name: str
    audio_length: int

class ReRankerUsageEntry(UsageBase): 
    num_candidates: int
    selected_candidate: int

UsageEntryType = Union[LLMUsageEntry, STTUsageEntry, TTSUsageEntry, ReRankerUsageEntry]

async def create_bulk_usage(
    session: AsyncSession,
    usages: List[UsageEntryType]
) -> Dict[str, List[Union[LLMUsage, STTUsage, TTSUsage, ReRankerUsage]]]:
    """
    Efficiently process bulk usage entries of various types.
    Returns a dictionary of results grouped by usage type.
    """
    # Group usages by type for efficient processing
    grouped_usages = defaultdict(list)
    model_cache = {}
    voice_cache = {}
    results = defaultdict(list)

    for usage in usages:
        if isinstance(usage, LLMUsageEntry):
            grouped_usages["llm"].append(usage)
        elif isinstance(usage, STTUsageEntry):
            grouped_usages["stt"].append(usage)
        elif isinstance(usage, TTSUsageEntry):
            grouped_usages["tts"].append(usage)
        elif isinstance(usage, ReRankerUsageEntry):
            grouped_usages["reranker"].append(usage)

    # Process each type in bulk
    for usage_type, items in grouped_usages.items():
        if not items:
            continue

        # Fetch all required models at once
        model_names = {item.model_name for item in items}
        for model_name in model_names:
            if model_name not in model_cache:
                model = await get_model_by_name(session, model_name)
                if not model or not model.id:
                    continue
                model_cache[model_name] = model

        # For TTS, fetch all voice types at once
        if usage_type == "tts":
            voice_names = {item.voice_name for item in items}
            voice_result = await session.execute(
                select(VoiceType).where(VoiceType.name.in_(voice_names))
            )
            voice_cache = {voice.name: voice for voice in voice_result.scalars().all()}

        # Entry usage objects based on type
        new_usages = []
        for item in items:
            model = model_cache.get(item.model_name)
            if not model:
                continue

            if usage_type == "llm":
                new_usage = LLMUsage(
                    model_id=model.id,
                    api_key_hash=item.api_key_hash,
                    status_code=item.status_code,
                    new_prompt_tokens=item.new_prompt_tokens,
                    cache_prompt_tokens=item.cache_prompt_tokens,
                    generated_tokens=item.generated_tokens,
                    schema_gen_tokens=item.schema_gen_tokens
                )
            elif usage_type == "stt":
                new_usage = STTUsage(
                    model_id=model.id,
                    api_key_hash=item.api_key_hash,
                    status_code=item.status_code,
                    audio_length=item.audio_length
                )
            elif usage_type == "tts":
                voice = voice_cache.get(item.voice_name)
                if not voice:
                    continue
                new_usage = TTSUsage(
                    model_id=model.id,
                    api_key_hash=item.api_key_hash,
                    status_code=item.status_code,
                    text_length=item.text_length,
                    voice_type=voice.id,
                    audio_length=item.audio_length
                )
            elif usage_type == "reranker":
                new_usage = ReRankerUsage(
                    model_id=model.id,
                    api_key_hash=item.api_key_hash,
                    status_code=item.status_code,
                    num_candidates=item.num_candidates,
                    selected_candidate=item.selected_candidate
                )

            new_usages.append(new_usage)
            results[usage_type].append(new_usage)

        if new_usages:
            session.add_all(new_usages)

    await session.commit()
    return results

# LLM Usage functions
async def create_llm_usage(
    session: AsyncSession,
    usage: LLMUsageEntry
) -> Optional[LLMUsage]:
    model = await get_model_by_name(session, usage.model_name)

    if not model:
        raise ValueError(f"Model {usage.model_name} not found")

    if not model.id:
        return None
    
    new_usage = LLMUsage(
        model_id=model.id,
        api_key_hash=usage.api_key_hash,
        status_code=usage.status_code,
        new_prompt_tokens=usage.new_prompt_tokens,
        cache_prompt_tokens=usage.cache_prompt_tokens,
        generated_tokens=usage.generated_tokens,
        schema_gen_tokens=usage.schema_gen_tokens
    )
    session.add(new_usage)
    await session.commit()
    return new_usage

# STT Usage functions
async def create_stt_usage(
    session: AsyncSession,
    usage: STTUsageEntry  
) -> Optional[STTUsage]:
    model = await get_model_by_name(session, usage.model_name)

    if not model:
        raise ValueError(f"Model {usage.model_name} not found")
    
    if not model.id:
        return None
    
    new_usage = STTUsage(
        model_id=model.id,
        api_key_hash=usage.api_key_hash,
        status_code=usage.status_code,
        audio_length=usage.audio_length
    )
    session.add(new_usage)
    await session.commit()
    return new_usage

# TTS Usage functions  
async def create_tts_usage(
    session: AsyncSession,
    usage: TTSUsageEntry
) -> Optional[TTSUsage]:
    model = await get_model_by_name(session, usage.model_name)

    if not model:
        raise ValueError(f"Model {usage.model_name} not found")
    
    if not model.id:
        return None
    
    # Get voice type id
    voice_result = await session.execute(
        select(VoiceType).where(VoiceType.name == usage.voice_name)
    )
    voice = voice_result.scalar_one_or_none()
    if not voice:
        return None
    
    new_usage = TTSUsage(
        model_id=model.id,
        api_key_hash=usage.api_key_hash,
        status_code=usage.status_code,
        text_length=usage.text_length,
        voice_type=voice.id,
        audio_length=usage.audio_length
    )
    session.add(new_usage)
    await session.commit()
    return new_usage


async def create_reranker_usage(
    session: AsyncSession,
    usage: ReRankerUsageEntry
) -> Optional[ReRankerUsage]:
    model = await get_model_by_name(session, usage.model_name)

    if not model:
        raise ValueError(f"Model {usage.model_name} not found")
    
    if not model.id:
        return None
    
    new_usage = ReRankerUsage(
        model_id=model.id,
        api_key_hash=usage.api_key_hash,
        status_code=usage.status_code,
        num_candidates=usage.num_candidates,
        selected_candidate=usage.selected_candidate
    )
    session.add(new_usage)
    await session.commit()
    return new_usage

# Helper function to calculate offset based on page and limit
def get_offset(page: int, limit: int) -> int:
    return (page - 1) * limit

# Pagination logic added (page, limit) to the queries

async def get_usage_by_api_key(
    session: AsyncSession,
    api_key_hash: str,
    usage_type: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> List[Usage]:
    # Ensure the polymorphic entities (Usage subclasses) are loaded
    usage_polymorphic = with_polymorphic(
        Usage,  # Base class
        [LLMUsage, STTUsage, TTSUsage, ReRankerUsage],  # Polymorphic child classes
        aliased=True
    )

    # Prepare the query, eager load relationships and child classes
    query = select(usage_polymorphic).options(
        selectinload(usage_polymorphic.model),     # Eagerly load the model relationship
        selectinload(usage_polymorphic.api_key)    # Eagerly load the api_key relationship
    ).where(usage_polymorphic.api_key_hash == api_key_hash)

    # Filter by usage type if provided
    if usage_type:
        query = query.where(usage_polymorphic.type == usage_type)

    # Add pagination (limit and offset)
    query = query.limit(limit).offset(get_offset(page, limit))

    # Execute the query and fetch the results
    result = await session.execute(query)
    return result.scalars().all()

async def get_usage_by_model_and_api_key(
    session: AsyncSession,
    api_key_hash: str,
    model_name: str,
    usage_type: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> List[Usage]:
    model = await get_model_by_name(session, model_name)

    if not model:
        raise ValueError(f"Model {model_name} not found")

    # Define a polymorphic load of all subtypes of Usage  
    usage_polymorphic = with_polymorphic(
        Usage,  # Base class
        [LLMUsage, STTUsage, TTSUsage, ReRankerUsage],  # Polymorphic child classes
        aliased=True
    )

    # Prepare the query and use selectinload to load necessary relationships
    query = select(usage_polymorphic).options(
        selectinload(usage_polymorphic.model),  # Eagerly load model relationship
        selectinload(usage_polymorphic.api_key)  # Eagerly load api_key relationship
    ).where(
        usage_polymorphic.api_key_hash == api_key_hash,
        usage_polymorphic.model_id == model.id
    )
    
    if usage_type:
        query = query.where(usage_polymorphic.type == usage_type)

    # Add pagination (limit and offset)
    query = query.limit(limit).offset(get_offset(page, limit))

    # Execute the query and ensure all data is loaded eagerly at query time
    result = await session.execute(query)
    rows = result.scalars().all()

    return rows

async def get_usage_by_model(
    session: AsyncSession,
    model_name: str,
    usage_type: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> List[Usage]:
    # Fetch the model by name
    model = await get_model_by_name(session, model_name)

    if not model:
        raise ValueError(f"Model {model_name} not found")

    if not model.id:
        return []

    # Ensure polymorphic load of Usage subclasses
    usage_polymorphic = with_polymorphic(
        Usage,  # Base class
        [LLMUsage, STTUsage, TTSUsage, ReRankerUsage],  # The child polymorphic classes
        aliased=True
    )

    # Prepare the query with eager-loading for relationships
    query = select(usage_polymorphic).options(
        selectinload(usage_polymorphic.model),     # Eagerly load the model relationship
        selectinload(usage_polymorphic.api_key)    # Eagerly load the api_key relationship
    ).where(usage_polymorphic.model_id == model.id)

    if usage_type:
        query = query.where(usage_polymorphic.type == usage_type)

    # Add pagination (limit and offset)
    query = query.limit(limit).offset(get_offset(page, limit))

    # Execute the query and return the result
    result = await session.execute(query)
    return result.scalars().all()