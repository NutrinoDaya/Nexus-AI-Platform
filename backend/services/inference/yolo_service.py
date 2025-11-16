"""
YOLO Model Service
Handles YOLO models for detection, segmentation, and tracking using Ultralytics
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import cv2
from ultralytics import YOLO
from pathlib import Path

from backend.core.config import settings

logger = logging.getLogger(__name__)


class YOLOService:
    """Service for YOLO model operations"""
    
    def __init__(self):
        self.models: Dict[str, YOLO] = {}
        self.model_configs: Dict[str, Dict] = {}
        
    def load_model(self, model_path: str, model_id: str = None) -> str:
        """Load a YOLO model"""
        try:
            if model_id is None:
                model_id = Path(model_path).stem
                
            # Load model
            model = YOLO(model_path)
            
            # Store model and configuration
            self.models[model_id] = model
            self.model_configs[model_id] = {
                "path": model_path,
                "task": self._detect_task(model),
                "input_size": getattr(model.model, 'imgsz', 640),
                "classes": model.names if hasattr(model, 'names') else {},
                "loaded": True
            }
            
            logger.info(f"Loaded YOLO model: {model_id} from {model_path}")
            return model_id
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model {model_path}: {e}")
            raise
    
    def _detect_task(self, model: YOLO) -> str:
        """Detect the task type of the YOLO model"""
        try:
            # Check model type from the model itself
            if hasattr(model.model, 'model') and hasattr(model.model.model, '_modules'):
                modules = list(model.model.model._modules.keys())
                if 'Segment' in str(modules):
                    return 'segment'
                elif 'Pose' in str(modules):
                    return 'pose'
                elif 'Classify' in str(modules):
                    return 'classify'
            return 'detect'
        except Exception:
            return 'detect'
    
    def detect(
        self, 
        model_id: str, 
        image: np.ndarray,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        max_det: int = 1000,
        classes: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Run YOLO detection"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not loaded")
            
        model = self.models[model_id]
        
        try:
            # Run inference
            results = model(
                image,
                conf=conf_threshold,
                iou=iou_threshold,
                max_det=max_det,
                classes=classes,
                verbose=False
            )
            
            # Process results
            detections = []
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    for i, (box, conf, cls_id) in enumerate(zip(boxes, confidences, class_ids)):
                        x1, y1, x2, y2 = box
                        detections.append({
                            "id": i,
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "confidence": float(conf),
                            "class_id": int(cls_id),
                            "class_name": model.names.get(cls_id, f"class_{cls_id}") if hasattr(model, 'names') else f"class_{cls_id}"
                        })
            
            return {
                "detections": detections,
                "image_shape": image.shape,
                "model_id": model_id,
                "task": "detect"
            }
            
        except Exception as e:
            logger.error(f"YOLO detection failed for model {model_id}: {e}")
            raise
    
    def segment(
        self,
        model_id: str,
        image: np.ndarray,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        max_det: int = 1000
    ) -> Dict[str, Any]:
        """Run YOLO segmentation"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not loaded")
            
        model = self.models[model_id]
        
        try:
            # Run inference
            results = model(
                image,
                conf=conf_threshold,
                iou=iou_threshold,
                max_det=max_det,
                verbose=False
            )
            
            # Process results
            detections = []
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    # Get masks if available
                    masks = []
                    if hasattr(result, 'masks') and result.masks is not None:
                        masks = result.masks.data.cpu().numpy()
                    
                    for i, (box, conf, cls_id) in enumerate(zip(boxes, confidences, class_ids)):
                        x1, y1, x2, y2 = box
                        detection = {
                            "id": i,
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "confidence": float(conf),
                            "class_id": int(cls_id),
                            "class_name": model.names.get(cls_id, f"class_{cls_id}") if hasattr(model, 'names') else f"class_{cls_id}"
                        }
                        
                        # Add mask if available
                        if i < len(masks):
                            # Convert mask to polygon points
                            mask = masks[i].astype(np.uint8)
                            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            if contours:
                                # Get the largest contour
                                largest_contour = max(contours, key=cv2.contourArea)
                                # Simplify polygon
                                epsilon = 0.02 * cv2.arcLength(largest_contour, True)
                                polygon = cv2.approxPolyDP(largest_contour, epsilon, True)
                                detection["polygon"] = polygon.reshape(-1, 2).tolist()
                        
                        detections.append(detection)
            
            return {
                "detections": detections,
                "image_shape": image.shape,
                "model_id": model_id,
                "task": "segment"
            }
            
        except Exception as e:
            logger.error(f"YOLO segmentation failed for model {model_id}: {e}")
            raise
    
    def track(
        self,
        model_id: str,
        image: np.ndarray,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        tracker: str = "bytetrack.yaml"
    ) -> Dict[str, Any]:
        """Run YOLO tracking"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not loaded")
            
        model = self.models[model_id]
        
        try:
            # Run inference with tracking
            results = model.track(
                image,
                conf=conf_threshold,
                iou=iou_threshold,
                tracker=tracker,
                verbose=False
            )
            
            # Process results
            tracks = []
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    # Get track IDs if available
                    track_ids = []
                    if hasattr(result.boxes, 'id') and result.boxes.id is not None:
                        track_ids = result.boxes.id.cpu().numpy().astype(int)
                    
                    for i, (box, conf, cls_id) in enumerate(zip(boxes, confidences, class_ids)):
                        x1, y1, x2, y2 = box
                        track = {
                            "detection_id": i,
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "confidence": float(conf),
                            "class_id": int(cls_id),
                            "class_name": model.names.get(cls_id, f"class_{cls_id}") if hasattr(model, 'names') else f"class_{cls_id}",
                            "track_id": int(track_ids[i]) if i < len(track_ids) else None
                        }
                        tracks.append(track)
            
            return {
                "tracks": tracks,
                "image_shape": image.shape,
                "model_id": model_id,
                "task": "track"
            }
            
        except Exception as e:
            logger.error(f"YOLO tracking failed for model {model_id}: {e}")
            raise
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a loaded model"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not loaded")
            
        config = self.model_configs[model_id]
        model = self.models[model_id]
        
        return {
            "model_id": model_id,
            "path": config["path"],
            "task": config["task"],
            "input_size": config["input_size"],
            "classes": config["classes"],
            "loaded": config["loaded"],
            "class_count": len(config["classes"])
        }
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all loaded models"""
        return [self.get_model_info(model_id) for model_id in self.models.keys()]
    
    def unload_model(self, model_id: str) -> bool:
        """Unload a model"""
        if model_id in self.models:
            del self.models[model_id]
            del self.model_configs[model_id]
            logger.info(f"Unloaded YOLO model: {model_id}")
            return True
        return False
    
    def preload_default_models(self):
        """Preload default YOLO models"""
        default_models = [
            ("yolov8n.pt", "yolov8n-detect"),
            ("yolov8s.pt", "yolov8s-detect"),
            ("yolov8n-seg.pt", "yolov8n-segment"),
            ("yolov8s-seg.pt", "yolov8s-segment")
        ]
        
        for model_file, model_id in default_models:
            model_path = os.path.join(settings.MODELS_PATH, model_file)
            if os.path.exists(model_path):
                try:
                    self.load_model(model_path, model_id)
                except Exception as e:
                    logger.warning(f"Failed to preload {model_id}: {e}")


# Global YOLO service instance
yolo_service = YOLOService()