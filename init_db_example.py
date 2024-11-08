from lmos_database.actions.db_init import lmos_init_database, lmos_reset_schema, lmos_verify_schema
import asyncio

async def main():
    db_url = "postgresql+asyncpg://postgres:postgres@localhost/lmos"
    
    # Initialize database
    await lmos_init_database(db_url)
    
    # Reset schema (drop and recreate)
    await lmos_reset_schema(db_url)
    
    # Verify schema
    await lmos_verify_schema(db_url)

asyncio.run(main())
