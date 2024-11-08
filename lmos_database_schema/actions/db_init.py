from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy_utils import database_exists, create_database, drop_database
from sqlalchemy.engine.url import make_url
from sqlalchemy import text
import asyncio
from typing import Optional

from ..tables import Base

async def init_database(db_url: str) -> None:
    """
    Initialize the database if it doesn't exist.
    This has to be done with a sync connection first.
    """
    url = make_url(db_url)
    sync_url = url.set(drivername="postgresql")
    
    if not database_exists(sync_url):
        create_database(sync_url)
        print(f"Created database '{url.database}'")
    else:
        print(f"Database '{url.database}' already exists")

async def drop_database(db_url: str) -> None:
    """
    Drop the entire database.
    This has to be done with a sync connection.
    """
    url = make_url(db_url)
    sync_url = url.set(drivername="postgresql")
    
    if database_exists(sync_url):
        drop_database(sync_url)
        print(f"Dropped database '{url.database}'")
    else:
        print(f"Database '{url.database}' does not exist")

async def create_schema(db_url: str, schema_name: Optional[str] = None) -> None:
    """
    Create all tables in the specified schema.
    If no schema is specified, creates in public schema.
    """
    engine = create_async_engine(db_url)
    
    try:
        if schema_name:
            async with engine.begin() as conn:
                await conn.execute(CreateSchema(schema_name, if_not_exists=True))
                print(f"Created schema '{schema_name}'")
                
            # Set search path for table creation
            async with engine.begin() as conn:
                await conn.execute(text(f"SET search_path TO {schema_name}, public"))
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Created all database tables")
        
    finally:
        await engine.dispose()

async def drop_tables(db_url: str, schema_name: Optional[str] = None) -> None:
    """
    Drop all tables in the specified schema.
    If no schema is specified, drops from public schema.
    """
    engine = create_async_engine(db_url)
    
    try:
        if schema_name:
            async with engine.begin() as conn:
                await conn.execute(text(f"SET search_path TO {schema_name}, public"))
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("Dropped all database tables")
        
        if schema_name:
            async with engine.begin() as conn:
                await conn.execute(DropSchema(schema_name, cascade=True))
                print(f"Dropped schema '{schema_name}'")
                
    finally:
        await engine.dispose()

async def verify_schema(db_url: str, schema_name: Optional[str] = None) -> bool:
    """
    Verify that all tables exist and have correct structure.
    Returns True if verification passes.
    """
    engine = create_async_engine(db_url)
    
    try:
        if schema_name:
            async with engine.begin() as conn:
                await conn.execute(text(f"SET search_path TO {schema_name}, public"))
        
        # Get all table names from metadata
        expected_tables = set(Base.metadata.tables.keys())
        
        # Get actual tables from database
        async with engine.begin() as conn:
            if schema_name:
                result = await conn.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    f"WHERE table_schema = '{schema_name}'"
                ))
            else:
                result = await conn.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
            
            actual_tables = set(row[0] for row in result)
        
        missing_tables = expected_tables - actual_tables
        
        if missing_tables:
            print(f"Missing tables: {missing_tables}")
            return False
        
        print("Schema verification passed")
        return True
        
    finally:
        await engine.dispose()

async def reset_schema(db_url: str, schema_name: Optional[str] = None) -> None:
    """
    Drop and recreate all tables (fresh start).
    """
    await drop_tables(db_url, schema_name)
    await create_schema(db_url, schema_name)
    print("Schema reset completed")

if __name__ == "__main__":
    async def main():
        db_url = "postgresql+asyncpg://postgres:postgres@localhost/lmos"
        
        # Initialize database
        await init_database(db_url)
        
        # Reset schema (drop and recreate)
        await reset_schema(db_url)
        
        # Verify schema
        await verify_schema(db_url)

    asyncio.run(main())
