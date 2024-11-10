import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis.asyncio.client import Redis
from lmos_database.actions.user import(
    create_user, get_user_by_username, get_user_by_email, get_user_by_id, get_all_users, delete_user_by_id, delete_user_by_username
)

from lmos_database.actions.model import (
    create_model, get_model_by_name, get_model_by_id, get_all_models, delete_model_by_id, delete_model_by_name
)

from lmos_database.actions.apikey import (
    create_api_key, get_api_keys_by_user, delete_api_key_by_hash, disable_api_key_by_hash
)

from lmos_database.actions.permissions import (
    grant_model_access, revoke_model_access, get_api_permissions
)

from lmos_database.actions.usage import (
    create_llm_usage, get_usage_by_api_key, create_stt_usage, create_bulk_usage, get_usage_by_model_and_api_key, LLMUsageEntry, get_usage_by_model, create_reranker_usage, create_tts_usage
)

from lmos_database.actions.rate_limit import (
    record_ratelimit_usage, get_current_limits
)

from lmos_database.actions.hash import (
    hash_str
)

from lmos_database.actions.redis_access_cache import close_redis

logging.basicConfig()
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)


# Database settings
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/lmos"
REDIS_URL = 'redis://localhost'

# Set up async engine and session for PostgreSQL
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
redis_client = Redis(
    host='127.0.0.1', port=6379, decode_responses=True,
    db=0, password=None
)

# Example functions calling the actions in actions.py

