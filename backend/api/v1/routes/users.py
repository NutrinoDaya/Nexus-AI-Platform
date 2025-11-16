"""
NexusAI Platform - User Management API Routes (Admin only)
User CRUD, role management, and activity tracking
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from uuid import uuid4

from backend.core.database import get_db
from backend.core.security import get_password_hash
from backend.core.logging_config import get_logger
from backend.api.dependencies.auth import require_admin
from backend.models.mongodb_models import UserRole
from backend.models.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    PaginationParams,
    PaginatedResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    pagination: PaginationParams = Depends(),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    List all users with pagination and filtering (Admin only)
    
    Filters:
    - role: Filter by user role
    - is_active: Filter by active status
    - search: Search by username, email, or full name
    """
    # Build filter
    filter_query: Dict[str, Any] = {}
    
    if role:
        filter_query["role"] = role
    
    if is_active is not None:
        filter_query["is_active"] = is_active
    
    if search:
        filter_query["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
        ]
    
    # Count total
    total = await db.users.count_documents(filter_query)
    
    # Apply pagination
    skip = (pagination.page - 1) * pagination.page_size
    cursor = db.users.find(filter_query).sort("created_at", -1).skip(skip).limit(pagination.page_size)
    users = await cursor.to_list(length=pagination.page_size)
    
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=[UserResponse(**user) for user in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get user details (Admin only)"""
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(**user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create new user (Admin only)"""
    # Check if username exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    # Check if email exists
    existing_email = await db.users.find_one({"email": user_data.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
    
    # Create user
    user = {
        "_id": str(uuid4()),
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "role": user_data.role or UserRole.USER.value,
        "is_active": True,
        "is_locked": False,
        "failed_login_attempts": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await db.users.insert_one(user)
    
    logger.info(f"User created by admin: {user['username']} (ID: {user['_id']})")
    
    return UserResponse(**user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update user (Admin only)"""
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.users.update_one(
        {"_id": user_id},
        {"$set": update_data}
    )
    
    updated_user = await db.users.find_one({"_id": user_id})
    
    logger.info(f"User updated by admin: {updated_user['username']} (ID: {user_id})")
    
    return UserResponse(**updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete user (Admin only)"""
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent deleting yourself (would need current_user context)
    # This is a safety check that could be enhanced
    
    await db.users.delete_one({"_id": user_id})
    
    logger.info(f"User deleted by admin: {user['username']} (ID: {user_id})")


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Activate user account (Admin only)"""
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {
            "is_active": True,
            "is_locked": False,
            "failed_login_attempts": 0,
            "locked_until": None,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated_user = await db.users.find_one({"_id": user_id})
    
    logger.info(f"User activated by admin: {updated_user['username']} (ID: {user_id})")
    
    return UserResponse(**updated_user)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Deactivate user account (Admin only)"""
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {
            "is_active": False,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated_user = await db.users.find_one({"_id": user_id})
    
    logger.info(f"User deactivated by admin: {updated_user['username']} (ID: {user_id})")
    
    return UserResponse(**updated_user)


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role: str = Query(..., description="New user role"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update user role (Admin only)"""
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    old_role = user.get("role")
    
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {
            "role": role,
            "updated_at": datetime.utcnow(),
        }}
    )
    
    updated_user = await db.users.find_one({"_id": user_id})
    
    logger.info(f"User role updated: {updated_user['username']} ({old_role} -> {role})")
    
    return UserResponse(**updated_user)


@router.get("/{user_id}/activity", response_model=dict)
async def get_user_activity(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get user activity log (Admin only)"""
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get audit logs
    cursor = db.audit_logs.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
    audit_logs = await cursor.to_list(length=limit)
    
    return {
        "user_id": user_id,
        "username": user.get("username"),
        "last_login": user.get("last_login").isoformat() if user.get("last_login") else None,
        "created_at": user.get("created_at").isoformat(),
        "failed_login_attempts": user.get("failed_login_attempts", 0),
        "is_locked": user.get("is_locked", False),
        "activity_logs": [
            {
                "action": log.get("action"),
                "resource_type": log.get("resource_type"),
                "resource_id": log.get("resource_id"),
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None,
                "ip_address": log.get("ip_address"),
                "user_agent": log.get("user_agent"),
                "details": log.get("details"),
            }
            for log in audit_logs
        ],
    }
