from lmos_database_schema.actions.db_init import init_database, reset_schema, verify_schema
import asyncio

async def main():
    db_url = "postgresql+asyncpg://postgres:postgres@localhost/lmos"
    
    # Initialize database
    await init_database(db_url)
    
    # Reset schema (drop and recreate)
    await reset_schema(db_url)
    
    # Verify schema
    await verify_schema(db_url)

asyncio.run(main())