async def main():
    async with AsyncSessionLocal() as session:
        # Collect all users
        print("\n--- Getting All Users to delete ---")
        users = await get_all_users(session)
        for user in users:
            await delete_user_by_username(session, user.username)
            print(f"    Deleted User: {user.username}")


        # Create User
        print("\n--- Creating User ---")
        new_user = await create_user(
            session,
            username="TestAccount",
            email="test@test.com",
            password_hash="test"
        )
        print(f"    User Created: {new_user}")

        # Create User
        print("\n--- Creating User ---")
        new_user = await create_user(
            session,
            username="TestAccount2",
            email="test2@test.com",
            password_hash="test"
        )
        print(f"    User Created: {new_user}")

        # Collect a specific user for deleting via id
        print("\n--- Fetching User by Username ---")
        fetched_user_delete = await get_user_by_username(session, username="TestAccount2")
        print(f"    User Found: {fetched_user_delete}")

        # Collect all user
        print("\n--- Getting All Users ---")
        users = await get_all_users(session)
        for user in users:
            print(f"   {user}")

        # Delete via ID
        print("\n--- Delete by ID ---")
        deleted_user_by_id = await delete_user_by_id(session, fetched_user_delete.id)
        print(f"   User Deleted by ID: {deleted_user_by_id}")

        # Collect a specific user
        print("\n--- Fetching User by Username ---")
        fetched_user = await get_user_by_username(session, username="TestAccount")
        print(f"    User Found: {fetched_user}")

        # Collect a specific user via email
        print("\n--- Fetching User by Email ---")
        fetched_user = await get_user_by_email(session, "test@test.com")
        print(f"    User Found: {fetched_user}")

        # Collect a specific user via id
        print("\n--- Fetching User by ID ---")
        fetched_user = await get_user_by_id(session, fetched_user.id)
        print(f"    User Found: {fetched_user}")

        # Create a model
        print("--- Creating Model ---")
        new_model = await create_model(session, name="GPT-4", permission_bit=0)
        print(f"    Model Created: {new_model}")

        # Get all models
        print("\n--- Getting All Models ---")
        models = await get_all_models(session)
        print("Models:")
        for model in models:
            print(f"   {model}")

        # Fetch a model by name
        print("\n--- Fetching Model by Name ---")
        fetched_model = await get_model_by_name(session, model_name="GPT-4")
        print(f"    Model Found: {fetched_model}")

        # Fetch a model by id
        print("\n--- Fetching Model by ID ---")
        fetched_model = await get_model_by_id(session, fetched_model.id)
        print(f"    Model Found: {fetched_model}")

        # Get all api keys for the test user and delete them
        print("\n--- Getting API Keys for User ---")
        api_keys = await get_api_keys_by_user(session, fetched_user.id)
        for api_key in api_keys:
            await delete_api_key_by_hash(session, api_key.key_hash)
            print(f"    Deleted API Key: {api_key.key_hash}")

        # Creating an API Key
        print("\n--- Creating API Key ---")
        user_id = fetched_user.id
        new_api_key = await create_api_key(session, user_id)
        hashed_key = hash_str(new_api_key, is_api_key=True)
        print(f"    API Key Created: {new_api_key}")

        # Grant model access to the API key
        print("\n--- Granting Access ---")
        granted = await grant_model_access(
            session, redis_client, hashed_key, "GPT-4",
            requests_per_minute=60, resource_quota_per_minute=60
        )
        print(f"    Access Granted: {granted}")

        # Apply some llm usage
        entry1 = LLMUsageEntry(
            model_name="GPT-4",
            api_key_hash=hashed_key,
            status_code=200,
            new_prompt_tokens=100,
            cache_prompt_tokens=0,
            generated_tokens=50,
            schema_gen_tokens=0,
        )
        entry2 = LLMUsageEntry(
            model_name="GPT-4",
            api_key_hash=hashed_key,
            status_code=200,
            new_prompt_tokens=100,
            cache_prompt_tokens=0,
            generated_tokens=50,
            schema_gen_tokens=0,
        )
        print("\n--- Creating LLM Usage ---")

        usage = await create_llm_usage(
            session,
            entry1
        )
        print(f"    LLM Usage Created: {usage}")

        # Create bulk usage
        print("\n--- Creating Bulk LLM Usage ---")
        entries = [entry1, entry2]
        await create_bulk_usage(session, entries)

        # Get usage by model and API key
        print("\n--- Getting Usage by Model and API Key ---")
        usage_by_model_and_api_key = await get_usage_by_model_and_api_key(
            session, hashed_key, "GPT-4", page=1, limit=10)
        for usage_row in usage_by_model_and_api_key:
            print(f"    Usage: {usage_row}")

        # Get usage by model
        print("\n--- Getting Usage by Model ---")
        usage_by_model = await get_usage_by_model(session, "GPT-4", page=1, limit=10)
        for usage_row in usage_by_model:
            print(f"    Usage: {usage_row}")

        # Get usage by API key but with a limit of 2 per page and loop
        print("\n--- Getting Usage by API Key with Pagination ---")
        for page in range(1, 3):  # Assuming there are more than 2 pages
            usage_by_api_key = await get_usage_by_api_key(session, hashed_key, page=page, limit=2)
            print(f"    Usage Page {page}: {usage_by_api_key}")
            if len(usage_by_api_key) < 2:
                break

        # Record usage
        print("\n--- Recording Rate Limit Usage ---")
        await record_ratelimit_usage(redis_client, "key123", "gpt-4", 150)  # 150 tokens

        # # Check current usage
        print("\n--- Getting Current Rate Limits ---")
        rl_usage = await get_current_limits(redis_client, "key123", "gpt-4")
        print(f"    Requests this minute: {rl_usage.current_requests_per_minute}")
        print(f"    Resources this minute: {rl_usage.current_resource_quota_per_minute}")
        print(f"    Window resets in: {rl_usage.remaining_seconds} seconds")

        # Wait for the rate limit to reset
        print("\n--- Waiting for Rate Limit Reset ---")
        await asyncio.sleep(rl_usage.remaining_seconds + 1) # Wait for the rate limit to reset

        # Rechecking rate limit after waiting
        print("\n--- Getting Current Rate Limits After Waiting ---")
        rl_usage = await get_current_limits(redis_client, "key123", "gpt-4")
        print(f"    Requests this minute: {rl_usage.current_requests_per_minute}")
        print(f"    Resources this minute: {rl_usage.current_resource_quota_per_minute}")
        print(f"    Window resets in: {rl_usage.remaining_seconds} seconds")

        
        # Get Usage by API Key
        print("\n--- Getting Usage by API Key ---")
        usage_by_api_key = await get_usage_by_api_key(session, hashed_key)
        print(f"    Usage by API Key: {usage_by_api_key}")

        # Check if access to model is available for the API key
        print("\n--- Checking Access Permissions ---")
        has_access = await get_api_permissions(session, redis_client, hashed_key)
        print(f"    API Key has access: {has_access}")

        # Revoke model access from the API key
        print("\n--- Revoking Access ---")
        revoked = await revoke_model_access(session, redis_client, hashed_key, "GPT-4")
        print(f"    Access Revoked: {revoked}")

        # Re-check access after revoking
        print("\n--- Checking Access After Revoke ---")
        has_access_after_revoke = await get_api_permissions(session, redis_client, hashed_key)
        print(f"    API Key has access after revocation: {has_access_after_revoke}")

        # Disabling API Key
        print("\n--- Disabling API Key ---")
        disabled = await disable_api_key_by_hash(session, redis_client, hashed_key)
        print(f"    API Key Disabled: {disabled}")

        # Re-check access after disabling
        print("\n--- Checking Disabled API Key Access ---")
        has_access_disabled = await get_api_permissions(session, redis_client, hashed_key)
        print(f"    API Key has access after disabling: {has_access_disabled}")

        # Delete the API key
        print("\n--- Deleting API Key ---")
        deleted = await delete_api_key_by_hash(session, redis_client, hashed_key)
        print(f"    API Key Deleted: {deleted}")

        # Re-check access after deletion
        print("\n--- Checking Non-existent API Key Access ---")
        has_access_deleted = await get_api_permissions(session, redis_client, hashed_key)
        print(f"    API Key has access after deletion: {has_access_deleted}")

        # Delete the user
        print("\n--- Deleting User ---")
        await delete_user_by_username(session, "TestAccount")
        print("    User Deleted")

        # Re-check if user exists
        print("\n--- Checking Non-existent User ---")
        fetched_user_deleted = await get_user_by_username(session, username="TestAccount")
        print(f"   User Found: {fetched_user_deleted}")

        # Delete the model
        print("\n--- Deleting Model ---")
        await delete_model_by_name(session, "GPT-4")
        print("    Model Deleted")

        # Re-check if model exists
        print("\n--- Checking Non-existent Model ---")
        fetched_model_deleted = await get_model_by_name(session, model_name="GPT-4")
        print(f"   Model Found: {fetched_model_deleted}")

        # Close the session
        await session.close()
        await close_redis(redis_client)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
