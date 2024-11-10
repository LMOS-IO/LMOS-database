from lmos_database.actions.db_init import lmos_init_database, lmos_reset_schema, lmos_verify_schema
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis.asyncio.client import Redis

from lmos_database.actions.user import create_user
from lmos_database.actions.model import create_model
from lmos_database.actions.apikey import create_api_key
from lmos_database.actions.permissions import grant_model_access
from lmos_database.actions.hash import hash_str

# Database settings
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres/lmos"
REDIS_URL = 'redis://redis'

# Set up async engine and session for PostgreSQL
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

async def create_user_and_key():
    async with AsyncSessionLocal() as session:
        print("\n--- Creating User ---")
        new_user = await create_user(
            session,
            username="TestAccount",
            email="test@test.com",
            password_hash=hash_str("1234"),
        )
        print(f"User created: {new_user}")

        print("--- Creating Model ---")
        new_model = await create_model(session, name="GPT-4", permission_bit=0)

        print("--- Creating APIKEY ---")
        new_api_key = await create_api_key(session, user_id=new_user.id)
        print("\n\nAPIKEY:")
        print(new_api_key)
        print("\n\n--- Granting Model Access ---")
        await grant_model_access(session, user_id=new_user.id, model_id=new_model.id)
        print("--- Done ---")

async def main():
    # Initialize database
    await lmos_init_database(DATABASE_URL)
    
    # Reset schema (drop and recreate)
    await lmos_reset_schema(DATABASE_URL)
    
    # Verify schema
    await lmos_verify_schema(DATABASE_URL)

    # Create user and API key
    await create_user_and_key()
    # Close the session
    await redis_client.close()

asyncio.run(main())
