from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship, declarative_base
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
    api_requests = relationship("APIRequest", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(key='{self.key}', user_id='{self.user_id}')>"

# API Requests Table
class APIRequest(Base):
    __tablename__ = 'api_requests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(String(512), ForeignKey('api_keys.key'), nullable=False)  # Fixed length of 64 characters
    endpoint = Column(String(512), nullable=False)  # Fixed length of 128 characters
    request_time = Column(DateTime(timezone=True), server_default=func.now())
    status_code = Column(Integer, nullable=False)
    api_key = relationship("APIKey", back_populates="api_requests")
    
    def __repr__(self):
        return f"<APIRequest(endpoint='{self.endpoint}', status_code='{self.status_code}')>"

# Example usage of creating tables
if __name__ == "__main__":
    from sqlalchemy import create_engine

    # Create an SQLite database (replace with your preferred database URI)
    engine = create_engine('sqlite:///example.db', echo=True)
    
    # Create all tables
    Base.metadata.create_all(engine)
