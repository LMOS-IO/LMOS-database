from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()

# Users Table
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

# API Keys Table
class APIKey(Base):
    __tablename__ = 'api_keys'

    key = Column(String(512), primary_key=True, unique=True, nullable=False)  # Fixed length of 64 characters
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="api_keys")
    usages = relationship("Usage", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(key='{self.key}', user_id='{self.user_id}')>"

# Endpoint table
class Endpoint(Base):
    __tablename__ = 'endpoint'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)

    def __repr__(self):
        return f"<Endpoint(name='{self.name}')>"

# Base class for Usage, with polymorphism
class Usage(Base):
    __tablename__ = 'usage'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    endpoint_id = Column(UUID(as_uuid=True), ForeignKey('endpoint.id'))
    endpoint = relationship("Endpoint")
    api_key_id = Column(String(512), ForeignKey('api_keys.key'), nullable=False)
    api_key = relationship("APIKey", back_populates="usages")
    request_time = Column(DateTime(timezone=True), server_default=func.now())
    status_code = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f"<Usage(type='{self.type}', timestamp='{self.timestamp}', endpoint_id='{self.endpoint_id}', api_key_id='{self.api_key_id}', status_code='{self.status_code}')>"
    
    __mapper_args__ = {
        'polymorphic_identity': 'usage',
        'polymorphic_on': type
    }

# Derived class for LLMUsage
class LLMUsage(Usage):
    __tablename__ = 'llm_usage'
    id = Column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    response_length = Column(Integer)
    new_prompt_tokens = Column(Integer)
    cache_prompt_tokens = Column(Integer)
    generated_tokens = Column(Integer)
    schema_gen_tokens = Column(Integer)

    def __repr__(self):
        return f"<LLMUsage(response_length='{self.response_length}', new_prompt_tokens='{self.new_prompt_tokens}', cache_prompt_tokens='{self.cache_prompt_tokens}', generated_tokens='{self.generated_tokens}', schema_gen_tokens='{self.schema_gen_tokens}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'llm',
    }

# Derived class for STTUsage
class STTUsage(Usage):
    __tablename__ = 'stt_usage'
    id = Column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    audio_length = Column(Integer)  # Length of the audio in seconds

    def __repr__(self):
        return f"<STTUsage(audio_length='{self.audio_length}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'stt',
    }

# Derived class for TTSUsage
class TTSUsage(Usage):
    __tablename__ = 'tts_usage'
    id = Column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    text_length = Column(Integer)  # Length of the text to synthesize
    voice_type = Column(String(50))
    audio_length = Column(Integer)  # Length of the generated audio in seconds

    def __repr__(self):
        return f"<TTSUsage(text_length='{self.text_length}', voice_type='{self.voice_type}', audio_length='{self.audio_length}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'tts',
    }

# Rebuilding the Derived class for ReRankerUsage
class ReRankerUsage(Usage):
    __tablename__ = 'reranker_usage'
    id = Column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    num_candidates = Column(Integer)
    selected_candidate = Column(Integer)  # Index of the selected candidate
    rerank_time = Column(Integer)  # Time taken to rerank in milliseconds
    score_distribution = Column(String(255))  # Score distribution for candidates

    def __repr__(self):
        return f"<ReRankerUsage(num_candidates='{self.num_candidates}', selected_candidate='{self.selected_candidate}', rerank_time='{self.rerank_time}', score_distribution='{self.score_distribution}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'reranker',
    }