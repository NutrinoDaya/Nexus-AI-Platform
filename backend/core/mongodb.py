"""
MongoDB Database Connection and Configuration

This module handles MongoDB connection management using Motor (async MongoDB driver).
Provides database instance and helper functions for database operations.
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid
import logging

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Global MongoDB client and database instances
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongodb() -> None:
    """
    Establish connection to MongoDB database.
    
    Creates indexes for optimal query performance on frequently accessed fields.
    Called during application startup.
    """
    global _client, _database
    
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")
        
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            serverSelectionTimeoutMS=5000
        )
        
        _database = _client[settings.MONGODB_DB_NAME]
        
        # Test the connection
        await _client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongodb_connection() -> None:
    """
    Close MongoDB connection.
    
    Called during application shutdown to cleanly close all connections.
    """
    global _client
    
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """
    Get the MongoDB database instance.
    
    Returns:
        AsyncIOMotorDatabase: The database instance
        
    Raises:
        RuntimeError: If database connection hasn't been established
    """
    if _database is None:
        raise RuntimeError("Database connection not established. Call connect_to_mongodb() first.")
    return _database


async def create_indexes() -> None:
    """
    Create database indexes for optimal query performance.
    
    Performance-optimized indexes for common query patterns:
    - Users: Fast lookups by username/email, filtering by role/status
    - Models: Framework filtering, ownership queries, status filtering
    - InferenceJobs: User + time range queries, status filtering
    - Cameras: Owner queries, status filtering, analytics queries
    - CameraEvents: Time-based queries, camera + event type filtering
    """
    db = get_database()
    
    try:
        # Users collection indexes
        await db.users.create_indexes([
            IndexModel([("username", ASCENDING)], unique=True),
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("role", ASCENDING), ("is_active", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)])
        ])
        
        # Models collection indexes  
        await db.models.create_indexes([
            IndexModel([("name", ASCENDING)]),
            IndexModel([("framework", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("created_by", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("tags", ASCENDING)])  # For tag-based filtering
        ])
        
        # ModelAccess collection indexes
        await db.model_access.create_indexes([
            IndexModel([("user_id", ASCENDING), ("model_id", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING), ("can_use", ASCENDING)]),
            IndexModel([("model_id", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)])  # TTL cleanup
        ])
        
        # InferenceJobs collection indexes
        await db.inference_jobs.create_indexes([
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),  # User history
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),  # Status filtering
            IndexModel([("model_id", ASCENDING), ("created_at", DESCENDING)]),  # Model usage
            IndexModel([("created_at", DESCENDING)]),  # Recent jobs
            # TTL index for auto-cleanup of old jobs (30 days)
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=2592000)
        ])
        
        # Cameras collection indexes
        await db.cameras.create_indexes([
            IndexModel([("owner_id", ASCENDING)]),
            IndexModel([("status", ASCENDING), ("analytics_enabled", ASCENDING)]),  # Active analytics
            IndexModel([("rtsp_url", ASCENDING)], unique=True),
            IndexModel([("location", ASCENDING)]),  # Geographic filtering
            IndexModel([("created_at", DESCENDING)])
        ])
        
        # CameraEvents collection indexes (NEW - for analytics)
        await db.camera_events.create_indexes([
            IndexModel([("camera_id", ASCENDING), ("created_at", DESCENDING)]),  # Camera timeline
            IndexModel([("event_type", ASCENDING), ("created_at", DESCENDING)]),  # Event filtering
            IndexModel([("camera_id", ASCENDING), ("event_type", ASCENDING)]),  # Camera + type
            # TTL index for auto-cleanup of old events (7 days)
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=604800)
        ])
        
        # Settings collection indexes
        await db.settings.create_indexes([
            IndexModel([("key", ASCENDING)], unique=True),
            IndexModel([("category", ASCENDING)]),
            IndexModel([("updated_at", DESCENDING)])
        ])
        
        logger.info("Successfully created database indexes")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise


async def create_collections() -> None:
    """
    Create MongoDB collections if they don't exist.
    
    Collections created:
    - users: User accounts
    - models: AI model metadata
    - model_access: User permissions for models
    - inference_jobs: Inference task tracking
    - cameras: Camera configurations
    - camera_events: Camera event history
    - audit_logs: System audit trail
    - system_settings: Application settings
    """
    db = get_database()
    
    collections = [
        "users",
        "models",
        "model_access",
        "inference_jobs",
        "cameras",
        "camera_events",
        "audit_logs",
        "system_settings"
    ]
    
    for collection_name in collections:
        try:
            await db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
        except CollectionInvalid:
            # Collection already exists
            logger.debug(f"Collection {collection_name} already exists")
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise


# Helper functions for common database operations

async def get_by_id(collection: str, doc_id: str) -> Optional[dict]:
    """
    Get a document by ID.
    
    Args:
        collection: Collection name
        doc_id: Document ID
        
    Returns:
        Document dict or None if not found
    """
    db = get_database()
    return await db[collection].find_one({"_id": doc_id})


async def insert_one(collection: str, document: dict) -> str:
    """
    Insert a single document.
    
    Args:
        collection: Collection name
        document: Document to insert
        
    Returns:
        Inserted document ID
    """
    db = get_database()
    result = await db[collection].insert_one(document)
    return str(result.inserted_id)


async def update_one(collection: str, doc_id: str, update_data: dict) -> bool:
    """
    Update a single document.
    
    Args:
        collection: Collection name
        doc_id: Document ID
        update_data: Fields to update
        
    Returns:
        True if document was updated, False otherwise
    """
    db = get_database()
    result = await db[collection].update_one(
        {"_id": doc_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


async def delete_one(collection: str, doc_id: str) -> bool:
    """
    Delete a single document.
    
    Args:
        collection: Collection name
        doc_id: Document ID
        
    Returns:
        True if document was deleted, False otherwise
    """
    db = get_database()
    result = await db[collection].delete_one({"_id": doc_id})
    return result.deleted_count > 0


async def count_documents(collection: str, query: dict = None) -> int:
    """
    Count documents matching a query.
    
    Args:
        collection: Collection name
        query: Query filter (default: all documents)
        
    Returns:
        Number of matching documents
    """
    db = get_database()
    return await db[collection].count_documents(query or {})
