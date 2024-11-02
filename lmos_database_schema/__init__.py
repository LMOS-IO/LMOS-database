from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import func
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
    password_hash = Column(String, nullable=False)
    totp_secret = Column(String, nullable=True)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

# API Keys Table
class APIKey(Base):
    __tablename__ = 'api_keys'

    key_hash = Column(String(512), primary_key=True, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="api_keys")
    usages = relationship("Usage", back_populates="api_key", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<APIKey(key='{self.key_hash}', user_id='{self.user_id}')>"

# Model table
class Model(Base):
    __tablename__ = 'model'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    def __repr__(self):
        return f"<Model(name='{self.name}')>"
    
# Voice type table
class VoiceType(Base):
    __tablename__ = 'voice_type'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    tts_usages = relationship("TTSUsage", back_populates="voice")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<VoiceType(name='{self.name}')>"

# Base class for Usage, with polymorphism
class Usage(Base):
    __tablename__ = 'usage'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    model_id = Column(UUID(as_uuid=True), ForeignKey('model.id'))
    model = relationship("Model")
    api_key_id = Column(String(512), ForeignKey('api_keys.key_hash'), nullable=False)
    api_key = relationship("APIKey", back_populates="usages")
    status_code = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f"<Usage(type='{self.type}', timestamp='{self.timestamp}', model_id='{self.model_id}', api_key_id='{self.api_key_id}', status_code='{self.status_code}')>"
    
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
    voice_type = Column(UUID(as_uuid=True), ForeignKey('voice_type.id'))
    voice = relationship("VoiceType", back_populates="tts_usages")
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

    def __repr__(self):
        return f"<ReRankerUsage(num_candidates='{self.num_candidates}', selected_candidate='{self.selected_candidate}')>"

    __mapper_args__ = {
        'polymorphic_identity': 'reranker',
    }