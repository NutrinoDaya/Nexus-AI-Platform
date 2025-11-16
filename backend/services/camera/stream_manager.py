"""
NexusAI Platform - Camera Streaming Manager
RTSP/WebRTC stream handling with reconnection and recording
"""

import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime
import cv2
import numpy as np
from collections import deque

from backend.core.config import settings, config
from backend.core.logging_config import get_logger
from backend.models.mongodb_models import CameraStatus

logger = get_logger(__name__)


class StreamSession:
    """Individual camera stream session with async frame processing"""
    
    def __init__(self, camera: Dict[str, Any]):
        self.camera = camera
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_active = False
        
        # Async frame processing
        self.frame_queue = asyncio.Queue(maxsize=30)
        self.processing_task: Optional[asyncio.Task] = None
        self.capture_task: Optional[asyncio.Task] = None
        
        # Frame tracking
        self.frame_buffer = deque(maxlen=config.cameras_config.get("max_frame_buffer", 60))
        self.last_frame_time = None
        self.reconnect_attempts = 0
        self.error_message = None
        self.frame_count = 0
        self.dropped_frames = 0
        
        # Performance metrics
        self.fps_counter = deque(maxlen=30)  # Last 30 frame times
        self.processing_times = deque(maxlen=100)  # Processing time tracking
    
    async def connect(self) -> bool:
        """Connect to camera stream"""
        try:
            # Create VideoCapture object
            self.cap = cv2.VideoCapture(self.camera["rtsp_url"])
            
            # Set buffer size
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            
            # Set timeout
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            
            if not self.cap.isOpened():
                raise Exception(f"Failed to open camera stream: {self.camera['rtsp_url']}")
            
            self.is_active = True
            self.reconnect_attempts = 0
            self.error_message = None
            
            logger.info(f"Camera connected: {self.camera['name']} ({self.camera['rtsp_url']})")
            return True
            
        except Exception as e:
            logger.error(f"Camera connection failed: {self.camera['name']} - {e}")
            self.error_message = str(e)
            self.is_active = False
            return False
    
    async def disconnect(self):
        """Disconnect from camera"""
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.is_active = False
        logger.info(f"Camera disconnected: {self.camera['name']}")
    
    async def start_processing(self):
        """Start async frame capture and processing"""
        if self.is_active:
            logger.warning(f"Stream already active: {self.camera['name']}")
            return
        
        if not await self.connect():
            return
        
        # Start capture and processing tasks
        self.capture_task = asyncio.create_task(self._capture_loop())
        self.processing_task = asyncio.create_task(self._processing_loop())
        
        logger.info(f"Started async processing for camera: {self.camera['name']}")
    
    async def stop_processing(self):
        """Stop async frame capture and processing"""
        self.is_active = False
        
        # Cancel tasks
        if self.capture_task:
            self.capture_task.cancel()
            try:
                await self.capture_task
            except asyncio.CancelledError:
                pass
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        await self.disconnect()
        logger.info(f"Stopped processing for camera: {self.camera['name']}")
    
    async def _capture_loop(self):
        """Producer: Capture frames in background thread"""
        while self.is_active:
            try:
                # Capture frame in thread pool to avoid blocking
                frame = await asyncio.to_thread(self._read_frame_sync)
                
                if frame is not None:
                    self.frame_count += 1
                    current_time = datetime.utcnow()
                    
                    # Update FPS tracking
                    if self.last_frame_time:
                        frame_interval = (current_time - self.last_frame_time).total_seconds()
                        self.fps_counter.append(1.0 / frame_interval if frame_interval > 0 else 0)
                    
                    self.last_frame_time = current_time
                    
                    # Add frame to processing queue
                    try:
                        self.frame_queue.put_nowait((frame, current_time))
                    except asyncio.QueueFull:
                        # Drop oldest frame if queue is full
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait((frame, current_time))
                            self.dropped_frames += 1
                        except asyncio.QueueEmpty:
                            pass
                else:
                    # Failed to read frame, wait before retry
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in capture loop for {self.camera['name']}: {e}")
                await asyncio.sleep(1.0)
    
    async def _processing_loop(self):
        """Consumer: Process frames from queue"""
        from backend.core.mongodb import get_database
        
        while self.is_active:
            try:
                # Get frame from queue (wait up to 1 second)
                frame, capture_time = await asyncio.wait_for(
                    self.frame_queue.get(), timeout=1.0
                )
                
                # Process frame
                start_time = datetime.utcnow()
                await self._process_frame(frame, capture_time)
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Track processing performance
                self.processing_times.append(processing_time * 1000)  # ms
                
                # Mark queue task as done
                self.frame_queue.task_done()
                
            except asyncio.TimeoutError:
                # No frame received in timeout, continue
                continue
            except Exception as e:
                logger.error(f"Error in processing loop for {self.camera['name']}: {e}")
                await asyncio.sleep(0.1)
    
    def _read_frame_sync(self) -> Optional[np.ndarray]:
        """Synchronous frame reading (runs in thread pool)"""
        if not self.cap or not self.cap.isOpened():
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret:
                # Add to buffer for latest frame access
                self.frame_buffer.append(frame)
                return frame
            return None
            
        except Exception as e:
            logger.error(f"Error reading frame sync: {self.camera['name']} - {e}")
            return None
    
    async def reconnect(self):
        """Attempt to reconnect to camera"""
        max_reconnect_attempts = config.cameras_config.get("max_reconnect_attempts", 5)
        reconnect_delay = config.cameras_config.get("reconnect_delay_seconds", 5)
        
        if self.reconnect_attempts >= max_reconnect_attempts:
            logger.error(f"Max reconnect attempts reached: {self.camera['name']}")
            await self.disconnect()
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Reconnecting camera: {self.camera['name']} (attempt {self.reconnect_attempts})")
        
        await self.disconnect()
        await asyncio.sleep(reconnect_delay)
        await self.connect()
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest frame from buffer"""
        if len(self.frame_buffer) > 0:
            return self.frame_buffer[-1]
        return None
    
    def get_stream_info(self) -> Dict:
        """Get stream information"""
        if self.cap and self.cap.isOpened():
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            return {
                "fps": fps,
                "width": width,
                "height": height,
                "is_active": self.is_active,
                "buffer_size": len(self.frame_buffer),
                "last_frame_time": self.last_frame_time.isoformat() if self.last_frame_time else None,
                "reconnect_attempts": self.reconnect_attempts,
                "error_message": self.error_message,
            }
        else:
            return {
                "is_active": False,
                "error_message": self.error_message or "Camera not connected",
            }


class StreamManager:
    """
    Manages multiple camera streams with automatic reconnection
    """
    
    def __init__(self):
        self._sessions: Dict[str, StreamSession] = {}
        self._capture_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
    
    async def start(self):
        """Start stream manager"""
        self._running = True
        logger.info("Stream manager started")
    
    async def stop(self):
        """Stop all streams"""
        self._running = False
        
        # Stop all capture tasks
        for task in self._capture_tasks.values():
            task.cancel()
        
        # Disconnect all cameras
        for session in self._sessions.values():
            await session.disconnect()
        
        self._sessions.clear()
        self._capture_tasks.clear()
        
        logger.info("Stream manager stopped")
    
    async def add_camera(self, camera: Dict[str, Any]) -> bool:
        """
        Add camera to stream manager
        
        Args:
            camera: Camera document from MongoDB
            
        Returns:
            True if camera added successfully
        """
        camera_id = str(camera["_id"])
        
        if camera_id in self._sessions:
            logger.warning(f"Camera already exists: {camera['name']}")
            return False
        
        # Create session
        session = StreamSession(camera)
        
        # Connect
        if not await session.connect():
            return False
        
        self._sessions[camera_id] = session
        
        # Start capture task
        task = asyncio.create_task(self._capture_loop(camera_id))
        self._capture_tasks[camera_id] = task
        
        logger.info(f"Camera added: {camera['name']}")
        return True
    
    async def remove_camera(self, camera_id: str):
        """Remove camera from manager"""
        if camera_id in self._capture_tasks:
            self._capture_tasks[camera_id].cancel()
            del self._capture_tasks[camera_id]
        
        if camera_id in self._sessions:
            await self._sessions[camera_id].disconnect()
            del self._sessions[camera_id]
        
        logger.info(f"Camera removed: {camera_id}")
    
    def get_session(self, camera_id: str) -> Optional[StreamSession]:
        """Get stream session"""
        return self._sessions.get(camera_id)
    
    def get_all_sessions(self) -> List[StreamSession]:
        """Get all stream sessions"""
        return list(self._sessions.values())
    
    async def _capture_loop(self, camera_id: str):
        """Continuous frame capture loop"""
        session = self._sessions.get(camera_id)
        if not session:
            return
        
        capture_interval = 1.0 / config.cameras_config.get("default_fps", 30)
        motion_detector = None
        prev_frame_gray = None
        
        try:
            while self._running and camera_id in self._sessions:
                frame = await session.read_frame()
                
                if frame is not None:
                    # Process frame for analytics
                    await self._process_frame(camera_id, frame, prev_frame_gray)
                    
                    # Update previous frame for motion detection
                    import cv2
                    prev_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                await asyncio.sleep(capture_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Capture loop cancelled: {camera_id}")
        except Exception as e:
            logger.error(f"Error in capture loop: {camera_id} - {e}")
    
    async def _process_frame(self, camera_id: str, frame: np.ndarray, prev_frame: Optional[np.ndarray]):
        """Process frame for motion detection and analytics"""
        import cv2
        from uuid import uuid4
        from backend.core.mongodb import get_database
        
        camera = self._sessions[camera_id].camera
        
        # Skip if analytics not enabled
        if not camera.get("motion_detection_enabled", False):
            return
        
        # Motion detection
        if prev_frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Compute frame difference
            frame_diff = cv2.absdiff(prev_frame, gray)
            
            # Threshold
            _, thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)
            
            # Dilate to fill gaps
            kernel = np.ones((5, 5), np.uint8)
            thresh = cv2.dilate(thresh, kernel, iterations=2)
            
            # Count non-zero pixels (motion pixels)
            motion_pixels = cv2.countNonZero(thresh)
            motion_threshold = camera.get("analytics_config", {}).get("motion_threshold", 5000)
            
            # Detect motion
            if motion_pixels > motion_threshold:
                logger.info(f"Motion detected on camera {camera_id}: {motion_pixels} pixels")
                
                # Create motion event
                try:
                    db = await get_database()
                    
                    # Find contours for bounding boxes
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Get significant contours
                    significant_contours = [c for c in contours if cv2.contourArea(c) > 500]
                    
                    event = {
                        "_id": str(uuid4()),
                        "camera_id": camera_id,
                        "event_type": "motion_detected",
                        "timestamp": datetime.utcnow(),
                        "metadata": {
                            "motion_pixels": int(motion_pixels),
                            "contour_count": len(significant_contours),
                            "bounding_boxes": [
                                {
                                    "x": int(x),
                                    "y": int(y),
                                    "width": int(w),
                                    "height": int(h),
                                    "area": int(cv2.contourArea(c))
                                }
                                for c in significant_contours[:10]  # Max 10 boxes
                                for x, y, w, h in [cv2.boundingRect(c)]
                            ]
                        },
                        "created_at": datetime.utcnow()
                    }
                    
                    await db.camera_events.insert_one(event)
                    logger.debug(f"Motion event created: {event['_id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to create motion event: {e}")
        
        # Optional: Run AI inference if models are configured
        analytics_config = camera.get("analytics_config", {})
        if analytics_config.get("detection_enabled") and analytics_config.get("model_id"):
            try:
                # This could be done asynchronously or in background
                # For now, we'll skip to avoid blocking the capture loop
                pass
            except Exception as e:
                logger.error(f"Failed to run AI detection: {e}")
    
    async def get_frame_jpeg(self, camera_id: str) -> Optional[bytes]:
        """Get latest frame as JPEG bytes"""
        session = self.get_session(camera_id)
        if not session:
            return None
        
        frame = session.get_latest_frame()
        if frame is None:
            return None
        
        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buffer.tobytes()


# Global stream manager instance
stream_manager = StreamManager()
