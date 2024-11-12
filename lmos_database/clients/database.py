from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from lmos_config import config
from sqlalchemy.orm import sessionmaker

class DatabaseManager:
    def load(self):
        self.engine = create_async_engine(str(config.internal_configuration.database.url))
        self.AsyncSessionLocal = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

db_manager = DatabaseManager()
