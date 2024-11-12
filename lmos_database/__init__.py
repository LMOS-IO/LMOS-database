
from .clients.database import db_manager
from .clients.redis import redis_manager

def initialize_services():
    # Initialize database
    db_manager.load()

    # Initialize Redis
    redis_manager.load()

initialize_services()