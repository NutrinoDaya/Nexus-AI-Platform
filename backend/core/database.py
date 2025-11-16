"""
NexusAI Platform - Database Module (MongoDB Only)
Redirects to MongoDB implementation for backward compatibility
"""

from backend.core.mongodb import (
    get_database,
    connect_to_mongodb as init_mongodb,
    close_mongodb_connection,
    get_mongodb_client,
)

# Maintain backward compatibility with function names
init_database = init_mongodb
close_database = close_mongodb_connection
get_db = get_database  # For legacy code compatibility

__all__ = [
    "get_database",
    "init_mongodb", 
    "close_mongodb_connection",
    "get_mongodb_client",
    "init_database",  # Alias
    "close_database",  # Alias
    "get_db",  # Alias
]
