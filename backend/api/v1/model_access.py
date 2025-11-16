"""
Model Access Control API Routes

This module handles granting, revoking, and managing user access to AI models.
Provides granular permissions (use, view, edit, delete) with expiration support.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.mongodb import get_database
from backend.core.security import get_current_user
from backend.models.mongodb_models import UserModel, ModelDocument, ModelAccessDocument, UserRole
from backend.models.schemas import (
    ModelAccessCreate,
    ModelAccessUpdate,
    ModelAccessResponse,
    MessageResponse
)

router = APIRouter(prefix="/models/{model_id}/access", tags=["model-access"])


@router.post("", response_model=ModelAccessResponse, status_code=status.HTTP_201_CREATED)
async def grant_model_access(
    model_id: str,
    access_data: ModelAccessCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserModel = Depends(get_current_user)
):
    """Grant a user access to a model with specific permissions"""
    # Check if model exists
    model = await db.models.find_one({"_id": model_id})
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and model["created_by"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owners and admins can grant access"
        )
    
    # Check if target user exists
    target_user = await db.users.find_one({"_id": access_data.user_id})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found"
        )
    
    # Check if access already exists
    existing_access = await db.model_access.find_one({
        "user_id": access_data.user_id,
        "model_id": model_id
    })
    
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Access already granted to this user. Use PATCH to update permissions."
        )
    
    # Create new access
    new_access = ModelAccessDocument(
        user_id=access_data.user_id,
        model_id=model_id,
        can_use=access_data.can_use,
        can_view=access_data.can_view,
        can_edit=access_data.can_edit,
        can_delete=access_data.can_delete,
        granted_by_id=current_user.id,
        expires_at=access_data.expires_at,
        notes=access_data.notes
    )
    
    await db.model_access.insert_one(new_access.dict(by_alias=True))
    
    return new_access


@router.get("", response_model=List[ModelAccessResponse])
async def list_model_access(
    model_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_expired: bool = Query(False),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    List all users with access to a model.
    
    Only model owners, admins, or users with view permission can list access.
    
    Args:
        model_id: UUID of the model
        skip: Number of records to skip (pagination)
        limit: Maximum records to return
        include_expired: Include expired access grants
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of ModelAccess objects
        
    Raises:
        404: Model not found
        403: User lacks permission to view access
    """
    # Check if model exists
    model = await db.models.find_one({"_id": str(model_id)})
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Check permissions
    is_owner = model.get("created_by") == current_user.get("id")
    is_admin = current_user.get("role") == UserRole.ADMIN
    
    # Check if user has view permission
    user_access = await db.model_access.find_one({
        "user_id": current_user.get("id"),
        "model_id": str(model_id),
        "can_view": True
    })
    
    if not (is_owner or is_admin or user_access):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view access for this model"
        )
    
    # Build query filter
    query_filter = {"model_id": str(model_id)}
    
    # Filter expired if requested
    if not include_expired:
        query_filter["$or"] = [
            {"expires_at": None},
            {"expires_at": {"$gt": datetime.utcnow()}}
        ]
    
    # Apply pagination
    cursor = db.model_access.find(query_filter).skip(skip).limit(limit)
    accesses = await cursor.to_list(length=limit)
    
    return accesses


@router.get("/{user_id}", response_model=ModelAccessResponse)
async def get_user_model_access(
    model_id: UUID,
    user_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get specific user's access to a model.
    
    Args:
        model_id: UUID of the model
        user_id: UUID of the user
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ModelAccess object
        
    Raises:
        404: Model or access not found
        403: User lacks permission to view access
    """
    # Check if model exists
    model = await db.models.find_one({"_id": str(model_id)})
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Check permissions
    is_owner = model.get("created_by") == current_user.get("id")
    is_admin = current_user.get("role") == UserRole.ADMIN
    is_self = current_user.get("id") == str(user_id)
    
    if not (is_owner or is_admin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this access"
        )
    
    # Get access
    access = await db.model_access.find_one({
        "user_id": str(user_id),
        "model_id": str(model_id)
    })
    
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access not found"
        )
    
    return access


@router.patch("/{user_id}", response_model=ModelAccessResponse)
async def update_model_access(
    model_id: UUID,
    user_id: UUID,
    access_data: ModelAccessUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Update user's access permissions to a model.
    
    Only model owners and admins can update access.
    
    Args:
        model_id: UUID of the model
        user_id: UUID of the user
        access_data: Updated permissions
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated ModelAccess object
        
    Raises:
        404: Model or access not found
        403: User lacks permission to update access
    """
    # Check if model exists
    model = await db.models.find_one({"_id": str(model_id)})
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and model.get("created_by") != current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owners and admins can update access"
        )
    
    # Get existing access
    access = await db.model_access.find_one({
        "user_id": str(user_id),
        "model_id": str(model_id)
    })
    
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access not found"
        )
    
    # Update fields
    update_data = access_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.model_access.update_one(
        {"user_id": str(user_id), "model_id": str(model_id)},
        {"$set": update_data}
    )
    
    # Retrieve updated document
    updated_access = await db.model_access.find_one({
        "user_id": str(user_id),
        "model_id": str(model_id)
    })
    
    return updated_access


@router.delete("/{user_id}", response_model=MessageResponse)
async def revoke_model_access(
    model_id: UUID,
    user_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Revoke a user's access to a model.
    
    Only model owners and admins can revoke access.
    
    Args:
        model_id: UUID of the model
        user_id: UUID of the user
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Success message
        
    Raises:
        404: Model or access not found
        403: User lacks permission to revoke access
    """
    # Check if model exists
    model = await db.models.find_one({"_id": str(model_id)})
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Check permissions
    if current_user.get("role") != UserRole.ADMIN and model.get("created_by") != current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owners and admins can revoke access"
        )
    
    # Get access
    access = await db.model_access.find_one({
        "user_id": str(user_id),
        "model_id": str(model_id)
    })
    
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access not found"
        )
    
    await db.model_access.delete_one({
        "user_id": str(user_id),
        "model_id": str(model_id)
    })
    
    return MessageResponse(message="Access revoked successfully")
