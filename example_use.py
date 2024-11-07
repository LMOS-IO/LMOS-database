import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from lmos_database_schema.actions import (
    get_model_by_name, get_api_key_permissions, check_model_access,
    grant_model_access, revoke_model_access, create_api_key, 
    delete_api_key, get_all_models, create_model
)

# Database settings
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/test_db"
REDIS_URL = 'redis://localhost'

# Set up async engine and session for PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Example functions calling the actions in actions.py 

async def main():
    async with AsyncSessionLocal() as session:
        # Create a model
        print("--- Creating Model ---")
        new_model = await create_model(session, name="GPT-4", permission_bit=0)
        print(f"Model Created: {new_model}")

        # Get all models
        print("\n--- Getting All Models ---")
        models = await get_all_models(session)
        print("Models:", models)

        # Fetch a model by name
        print("\n--- Fetching Model by Name ---")
        fetched_model = await get_model_by_name(session, model_name="GPT-4")
        print(f"Model Found: {fetched_model}")

        # Create User
        print("\n--- Creating User ---")
        # TODO resume implementation
        raise NotImplementedError("User creation and management is not implemented yet.")


        # Creating an API Key
        print("\n--- Creating API Key ---")
        user_id = 123
        example_hash_512 = "0" * 512
        new_api_key = await create_api_key(session, user_id, api_hash=example_hash_512)
        print(f"API Key Created: {new_api_key}")

        # Grant model access to the API key
        print("\n--- Granting Access ---")
        granted = await grant_model_access(session, new_api_key.key_hash, "GPT-4")
        print(f"Access Granted: {granted}")

        # Check if access to model is available for the API key
        print("\n--- Checking Access Permissions ---")
        has_access = await check_model_access(session, new_api_key.key_hash, "GPT-4")
        print(f"API Key has access: {has_access}")

        # Revoke model access from the API key
        print("\n--- Revoking Access ---")
        revoked = await revoke_model_access(session, new_api_key.key_hash, "GPT-4")
        print(f"Access Revoked: {revoked}")

        # Re-check access after revoking
        print("\n--- Checking Access After Revoke ---")
        has_access_after_revoke = await check_model_access(session, new_api_key.key_hash, "GPT-4")
        print(f"API Key has access after revocation: {has_access_after_revoke}")

        # Get API key permissions to see if storage and retrieval works
        print("\n--- Get API Key Permissions ---")
        permissions = await get_api_key_permissions(session, new_api_key.key_hash)
        print(f"API Key Permissions: {permissions}")

        # Delete the API key
        print("\n--- Deleting API Key ---")
        deleted = await delete_api_key(session, new_api_key.key_hash)
        print(f"API Key Deleted: {deleted}")

        # Re-check access after deletion
        print("\n--- Checking Non-existent API Key Access ---")
        has_access_deleted = await check_model_access(session, new_api_key.key_hash, "GPT-4")
        print(f"API Key has access after deletion: {has_access_deleted}")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
