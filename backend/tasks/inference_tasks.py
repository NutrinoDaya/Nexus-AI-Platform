"""
NexusAI Platform - Celery Tasks
Background tasks for inference, video processing, and model training
"""

import asyncio
from typing import Dict, List, Any
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
from uuid import uuid4

from backend.tasks.celery_app import celery_app
from backend.core.logging_config import get_logger
from backend.core.mongodb import get_database
from backend.services.inference.engine import InferenceEngine

logger = get_logger(__name__)


@celery_app.task(bind=True, name="tasks.batch_inference")
def batch_inference_task(self, job_id: str, image_paths: List[str], model_id: str):
    """
    Process batch inference job
    
    Args:
        job_id: Inference job ID (UUID string)
        image_paths: List of image paths
        model_id: Model ID (UUID string)
    """
    logger.info(f"Starting batch inference job {job_id} with {len(image_paths)} images")
    
    try:
        # Run async code in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new loop if one is already running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            _process_batch_inference(job_id, image_paths, model_id)
        )
        
        logger.info(f"Batch inference job {job_id} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Batch inference job {job_id} failed: {e}", exc_info=True)
        
        # Update job status to failed
        loop.run_until_complete(_update_job_status(job_id, "failed", str(e)))
        
        raise


async def _process_batch_inference(job_id: str, image_paths: List[str], model_id: str) -> Dict:
    """Process batch inference asynchronously"""
    db = await get_database()
    
    # Get model
    model = await db.models.find_one({"_id": model_id})
    
    if not model:
        raise ValueError(f"Model not found: {model_id}")
    
    # Initialize inference engine
    engine = InferenceEngine()
    
    # Process each image
    results = []
    for image_path in image_paths:
        try:
            # Read image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Run inference
            result = await engine.predict(model, image_data)
            results.append({
                "image_path": image_path,
                "success": True,
                "result": result,
            })
            
        except Exception as e:
            logger.error(f"Failed to process image {image_path}: {e}")
            results.append({
                "image_path": image_path,
                "success": False,
                "error": str(e),
            })
    
    # Update job with results
    await db.inference_jobs.update_one(
        {"_id": job_id},
        {"$set": {
            "status": "COMPLETED",
            "result_data": {"batch_results": results},
            "completed_at": datetime.utcnow(),
        }}
    )
    
    return {
        "job_id": job_id,
        "total_images": len(image_paths),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
    }


async def _update_job_status(job_id: str, status: str, error: str = None):
    """Update job status"""
    db = await get_database()
    
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow(),
    }
    
    if error:
        update_data["error_message"] = error
    
    if status in ["COMPLETED", "FAILED"]:
        update_data["completed_at"] = datetime.utcnow()
    
    await db.inference_jobs.update_one(
        {"_id": job_id},
        {"$set": update_data}
    )


@celery_app.task(bind=True, name="tasks.video_analysis")
def video_analysis_task(self, video_path: str, model_id: str, camera_id: str):
    """
    Analyze video file with AI model
    
    Args:
        video_path: Path to video file
        model_id: Model ID for inference (UUID string)
        camera_id: Camera ID (UUID string)
    """
    logger.info(f"Starting video analysis: {video_path}")
    
    try:
        # Run async code in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            _process_video_analysis(video_path, model_id, camera_id)
        )
        
        logger.info(f"Video analysis completed: {video_path}")
        return result
        
    except Exception as e:
        logger.error(f"Video analysis failed: {e}", exc_info=True)
        raise


