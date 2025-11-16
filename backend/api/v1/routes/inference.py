"""
NexusAI Platform - Inference API Routes
Real-time inference endpoints for images and videos
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.api.dependencies.auth import get_current_active_user, get_optional_user
from backend.core.database import get_db
from backend.core.logging_config import get_logger
from backend.core.storage import upload_file, download_file, get_file_url, BUCKETS
from backend.models.mongodb_models import InferenceStatus
from backend.models.schemas import (
    InferenceRequest,
    InferenceResult,
    InferenceJobResponse,
    PaginationParams,
    PaginatedResponse,
)
from backend.services.inference.engine import InferenceEngine

logger = get_logger(__name__)
router = APIRouter(prefix="/inference", tags=["Inference"])

# Initialize inference engine
inference_engine = InferenceEngine()


@router.post("/predict", response_model=InferenceResult)
async def predict_image(
    file: UploadFile = File(...),
    model_id: str = None,
    confidence_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    max_detections: int = 100,
    return_visualization: bool = False,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Perform real-time inference on an uploaded image.
    
    - **file**: Image file (jpg, png, bmp, webp)
    - **model_id**: Model to use (optional, uses default if not specified)
    - **confidence_threshold**: Minimum confidence score (0.0-1.0)
    - **iou_threshold**: IoU threshold for NMS (0.0-1.0)
    - **max_detections**: Maximum number of detections
    - **return_visualization**: Include annotated image in response
    
    Returns detection results with bounding boxes, classes, and confidences.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/bmp", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}",
        )
    
    # Get model
    if model_id:
        model = await db.models.find_one({"_id": model_id})
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found",
            )
    else:
        # Use default model
        model = await db.models.find_one({"is_default": True, "status": "active"})
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No default model available",
            )
    
    # Upload image to storage
    file_content = await file.read()
    input_path = await upload_file(
        bucket="inputs",
        object_name=f"inference/{uuid4()}/{file.filename}",
        file_data=file_content,
        content_type=file.content_type,
    )
    
    # Create inference job
    job_id = str(uuid4())
    inference_job = {
        "_id": job_id,
        "user_id": current_user["id"] if current_user else None,
        "model_id": model["_id"],
        "input_path": input_path,
        "input_type": "image",
        "status": InferenceStatus.PROCESSING.value,
        "started_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "inference_params": {
            "confidence_threshold": confidence_threshold,
            "iou_threshold": iou_threshold,
            "max_detections": max_detections,
        },
    }
    
    await db.inference_jobs.insert_one(inference_job)
    
    try:
        # Perform inference
        start_time = datetime.utcnow()
        
        result = await inference_engine.predict(
            model=model,
            image_data=file_content,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            max_detections=max_detections,
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update job
        await db.inference_jobs.update_one(
            {"_id": job_id},
            {"$set": {
                "status": InferenceStatus.COMPLETED.value,
                "completed_at": datetime.utcnow(),
                "processing_time_ms": processing_time,
                "result_data": result,
                "num_detections": result.get("num_detections", 0),
                "confidence_avg": result.get("confidence_avg"),
            }}
        )
        
        logger.info(
            f"Inference completed: job_id={job_id}, "
            f"model={model['name']}, detections={result['num_detections']}, "
            f"time={processing_time:.2f}ms"
        )
        
        return InferenceResult(**result)
        
    except Exception as e:
        # Update job with error
        await db.inference_jobs.update_one(
            {"_id": job_id},
            {"$set": {
                "status": InferenceStatus.FAILED.value,
                "completed_at": datetime.utcnow(),
                "error_message": str(e),
            }}
        )
        
        logger.error(f"Inference failed: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {str(e)}",
        )


@router.post("/batch", response_model=dict)
async def batch_inference(
    files: List[UploadFile] = File(...),
    model_id: str = None,
    confidence_threshold: float = 0.25,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Perform batch inference on multiple images.
    
    - **files**: List of image files
    - **model_id**: Model to use
    - **confidence_threshold**: Minimum confidence score
    
    Returns a job ID for tracking batch progress.
    """
    if len(files) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 files per batch",
        )
    
    # Get model
    if model_id:
        model = await db.models.find_one({"_id": model_id})
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    else:
        model = await db.models.find_one({"is_default": True, "status": "active"})
        if not model:
            raise HTTPException(status_code=404, detail="No default model available")
    
    # Create job IDs
    job_ids = []
    
    for file in files:
        # Upload file
        file_content = await file.read()
        input_path = await upload_file(
            bucket="inputs",
            object_name=f"batch/{uuid4()}/{file.filename}",
            file_data=file_content,
            content_type=file.content_type,
        )
        
        # Create job
        job_id = str(uuid4())
        job = {
            "_id": job_id,
            "user_id": current_user["id"],
            "model_id": model["_id"],
            "input_path": input_path,
            "input_type": "image",
            "status": InferenceStatus.PENDING.value,
            "created_at": datetime.utcnow(),
            "inference_params": {"confidence_threshold": confidence_threshold},
        }
        
        await db.inference_jobs.insert_one(job)
        job_ids.append(job_id)
    
    # TODO: Trigger Celery batch task
    
    logger.info(f"Batch inference queued: {len(files)} files")
    
    return {
        "success": True,
        "message": f"Batch inference queued: {len(files)} files",
        "job_ids": job_ids,
    }


@router.get("/jobs", response_model=PaginatedResponse)
async def list_inference_jobs(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[str] = None,
    model_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    List inference jobs for the current user.
    
    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status
    - **model_id**: Filter by model
    """
    filter_query = {"user_id": current_user["id"]}
    
    if status_filter:
        filter_query["status"] = status_filter
    
    if model_id:
        filter_query["model_id"] = model_id
    
    # Get total
    total = await db.inference_jobs.count_documents(filter_query)
    
    # Paginate
    skip = (pagination.page - 1) * pagination.page_size
    cursor = db.inference_jobs.find(filter_query).sort("created_at", -1).skip(skip).limit(pagination.page_size)
    jobs = await cursor.to_list(length=pagination.page_size)
    
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=[InferenceJobResponse(**job) for job in jobs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/jobs/{job_id}", response_model=InferenceJobResponse)
async def get_inference_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get details of a specific inference job.
    
    - **job_id**: Job UUID
    """
    job = await db.inference_jobs.find_one({
        "_id": job_id,
        "user_id": current_user["id"]
    })
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return InferenceJobResponse(**job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inference_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Delete an inference job.
    
    - **job_id**: Job UUID
    """
    job = await db.inference_jobs.find_one({
        "_id": job_id,
        "user_id": current_user["id"]
    })
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await db.inference_jobs.delete_one({"_id": job_id})
    
    logger.info(f"Inference job deleted: {job_id}")
    
    return None
