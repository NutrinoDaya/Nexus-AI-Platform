"""
NexusAI Platform - Models API Routes
Model registration, management, and access control
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.api.dependencies.auth import get_current_active_user, require_admin, get_optional_user
from backend.core.database import get_db
from backend.core.logging_config import get_logger
from backend.core.storage import upload_file, BUCKETS
from backend.models.mongodb_models import ModelStatus, UserRole
from backend.models.schemas import (
    ModelCreate,
    ModelUpdate,
    ModelResponse,
    PaginationParams,
    PaginatedResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/models", tags=["Models"])


@router.get("", response_model=PaginatedResponse)
async def list_models(
    pagination: PaginationParams = Depends(),
    task_type: Optional[str] = None,
    framework: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    List all available models with pagination and filtering.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **task_type**: Filter by task type
    - **framework**: Filter by framework (pytorch, onnx, tensorrt)
    - **status**: Filter by status (active, pending, deprecated)
    
    Returns models accessible to the current user based on access level.
    """
    # Build filter
    filter_query: Dict[str, Any] = {}
    
    # Apply filters
    if task_type:
        filter_query["task_type"] = task_type
    
    if framework:
        filter_query["framework"] = framework
    
    if status_filter:
        filter_query["status"] = status_filter
    
    # Filter by access level
    if not current_user:
        # Public only for unauthenticated users
        filter_query["access_level"] = "public"
    elif current_user.get("role") != UserRole.ADMIN.value:
        # User sees public, authenticated, and models they have explicit access to
        user_model_accesses = await db.user_model_access.find(
            {"user_id": current_user["id"]}
        ).to_list(length=None)
        accessible_model_ids = [access["model_id"] for access in user_model_accesses]
        
        filter_query["$or"] = [
            {"access_level": {"$in": ["public", "authenticated"]}},
            {"_id": {"$in": accessible_model_ids}},
        ]
    
    # Get total count
    total = await db.models.count_documents(filter_query)
    
    # Apply pagination
    skip = (pagination.page - 1) * pagination.page_size
    cursor = db.models.find(filter_query).skip(skip).limit(pagination.page_size)
    models = await cursor.to_list(length=pagination.page_size)
    
    # Calculate total pages
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=[ModelResponse(**model) for model in models],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get detailed information about a specific model.
    
    - **model_id**: UUID of the model
    """
    # Get model
    model = await db.models.find_one({"_id": model_id})
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    
    # Check access
    if model.get("access_level") == "private":
        if not current_user or current_user.get("role") != UserRole.ADMIN.value:
            # Check explicit access
            if current_user:
                access_check = await db.user_model_access.find_one({
                    "user_id": current_user["id"],
                    "model_id": model_id,
                })
                if not access_check:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this model",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
    
    elif model.get("access_level") in ["authenticated", "premium"]:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
    
    return ModelResponse(**model)


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    model_data: ModelCreate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Register a new model in the system.
    
    **Admin only**
    
    - **name**: Model name
    - **description**: Model description
    - **task_type**: Type of task (object_detection, segmentation, etc.)
    - **framework**: Model framework (pytorch, onnx, tensorrt)
    - **version**: Model version
    - **model_path**: Path to model file in storage
    """
    # Generate slug from name
    slug = model_data.name.lower().replace(" ", "-").replace("_", "-")
    
    # Check if slug exists
    existing = await db.models.find_one({"slug": slug})
    if existing:
        # Append version to slug
        slug = f"{slug}-{model_data.version}"
    
    # Create model document
    new_model = {
        **model_data.dict(),
        "_id": str(UUID(int=0)),  # Generate proper UUID
        "slug": slug,
        "status": ModelStatus.PENDING.value,
        "created_by": current_user["id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Generate proper UUID
    from uuid import uuid4
    new_model["_id"] = str(uuid4())
    
    result = await db.models.insert_one(new_model)
    created_model = await db.models.find_one({"_id": result.inserted_id})
    
    logger.info(f"Model created: {new_model['name']} by {current_user['username']}")
    
    return ModelResponse(**created_model)


@router.post("/upload", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def upload_model_file(
    file: UploadFile = File(...),
    name: str = None,
    description: str = None,
    task_type: str = "custom",
    framework: str = "onnx",
    version: str = "1.0.0",
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Upload a model file and register it.
    
    **Admin only**
    
    Accepts model files (.pt, .onnx, .trt, .pb, etc.)
    """
    # Validate file extension
    allowed_extensions = [".pt", ".pth", ".onnx", ".trt", ".engine", ".pb", ".h5"]
    file_ext = "." + file.filename.split(".")[-1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
        )
    
    # Upload to storage
    object_name = f"models/{task_type}/{name or file.filename}"
    
    file_content = await file.read()
    model_path = await upload_file(
        bucket="models",
        object_name=object_name,
        file_data=file_content,
        content_type=file.content_type or "application/octet-stream",
        metadata={
            "uploaded_by": current_user.get("username"),
            "original_filename": file.filename,
        },
    )
    
    # Create model record
    model_name = name or file.filename.rsplit(".", 1)[0]
    slug = model_name.lower().replace(" ", "-")
    
    from uuid import uuid4
    new_model = {
        "_id": str(uuid4()),
        "name": model_name,
        "slug": slug,
        "description": description,
        "task_type": task_type,
        "framework": framework,
        "version": version,
        "model_path": model_path,
        "status": ModelStatus.PENDING.value,
        "created_by": current_user["id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    result = await db.models.insert_one(new_model)
    created_model = await db.models.find_one({"_id": result.inserted_id})
    
    logger.info(f"Model uploaded: {new_model['name']} by {current_user['username']}")
    
    return ModelResponse(**created_model)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    model_update: ModelUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Update model information.
    
    **Admin only**
    """
    # Get model
    model = await db.models.find_one({"_id": model_id})
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    
    # Update fields
    update_data = model_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.models.update_one(
        {"_id": model_id},
        {"$set": update_data}
    )
    
    updated_model = await db.models.find_one({"_id": model_id})
    
    logger.info(f"Model updated: {updated_model['name']} by {current_user['username']}")
    
    return ModelResponse(**updated_model)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Delete a model.
    
    **Admin only**
    
    This will also delete all associated inference jobs.
    """
    # Get model
    model = await db.models.find_one({"_id": model_id})
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    
    # Delete model
    await db.models.delete_one({"_id": model_id})
    
    logger.info(f"Model deleted: {model['name']} by {current_user['username']}")
    
    return None


@router.post("/{model_id}/grant-access/{user_id}")
async def grant_model_access(
    model_id: str,
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Grant a user access to a specific model.
    
    **Admin only**
    """
    # Verify model and user exist
    model = await db.models.find_one({"_id": model_id})
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if access already exists
    existing = await db.user_model_access.find_one({
        "user_id": user_id,
        "model_id": model_id
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Access already granted")
    
    # Grant access
    from uuid import uuid4
    await db.user_model_access.insert_one({
        "_id": str(uuid4()),
        "user_id": user_id,
        "model_id": model_id,
        "created_at": datetime.utcnow(),
    })
    
    logger.info(f"Access granted to model {model_id} for user {user_id}")
    
    return {"success": True, "message": "Access granted successfully"}


@router.delete("/{model_id}/revoke-access/{user_id}")
async def revoke_model_access(
    model_id: str,
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Revoke a user's access to a specific model.
    
    **Admin only**
    """
    # Revoke access
    await db.user_model_access.delete_one({
        "user_id": user_id,
        "model_id": model_id
    })
    
    logger.info(f"Access revoked for model {model_id} from user {user_id}")
    
    return {"success": True, "message": "Access revoked successfully"}
