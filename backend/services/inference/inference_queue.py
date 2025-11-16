"""
Scalable Inference Queue Service
Handles concurrent inference requests with queue management and load balancing
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum
import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor
import threading

from backend.core.config import settings

logger = logging.getLogger(__name__)


class InferenceStatus(Enum):
    """Inference job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class InferenceJob:
    """Inference job data structure"""
    job_id: str
    model_id: str
    image_data: bytes
    inference_type: str  # detect, segment, track
    parameters: Dict[str, Any]
    callback: Optional[Callable] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: InferenceStatus = InferenceStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    priority: int = 1  # Higher number = higher priority


class InferenceQueue:
    """Scalable inference queue with worker pool management"""
    
    def __init__(self, max_workers: int = None, max_queue_size: int = 1000):
        self.max_workers = max_workers or settings.INFERENCE_MAX_WORKERS
        self.max_queue_size = max_queue_size
        
        # Queue management
        self.queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.jobs: Dict[str, InferenceJob] = {}
        self.workers: List[asyncio.Task] = []
        
        # Thread pool for CPU-intensive inference
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Statistics
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "queue_size": 0,
            "active_workers": 0
        }
        
        # Synchronization
        self._lock = threading.Lock()
        self._running = False
        
    async def start(self):
        """Start the inference queue workers"""
        if self._running:
            return
            
        self._running = True
        logger.info(f"Starting inference queue with {self.max_workers} workers")
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
            
    async def stop(self):
        """Stop the inference queue workers"""
        if not self._running:
            return
            
        self._running = False
        logger.info("Stopping inference queue workers")
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
            
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        self.workers.clear()
        
    async def submit_job(
        self,
        model_id: str,
        image_data: bytes,
        inference_type: str,
        parameters: Dict[str, Any] = None,
        priority: int = 1,
        callback: Optional[Callable] = None
    ) -> str:
        """Submit an inference job to the queue"""
        
        if not self._running:
            raise RuntimeError("Inference queue is not running")
            
        if self.queue.qsize() >= self.max_queue_size:
            raise RuntimeError(f"Queue is full (max size: {self.max_queue_size})")
            
        # Create job
        job_id = str(uuid4())
        job = InferenceJob(
            job_id=job_id,
            model_id=model_id,
            image_data=image_data,
            inference_type=inference_type,
            parameters=parameters or {},
            callback=callback,
            created_at=datetime.utcnow(),
            priority=priority
        )
        
        # Store job
        with self._lock:
            self.jobs[job_id] = job
            self.stats["total_jobs"] += 1
            
        # Add to queue (priority queue uses negative priority for max-heap behavior)
        await self.queue.put((-priority, datetime.utcnow().timestamp(), job))
        
        logger.debug(f"Submitted inference job {job_id} for model {model_id}")
        return job_id
        
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and result"""
        with self._lock:
            job = self.jobs.get(job_id)
            
        if not job:
            return None
            
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "result": job.result,
            "error": job.error
        }
        
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._lock:
            stats = self.stats.copy()
            stats["queue_size"] = self.queue.qsize()
            stats["active_jobs"] = len([j for j in self.jobs.values() if j.status == InferenceStatus.PROCESSING])
            
        return stats
        
    async def _worker(self, worker_name: str):
        """Worker coroutine to process inference jobs"""
        logger.info(f"Started inference worker: {worker_name}")
        
        try:
            while self._running:
                try:
                    # Get job from queue with timeout
                    try:
                        priority, timestamp, job = await asyncio.wait_for(
                            self.queue.get(), timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        continue
                        
                    # Update job status
                    job.status = InferenceStatus.PROCESSING
                    job.started_at = datetime.utcnow()
                    
                    logger.debug(f"Worker {worker_name} processing job {job.job_id}")
                    
                    # Process job in thread pool
                    try:
                        result = await asyncio.get_event_loop().run_in_executor(
                            self.thread_pool,
                            self._process_inference_job,
                            job
                        )
                        
                        # Update job with result
                        job.result = result
                        job.status = InferenceStatus.COMPLETED
                        job.completed_at = datetime.utcnow()
                        
                        with self._lock:
                            self.stats["completed_jobs"] += 1
                            
                        logger.debug(f"Job {job.job_id} completed successfully")
                        
                    except Exception as e:
                        # Handle job failure
                        job.error = str(e)
                        job.status = InferenceStatus.FAILED
                        job.completed_at = datetime.utcnow()
                        
                        with self._lock:
                            self.stats["failed_jobs"] += 1
                            
                        logger.error(f"Job {job.job_id} failed: {e}")
                        
                    # Call callback if provided
                    if job.callback:
                        try:
                            await job.callback(job)
                        except Exception as e:
                            logger.error(f"Callback failed for job {job.job_id}: {e}")
                            
                    # Mark task as done
                    self.queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Worker {worker_name} error: {e}")
                    
        except asyncio.CancelledError:
            logger.info(f"Worker {worker_name} cancelled")
        except Exception as e:
            logger.error(f"Worker {worker_name} failed: {e}")
            
    def _process_inference_job(self, job: InferenceJob) -> Dict[str, Any]:
        """Process inference job in thread pool (synchronous)"""
        from backend.services.inference.yolo_service import yolo_service
        
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(job.image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image")
                
            # Run inference based on type
            if job.inference_type == "detect":
                result = yolo_service.detect(
                    job.model_id,
                    image,
                    **job.parameters
                )
            elif job.inference_type == "segment":
                result = yolo_service.segment(
                    job.model_id,
                    image,
                    **job.parameters
                )
            elif job.inference_type == "track":
                result = yolo_service.track(
                    job.model_id,
                    image,
                    **job.parameters
                )
            else:
                raise ValueError(f"Unknown inference type: {job.inference_type}")
                
            return result
            
        except Exception as e:
            logger.error(f"Inference processing failed for job {job.job_id}: {e}")
            raise


# Global inference queue instance
inference_queue = InferenceQueue()