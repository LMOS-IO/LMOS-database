from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from lmos_database_schema.tables import Base

# Database connection URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/test_db"

def create_schema():
    # Create the engine
    engine = create_engine(DATABASE_URL)
    
    # Create database if it doesn't exist
    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Created database 'test_db'")
    else:
        print(f"Database 'test_db' already exists")

    # Create all tables
    Base.metadata.create_all(engine)
    print("Created all database tables")

def drop_schema():
    # Create the engine
    engine = create_engine(DATABASE_URL)
    
    # Drop all tables
    Base.metadata.drop_all(engine)
    print("Dropped all database tables")

if __name__ == "__main__":
    #drop_schema()
    create_schema()