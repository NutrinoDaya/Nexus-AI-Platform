"""
NexusAI Platform - Camera Management API Routes
Camera CRUD, streaming, and event management
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from uuid import uuid4

from backend.core.database import get_db
from backend.core.logging_config import get_logger
from backend.api.dependencies.auth import get_current_active_user, require_admin
from backend.models.mongodb_models import CameraStatus
from backend.models.schemas import (
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraEventResponse,
    PaginationParams,
    PaginatedResponse,
)
from backend.services.camera.stream_manager import stream_manager

logger = get_logger(__name__)
router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=PaginatedResponse[CameraResponse])
async def list_cameras(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[str] = None,
    group_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    List cameras with pagination and filtering
    
    Filters:
    - status: Filter by camera status
    - group_id: Filter by camera group
    - search: Search by name or location
    """
    # Build filter
    filter_query: Dict[str, Any] = {"user_id": current_user["id"]}
    
    if status_filter:
        filter_query["status"] = status_filter
    
    if group_id:
        filter_query["group_id"] = group_id
    
    if search:
        filter_query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
        ]
    
    # Count total
    total = await db.cameras.count_documents(filter_query)
    
    # Apply pagination
    skip = (pagination.page - 1) * pagination.page_size
    cursor = db.cameras.find(filter_query).skip(skip).limit(pagination.page_size)
    cameras = await cursor.to_list(length=pagination.page_size)
    
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=[CameraResponse(**camera) for camera in cameras],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get camera details"""
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Add stream info if active
    session = stream_manager.get_session(camera_id)
    if session:
        stream_info = session.get_stream_info()
        logger.debug(f"Stream info for camera {camera_id}: {stream_info}")
    
    return CameraResponse(**camera)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_data: CameraCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Create new camera"""
    # Create camera
    camera = {
        "_id": str(uuid4()),
        "user_id": current_user["id"],
        "name": camera_data.name,
        "rtsp_url": camera_data.rtsp_url,
        "location": camera_data.location,
        "manufacturer": camera_data.manufacturer,
        "model": camera_data.model,
        "resolution": camera_data.resolution,
        "fps": camera_data.fps,
        "recording_enabled": camera_data.recording_enabled,
        "motion_detection_enabled": camera_data.motion_detection_enabled,
        "analytics_config": camera_data.analytics_config or {},
        "status": CameraStatus.INACTIVE.value,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await db.cameras.insert_one(camera)
    
    logger.info(f"Camera created: {camera['name']} (ID: {camera['_id']})")
    
    return CameraResponse(**camera)


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: str,
    camera_data: CameraUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Update camera"""
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Update fields
    update_data = camera_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.cameras.update_one(
        {"_id": camera_id},
        {"$set": update_data}
    )
    
    updated_camera = await db.cameras.find_one({"_id": camera_id})
    
    logger.info(f"Camera updated: {updated_camera['name']} (ID: {camera_id})")
    
    return CameraResponse(**updated_camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Delete camera"""
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Stop stream if active
    await stream_manager.remove_camera(camera_id)
    
    # Delete camera
    await db.cameras.delete_one({"_id": camera_id})
    
    logger.info(f"Camera deleted: {camera['name']} (ID: {camera_id})")


@router.post("/{camera_id}/start", response_model=dict)
async def start_camera_stream(
    camera_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Start camera stream"""
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Add to stream manager
    success = await stream_manager.add_camera(camera)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start camera stream",
        )
    
    # Update status
    await db.cameras.update_one(
        {"_id": camera_id},
        {"$set": {
            "status": CameraStatus.ACTIVE.value,
            "last_seen": datetime.utcnow(),
        }}
    )
    
    logger.info(f"Camera stream started: {camera['name']} (ID: {camera_id})")
    
    return {"message": "Camera stream started", "camera_id": camera_id}


@router.post("/{camera_id}/stop", response_model=dict)
async def stop_camera_stream(
    camera_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Stop camera stream"""
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Remove from stream manager
    await stream_manager.remove_camera(camera_id)
    
    # Update status
    await db.cameras.update_one(
        {"_id": camera_id},
        {"$set": {"status": CameraStatus.INACTIVE.value}}
    )
    
    logger.info(f"Camera stream stopped: {camera['name']} (ID: {camera_id})")
    
    return {"message": "Camera stream stopped", "camera_id": camera_id}


@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(
    camera_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get latest camera snapshot as JPEG"""
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Get frame from stream manager
    frame_bytes = await stream_manager.get_frame_jpeg(camera_id)
    
    if frame_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera stream not available",
        )
    
    return StreamingResponse(
        iter([frame_bytes]),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/{camera_id}/events", response_model=PaginatedResponse[CameraEventResponse])
async def list_camera_events(
    camera_id: str,
    pagination: PaginationParams = Depends(),
    event_type: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List camera events with pagination"""
    # Verify camera ownership
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Build filter
    filter_query = {"camera_id": camera_id}
    
    if event_type:
        filter_query["event_type"] = event_type
    
    # Count total
    total = await db.camera_events.count_documents(filter_query)
    
    # Apply pagination and ordering
    skip = (pagination.page - 1) * pagination.page_size
    cursor = db.camera_events.find(filter_query).sort("timestamp", -1).skip(skip).limit(pagination.page_size)
    events = await cursor.to_list(length=pagination.page_size)
    
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=[CameraEventResponse(**event) for event in events],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/{camera_id}/stream-info", response_model=dict)
async def get_stream_info(
    camera_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Get live stream information"""
    camera = await db.cameras.find_one({
        "_id": camera_id,
        "user_id": current_user["id"],
    })
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    
    # Get stream info
    session = stream_manager.get_session(camera_id)
    if not session:
        return {
            "camera_id": camera_id,
            "is_active": False,
            "message": "Stream not active",
        }
    
    stream_info = session.get_stream_info()
    stream_info["camera_id"] = camera_id
    stream_info["camera_name"] = camera.get("name")
    
    return stream_info