async def _process_video_analysis(video_path: str, model_id: str, camera_id: str) -> Dict:
    """Process video analysis asynchronously"""
    import cv2
    from pathlib import Path
    
    db = await get_database()
    
    # Get model
    model = await db.models.find_one({"_id": model_id})
    if not model:
        raise ValueError(f"Model not found: {model_id}")
    
    # Initialize inference engine
    engine = InferenceEngine()
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    logger.info(f"Video: {frame_count} frames, {fps} FPS, {width}x{height}")
    
    # Process every Nth frame (e.g., 1 per second)
    frame_interval = max(1, fps // 1)  # 1 frame per second
    
    detections = []
    events = []
    frame_idx = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process only selected frames
            if frame_idx % frame_interval == 0:
                # Convert frame to bytes
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                # Run inference
                try:
                    result = await engine.predict(model, frame_bytes)
                    
                    # Store detections
                    if result.get("detections"):
                        timestamp = frame_idx / fps
                        detections.append({
                            "frame": frame_idx,
                            "timestamp": timestamp,
                            "detections": result["detections"],
                            "count": len(result["detections"])
                        })
                        
                        # Create camera event for significant detections
                        if len(result["detections"]) > 0:
                            event = {
                                "_id": str(uuid4()),
                                "camera_id": camera_id,
                                "event_type": "detection",
                                "timestamp": datetime.utcnow(),
                                "metadata": {
                                    "frame": frame_idx,
                                    "video_timestamp": timestamp,
                                    "detection_count": len(result["detections"]),
                                    "video_path": video_path
                                },
                                "created_at": datetime.utcnow()
                            }
                            await db.camera_events.insert_one(event)
                            events.append(event["_id"])
                
                except Exception as e:
                    logger.error(f"Inference failed for frame {frame_idx}: {e}")
            
            frame_idx += 1
            
            # Update progress every 100 frames
            if frame_idx % 100 == 0:
                progress = (frame_idx / frame_count) * 100
                logger.info(f"Processing: {progress:.1f}% ({frame_idx}/{frame_count})")
    
    finally:
        cap.release()
    
    return {
        "status": "completed",
        "video_path": video_path,
        "total_frames": frame_count,
        "processed_frames": len(detections),
        "total_detections": sum(d["count"] for d in detections),
        "events_created": len(events),
        "detection_frames": [d["frame"] for d in detections[:10]],  # First 10
    }


@celery_app.task(bind=True, name="tasks.model_optimization")
def model_optimization_task(self, model_id: str, optimization_type: str):
    """
    Optimize model (quantization, pruning, TensorRT conversion)
    
    Args:
        model_id: Model ID (UUID string)
        optimization_type: Type of optimization (quantize, prune, tensorrt)
    """
    logger.info(f"Starting model optimization: {model_id} ({optimization_type})")
    
    try:
        # Run async code in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            _optimize_model(model_id, optimization_type)
        )
        
        logger.info(f"Model optimization completed: {model_id}")
        return result
        
    except Exception as e:
        logger.error(f"Model optimization failed: {e}", exc_info=True)
        raise


