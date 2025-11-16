"""
YOLO API Routes
Endpoints for YOLO model management and inference
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from pydantic import BaseModel

from backend.services.inference.yolo_service import yolo_service
from backend.services.inference.inference_queue import inference_queue
from backend.api.dependencies.auth import get_current_user
from backend.models.mongodb_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/yolo", tags=["YOLO"])


class YOLOInferenceRequest(BaseModel):
    model_id: str
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    max_detections: int = 1000
    classes: Optional[List[int]] = None


class YOLOTrackRequest(BaseModel):
    model_id: str
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    tracker: str = "bytetrack.yaml"


@router.get("/models")
async def list_yolo_models(current_user: User = Depends(get_current_user)):
    """List all loaded YOLO models"""
    try:
        models = yolo_service.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to list YOLO models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.get("/models/{model_id}")
async def get_yolo_model_info(
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get information about a specific YOLO model"""
    try:
        model_info = yolo_service.get_model_info(model_id)
        return model_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get model info for {model_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model info")


@router.post("/models/load")
async def load_yolo_model(
    model_path: str = Form(...),
    model_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Load a YOLO model from file path"""
    try:
        loaded_model_id = yolo_service.load_model(model_path, model_id)
        model_info = yolo_service.get_model_info(loaded_model_id)
        return {
            "message": f"Model loaded successfully",
            "model_id": loaded_model_id,
            "model_info": model_info
        }
    except Exception as e:
        logger.error(f"Failed to load YOLO model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


@router.delete("/models/{model_id}")
async def unload_yolo_model(
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """Unload a YOLO model"""
    try:
        success = yolo_service.unload_model(model_id)
        if success:
            return {"message": f"Model {model_id} unloaded successfully"}
        else:
            raise HTTPException(status_code=404, detail="Model not found")
    except Exception as e:
        logger.error(f"Failed to unload YOLO model {model_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unload model")


@router.post("/detect")
async def yolo_detect(
    image: UploadFile = File(...),
    model_id: str = Form(...),
    confidence_threshold: float = Form(0.25),
    iou_threshold: float = Form(0.45),
    max_detections: int = Form(1000),
    priority: int = Form(1),
    async_processing: bool = Form(False),
    current_user: User = Depends(get_current_user)
):
    """Run YOLO object detection on an image with scalable processing"""
    try:
        # Read and validate image
        image_bytes = await image.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        if async_processing:
            # Submit to scalable inference queue
            job_id = await inference_queue.submit_job(
                model_id=model_id,
                image_data=image_bytes,
                inference_type="detect",
                parameters={
                    "conf_threshold": confidence_threshold,
                    "iou_threshold": iou_threshold,
                    "max_det": max_detections
                },
                priority=priority
            )
            
            return {
                "job_id": job_id,
                "status": "submitted",
                "message": "Detection job submitted for processing",
                "estimated_wait_time": await inference_queue.queue.qsize() * 0.5  # Rough estimate
            }
        else:
            # Process synchronously for immediate results
            results = yolo_service.detect(
                model_id=model_id,
                image=img,
                conf_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
                max_det=max_detections
            )
            
            return results
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"YOLO detection failed: {e}")
        raise HTTPException(status_code=500, detail="Detection failed")


@router.post("/segment")
async def yolo_segment(
    image: UploadFile = File(...),
    model_id: str = Form(...),
    confidence_threshold: float = Form(0.25),
    iou_threshold: float = Form(0.45),
    max_detections: int = Form(1000),
    current_user: User = Depends(get_current_user)
):
    """Run YOLO instance segmentation on an image"""
    try:
        # Read and decode image
        image_bytes = await image.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # Run segmentation
        results = yolo_service.segment(
            model_id=model_id,
            image=img,
            conf_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            max_det=max_detections
        )
        
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"YOLO segmentation failed: {e}")
        raise HTTPException(status_code=500, detail="Segmentation failed")


@router.post("/track")
async def yolo_track(
    image: UploadFile = File(...),
    model_id: str = Form(...),
    confidence_threshold: float = Form(0.25),
    iou_threshold: float = Form(0.45),
    tracker: str = Form("bytetrack.yaml"),
    current_user: User = Depends(get_current_user)
):
    """Run YOLO object tracking on an image"""
    try:
        # Read and decode image
        image_bytes = await image.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # Run tracking
        results = yolo_service.track(
            model_id=model_id,
            image=img,
            conf_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            tracker=tracker
        )
        
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"YOLO tracking failed: {e}")
        raise HTTPException(status_code=500, detail="Tracking failed")


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status and result of an inference job"""
    try:
        job_status = await inference_queue.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")
        return job_status
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.get("/queue/stats")
async def get_queue_stats(current_user: User = Depends(get_current_user)):
    """Get inference queue statistics"""
    try:
        stats = await inference_queue.get_queue_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue stats")


@router.post("/preload")
async def preload_default_models(current_user: User = Depends(get_current_user)):
    """Preload default YOLO models"""
    try:
        yolo_service.preload_default_models()
        models = yolo_service.list_models()
        return {
            "message": "Default models preloaded",
            "loaded_models": models
        }
    except Exception as e:
        logger.error(f"Failed to preload default models: {e}")
        raise HTTPException(status_code=500, detail="Failed to preload models")