import uuid
from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, Integer, String, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase, mapped_column, Mapped

class Base(DeclarativeBase):
    pass

# Users Table
class User(Base):
    __tablename__ = 'users'

    id: Mapped[UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    totp_secret: Mapped[str] = mapped_column(String, nullable=True)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

# Model table
class Model(Base):
    __tablename__ = 'model'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    api_key_associations = relationship("APIKeyModel", back_populates="model")
    api_keys = relationship("APIKey", secondary="api_key_model", viewonly=True)
    permission_bit: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    rate_limits = relationship("APIKeyModelRateLimit", back_populates="model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Model(name='{self.name}')>"
    
# Voice type table
class VoiceType(Base):
    __tablename__ = 'voice_type'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tts_usages = relationship("TTSUsage", back_populates="voice")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<VoiceType(name='{self.name}')>"
    
# Rate limits for API key and model combinations
class APIKeyModelRateLimit(Base):
    __tablename__ = 'api_key_model_rate_limits'

    api_key_hash: Mapped[str] = mapped_column(String(512), ForeignKey('api_keys.key_hash', ondelete="CASCADE"), primary_key=True)
    model_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('model.id'), primary_key=True)
    requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_quota_per_minute: Mapped[int] = mapped_column(Integer, nullable=False)

    api_key = relationship("APIKey", passive_deletes=True)
    model = relationship("Model")
    
    __table_args__ = (
        Index('idx_api_key_model_rate_limits', 'api_key_hash', 'model_id'),
    )

    def __repr__(self):
        return f"<APIKeyModelRateLimit(api_key_hash='{self.api_key_hash}', model_id='{self.model_id}', " \
               f"requests_per_minute={self.requests_per_minute}, resource_quota_per_minute={self.resource_quota_per_minute})>"

class APIKeyModel(Base):
    __tablename__ = 'api_key_model'
    
    api_key_hash: Mapped[str] = mapped_column(String(512), ForeignKey('api_keys.key_hash', ondelete="CASCADE"), primary_key=True)
    model_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('model.id'), primary_key=True)
    
    api_key = relationship("APIKey", back_populates="model_associations", passive_deletes=True)
    model = relationship("Model", back_populates="api_key_associations")
    
    __table_args__ = (
        Index('idx_api_key_model', 'api_key_hash', 'model_id'),
    )
    
    def __repr__(self):
        return f"<APIKeyModel(api_key_hash='{self.api_key_hash}', model_id='{self.model_id}')>"

# API Keys Table
class APIKey(Base):
    __tablename__ = 'api_keys'

    key_hash: Mapped[str] = mapped_column(String(512), primary_key=True, unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    user = relationship("User", back_populates="api_keys")
    usages = relationship("Usage", back_populates="api_key", cascade="all, delete-orphan")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_associations = relationship("APIKeyModel", back_populates="api_key", cascade="all, delete-orphan")
    models = relationship("Model", secondary="api_key_model", viewonly=True)
    model_permissions: Mapped[int] = mapped_column(BigInteger, default=0)
    rate_limits = relationship("APIKeyModelRateLimit", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(key='{self.key_hash}', user_id='{self.user_id}')>"

# Base class for Usage, with polymorphism
class Usage(Base):
    __tablename__ = 'usage'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('model.id'))
    model = relationship("Model")
    api_key_hash: Mapped[str] = mapped_column(String(512), ForeignKey('api_keys.key_hash', ondelete="CASCADE"), nullable=False)
    api_key = relationship("APIKey", back_populates="usages", passive_deletes=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=0)
    
    def __repr__(self):
        return f"<Usage(type='{self.type}', timestamp='{self.timestamp}', model_id='{self.model_id}', api_key_hash='{self.api_key_hash}', status_code='{self.status_code}')>"
    
    __mapper_args__ = {
        'polymorphic_identity': 'usage',
        'polymorphic_on': type
    }

# Derived class for LLMUsage
class LLMUsage(Usage):
    __tablename__ = 'llm_usage'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    new_prompt_tokens: Mapped[int] = mapped_column(Integer)
    cache_prompt_tokens: Mapped[int] = mapped_column(Integer)
    generated_tokens: Mapped[int] = mapped_column(Integer)
    schema_gen_tokens: Mapped[int] = mapped_column(Integer)

    def __repr__(self):
        return f"<LLMUsage(new_prompt_tokens='{self.new_prompt_tokens}', cache_prompt_tokens='{self.cache_prompt_tokens}', generated_tokens='{self.generated_tokens}', schema_gen_tokens='{self.schema_gen_tokens}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'llm',
    }

# Derived class for STTUsage
class STTUsage(Usage):
    __tablename__ = 'stt_usage'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    audio_length: Mapped[int] = mapped_column(Integer)  # Length of the audio in seconds

    def __repr__(self):
        return f"<STTUsage(audio_length='{self.audio_length}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'stt',
    }

# Derived class for TTSUsage
class TTSUsage(Usage):
    __tablename__ = 'tts_usage'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    text_length: Mapped[int] = mapped_column(Integer)  # Length of the text to synthesize
    voice_type: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('voice_type.id'))
    voice = relationship("VoiceType", back_populates="tts_usages")
    audio_length: Mapped[int] = mapped_column(Integer)  # Length of the generated audio in seconds

    def __repr__(self):
        return f"<TTSUsage(text_length='{self.text_length}', voice_type='{self.voice_type}', audio_length='{self.audio_length}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'tts',
    }

# Rebuilding the Derived class for ReRankerUsage
class ReRankerUsage(Usage):
    __tablename__ = 'reranker_usage'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('usage.id'), primary_key=True, default=uuid.uuid4)
    num_candidates: Mapped[int] = mapped_column(Integer)
    selected_candidate: Mapped[int] = mapped_column(Integer)  # Index of the selected candidate

    def __repr__(self):
        return f"<ReRankerUsage(num_candidates='{self.num_candidates}', selected_candidate='{self.selected_candidate}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'reranker',
    }
