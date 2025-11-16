"""
NexusAI Platform - System Settings API Routes
Dynamic configuration management
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from uuid import uuid4

from backend.core.database import get_db
from backend.core.logging_config import get_logger
from backend.api.dependencies.auth import get_current_active_user, require_admin
from backend.models.mongodb_models import UserRole
from backend.models.schemas import (
    SystemSettingCreate,
    SystemSettingUpdate,
    SystemSettingResponse,
    PaginationParams,
    PaginatedResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=PaginatedResponse[SystemSettingResponse])
async def list_settings(
    pagination: PaginationParams = Depends(),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    List system settings with pagination
    
    Filters:
    - category: Filter by category
    - search: Search by key or description
    """
    # Build filter
    filter_query: Dict[str, Any] = {}
    
    # Non-admin users can only see non-sensitive settings
    if current_user.get("role") != UserRole.ADMIN.value:
        filter_query["is_sensitive"] = False
    
    if category:
        filter_query["category"] = category
    
    if search:
        filter_query["$or"] = [
            {"key": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    
    # Count total
    total = await db.system_settings.count_documents(filter_query)
    
    # Apply pagination
    skip = (pagination.page - 1) * pagination.page_size
    cursor = db.system_settings.find(filter_query).sort([("category", 1), ("key", 1)]).skip(skip).limit(pagination.page_size)
    settings = await cursor.to_list(length=pagination.page_size)
    
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=[SystemSettingResponse(**setting) for setting in settings],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/categories", response_model=List[str])
async def list_categories(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get all setting categories"""
    filter_query = {}
    
    # Non-admin users can only see non-sensitive settings
    if current_user.get("role") != UserRole.ADMIN.value:
        filter_query["is_sensitive"] = False
    
    categories = await db.system_settings.distinct("category", filter_query)
    
    return categories


@router.get("/by-category/{category}", response_model=Dict[str, Any])
async def get_settings_by_category(
    category: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get all settings in a category as key-value pairs"""
    filter_query = {"category": category}
    
    # Non-admin users can only see non-sensitive settings
    if current_user.get("role") != UserRole.ADMIN.value:
        filter_query["is_sensitive"] = False
    
    cursor = db.system_settings.find(filter_query)
    settings = await cursor.to_list(length=None)
    
    # Build key-value dict
    settings_dict = {}
    for setting in settings:
        settings_dict[setting["key"]] = {
            "value": setting.get("value"),
            "data_type": setting.get("data_type"),
            "description": setting.get("description"),
            "is_editable": setting.get("is_editable"),
            "updated_at": setting.get("updated_at").isoformat() if setting.get("updated_at") else None,
        }
    
    return {
        "category": category,
        "settings": settings_dict,
    }


@router.get("/{key}", response_model=SystemSettingResponse)
async def get_setting(
    key: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get setting by key"""
    setting = await db.system_settings.find_one({"key": key})
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    
    # Check if user can view sensitive settings
    if setting.get("is_sensitive") and current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to sensitive setting",
        )
    
    return SystemSettingResponse(**setting)


@router.post(
    "",
    response_model=SystemSettingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_setting(
    setting_data: SystemSettingCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create new setting (Admin only)"""
    # Check if key exists
    existing = await db.system_settings.find_one({"key": setting_data.key})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setting key already exists",
        )
    
    # Create setting
    setting = {
        "_id": str(uuid4()),
        "key": setting_data.key,
        "value": setting_data.value,
        "data_type": setting_data.data_type,
        "category": setting_data.category,
        "description": setting_data.description,
        "is_editable": setting_data.is_editable,
        "is_sensitive": setting_data.is_sensitive,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await db.system_settings.insert_one(setting)
    
    logger.info(f"Setting created: {setting['key']}")
    
    return SystemSettingResponse(**setting)


@router.put("/{key}", response_model=SystemSettingResponse)
async def update_setting(
    key: str,
    setting_data: SystemSettingUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Update setting"""
    setting = await db.system_settings.find_one({"key": key})
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    
    # Check if setting is editable
    if not setting.get("is_editable"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setting is not editable",
        )
    
    # Check permissions for sensitive settings
    if setting.get("is_sensitive") and current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to modify sensitive setting",
        )
    
    # Build update
    update_data = {}
    
    if setting_data.value is not None:
        update_data["value"] = setting_data.value
        update_data["updated_at"] = datetime.utcnow()
    
    # Only admin can update other fields
    if current_user.get("role") == UserRole.ADMIN.value:
        other_data = setting_data.model_dump(exclude_unset=True, exclude={"value"})
        update_data.update(other_data)
    
    await db.system_settings.update_one(
        {"key": key},
        {"$set": update_data}
    )
    
    updated_setting = await db.system_settings.find_one({"key": key})
    
    logger.info(f"Setting updated: {key} by {current_user.get('username')}")
    
    return SystemSettingResponse(**updated_setting)


@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_setting(
    key: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete setting (Admin only)"""
    setting = await db.system_settings.find_one({"key": key})
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    
    # Check if setting is deletable
    if not setting.get("is_editable"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setting cannot be deleted",
        )
    
    await db.system_settings.delete_one({"key": key})
    
    logger.info(f"Setting deleted: {key}")


@router.post("/bulk-update", response_model=dict, dependencies=[Depends(require_admin)])
async def bulk_update_settings(
    updates: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Bulk update multiple settings (Admin only)
    
    Request body: {"setting_key": "new_value", ...}
    """
    updated_count = 0
    errors = []
    
    for key, value in updates.items():
        try:
            setting = await db.system_settings.find_one({"key": key})
            
            if not setting:
                errors.append(f"Setting not found: {key}")
                continue
            
            if not setting.get("is_editable"):
                errors.append(f"Setting not editable: {key}")
                continue
            
            await db.system_settings.update_one(
                {"key": key},
                {"$set": {
                    "value": value,
                    "updated_at": datetime.utcnow(),
                }}
            )
            updated_count += 1
            
        except Exception as e:
            errors.append(f"Error updating {key}: {str(e)}")
    
    logger.info(f"Bulk settings update: {updated_count} updated, {len(errors)} errors")
    
    return {
        "updated": updated_count,
        "errors": errors,
        "total_requested": len(updates),
    }


@router.post("/reset/{key}", response_model=SystemSettingResponse, dependencies=[Depends(require_admin)])
async def reset_setting(
    key: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Reset setting to default value (Admin only)"""
    setting = await db.system_settings.find_one({"key": key})
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    
    # Reset to default (would need default value in model)
    # For now, just log the action
    logger.info(f"Setting reset requested: {key}")
    
    return SystemSettingResponse(**setting)
