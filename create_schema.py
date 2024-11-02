from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from lmos_database_schema import Base

# Database connection URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lmos"

def create_schema():
    # Create the engine
    engine = create_engine(DATABASE_URL)
    
    # Create database if it doesn't exist
    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Created database 'lmos'")
    else:
        print(f"Database 'lmos' already exists")

    # Create all tables
    Base.metadata.create_all(engine)
    print("Created all database tables")

if __name__ == "__main__":
    create_schema()