async def _optimize_model(model_id: str, optimization_type: str) -> Dict:
    """Optimize model asynchronously"""
    import torch
    from pathlib import Path
    
    db = await get_database()
    
    # Get model
    model = await db.models.find_one({"_id": model_id})
    if not model:
        raise ValueError(f"Model not found: {model_id}")
    
    model_path = model["model_path"]
    if model_path.startswith("s3://"):
        # Download from storage
        from backend.core.storage import download_file
        from backend.core.config import settings
        
        local_path = settings.MODELS_CACHE_PATH / f"{model_id}_original.pt"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        await download_file(
            bucket="models",
            object_name=model_path.replace("s3://nexusai-models/", ""),
            file_path=local_path,
        )
        model_path = str(local_path)
    
    optimized_path = Path(model_path).parent / f"{model_id}_{optimization_type}.pt"
    
    if optimization_type == "quantize":
        # FP32 to FP16 quantization
        logger.info("Performing FP16 quantization...")
        
        if model["framework"] == "PYTORCH":
            model_obj = torch.load(model_path)
            
            # Convert to FP16
            if isinstance(model_obj, dict) and 'model' in model_obj:
                model_obj['model'] = model_obj['model'].half()
            else:
                model_obj = model_obj.half()
            
            torch.save(model_obj, optimized_path)
            
            original_size = Path(model_path).stat().st_size
            optimized_size = optimized_path.stat().st_size
            compression_ratio = original_size / optimized_size
            
            result = {
                "status": "completed",
                "optimization_type": "quantize",
                "original_size_mb": original_size / (1024 * 1024),
                "optimized_size_mb": optimized_size / (1024 * 1024),
                "compression_ratio": compression_ratio,
                "output_path": str(optimized_path)
            }
        else:
            raise ValueError(f"Quantization not supported for {model['framework']}")
    
    elif optimization_type == "prune":
        # Weight pruning
        logger.info("Performing weight pruning...")
        
        if model["framework"] == "PYTORCH":
            import torch.nn.utils.prune as prune
            
            model_obj = torch.load(model_path)
            
            # Get the model (handle both direct model and checkpoint dict)
            if isinstance(model_obj, dict) and 'model' in model_obj:
                net = model_obj['model']
            else:
                net = model_obj
            
            # Apply global unstructured pruning (30% sparsity)
            parameters_to_prune = []
            for module in net.modules():
                if isinstance(module, (torch.nn.Conv2d, torch.nn.Linear)):
                    parameters_to_prune.append((module, 'weight'))
            
            if parameters_to_prune:
                prune.global_unstructured(
                    parameters_to_prune,
                    pruning_method=prune.L1Unstructured,
                    amount=0.3,  # 30% pruning
                )
                
                # Make pruning permanent
                for module, name in parameters_to_prune:
                    prune.remove(module, name)
            
            # Save pruned model
            if isinstance(model_obj, dict):
                model_obj['model'] = net
                torch.save(model_obj, optimized_path)
            else:
                torch.save(net, optimized_path)
            
            original_size = Path(model_path).stat().st_size
            optimized_size = optimized_path.stat().st_size
            
            result = {
                "status": "completed",
                "optimization_type": "prune",
                "pruning_amount": 0.3,
                "original_size_mb": original_size / (1024 * 1024),
                "optimized_size_mb": optimized_size / (1024 * 1024),
                "output_path": str(optimized_path)
            }
        else:
            raise ValueError(f"Pruning not supported for {model['framework']}")
    
    elif optimization_type == "tensorrt":
        # TensorRT conversion
        logger.info("Converting to TensorRT...")
        
        # This requires TensorRT and CUDA
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit
        except ImportError:
            raise ValueError("TensorRT and PyCUDA required for TensorRT optimization")
        
        # Export to ONNX first if PyTorch
        if model["framework"] == "PYTORCH":
            onnx_path = Path(model_path).with_suffix('.onnx')
            
            model_obj = torch.load(model_path)
            if isinstance(model_obj, dict) and 'model' in model_obj:
                net = model_obj['model']
            else:
                net = model_obj
            
            net.eval()
            
            # Export to ONNX with input specs from model config
            input_shape = (1, 3, 640, 640)  # Standard YOLO input shape
            sample_input = torch.randn(input_shape)
            torch.onnx.export(
                net,
                sample_input,
                onnx_path,
                opset_version=11,
                input_names=['images'],
                output_names=['output'],
            )
            
            logger.info(f"Exported to ONNX: {onnx_path}")
            model_path = str(onnx_path)
        
        # Convert ONNX to TensorRT
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)
        
        # Parse ONNX
        with open(model_path, 'rb') as f:
            if not parser.parse(f.read()):
                raise ValueError("Failed to parse ONNX model")
        
        # Build engine
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB
        
        # FP16 precision if available
        if builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
        
        engine = builder.build_serialized_network(network, config)
        
        # Save engine
        trt_path = Path(model_path).with_suffix('.engine')
        with open(trt_path, 'wb') as f:
            f.write(engine)
        
        result = {
            "status": "completed",
            "optimization_type": "tensorrt",
            "fp16_enabled": builder.platform_has_fast_fp16,
            "output_path": str(trt_path)
        }
    
    else:
        raise ValueError(f"Unknown optimization type: {optimization_type}")
    
    # Update model document with optimized version
    await db.models.update_one(
        {"_id": model_id},
        {"$set": {
            f"optimized_versions.{optimization_type}": {
                "path": result["output_path"],
                "created_at": datetime.utcnow(),
                **{k: v for k, v in result.items() if k not in ["status", "output_path"]}
            },
            "updated_at": datetime.utcnow()
        }}
    )
    
    return result


@celery_app.task(bind=True, name="tasks.cleanup_old_jobs")
def cleanup_old_jobs_task(self, days: int = 30):
    """
    Clean up old inference jobs
    
    Args:
        days: Delete jobs older than this many days
    """
    logger.info(f"Starting cleanup of jobs older than {days} days")
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        deleted_count = loop.run_until_complete(_cleanup_jobs(days))
        
        logger.info(f"Cleanup completed: {deleted_count} jobs deleted")
        return {"deleted": deleted_count}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        raise


async def _cleanup_jobs(days: int) -> int:
    """Clean up old jobs asynchronously"""
    db = await get_database()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.inference_jobs.delete_many({
        "created_at": {"$lt": cutoff_date}
    })
    
    return result.deleted_count
