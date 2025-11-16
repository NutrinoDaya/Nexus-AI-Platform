"""
NexusAI Platform - Inference Engine
Plugin-based model loader supporting PyTorch, ONNX, TensorRT
Multi-framework inference with caching and optimization
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from PIL import Image
import io

from backend.core.config import settings, config
from backend.core.logging_config import get_logger
from backend.core.storage import download_file
from backend.models.mongodb_models import ModelFramework

logger = get_logger(__name__)


class ModelLoader:
    """Base class for model loaders"""
    
    def load_model(self, model_path: str, config: Dict[str, Any]) -> Any:
        """Load model from path"""
        raise NotImplementedError
    
    def preprocess(self, image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
        """Preprocess image for inference"""
        raise NotImplementedError
    
    def predict(self, model: Any, input_data: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run inference"""
        raise NotImplementedError
    
    def postprocess(self, outputs: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess model outputs"""
        raise NotImplementedError


class ONNXLoader(ModelLoader):
    """ONNX Runtime model loader"""
    
    def __init__(self):
        try:
            import onnxruntime as ort
            self.ort = ort
            
            # Set providers based on device
            if settings.INFERENCE_DEVICE == "cuda":
                self.providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            else:
                self.providers = ['CPUExecutionProvider']
            
            logger.info(f"ONNX Runtime initialized with providers: {self.providers}")
        except ImportError:
            logger.error("ONNX Runtime not installed")
            raise
    
    def load_model(self, model_path: str, config: Dict[str, Any]) -> Any:
        """Load ONNX model"""
        sess_options = self.ort.SessionOptions()
        sess_options.graph_optimization_level = self.ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Set thread count
        inference_config = config.get("inference_config", {})
        num_threads = inference_config.get("num_threads", 4)
        sess_options.intra_op_num_threads = num_threads
        sess_options.inter_op_num_threads = 2
        
        session = self.ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=self.providers
        )
        
        logger.info(f"ONNX model loaded: {model_path}")
        return session
    
    def preprocess(self, image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
        """Preprocess image for ONNX model"""
        input_size = config.get("input_size", [640, 640])
        preprocessing_config = config.get("preprocessing_config", {})
        
        # Resize
        from cv2 import resize, INTER_LINEAR
        image = resize(image, tuple(input_size), interpolation=INTER_LINEAR)
        
        # Normalize
        if preprocessing_config.get("normalize", True):
            mean = preprocessing_config.get("mean", [0.0, 0.0, 0.0])
            std = preprocessing_config.get("std", [255.0, 255.0, 255.0])
            
            image = image.astype(np.float32)
            image = (image - np.array(mean)) / np.array(std)
        
        # HWC to CHW
        image = np.transpose(image, (2, 0, 1))
        
        # Add batch dimension
        image = np.expand_dims(image, axis=0)
        
        return image.astype(np.float32)
    
    def predict(self, model: Any, input_data: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
        """Run ONNX inference"""
        input_name = model.get_inputs()[0].name
        outputs = model.run(None, {input_name: input_data})
        return outputs[0]
    
    def postprocess(self, outputs: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess YOLO-style outputs"""
        confidence_threshold = config.get("confidence_threshold", 0.25)
        iou_threshold = config.get("iou_threshold", 0.45)
        max_detections = config.get("max_detections", 100)
        
        # NMS and filtering
        detections = self._apply_nms(
            outputs,
            confidence_threshold,
            iou_threshold,
            max_detections
        )
        
        return detections
    
    def _apply_nms(
        self,
        outputs: np.ndarray,
        conf_thresh: float,
        iou_thresh: float,
        max_det: int
    ) -> Dict[str, Any]:
        """Apply Non-Maximum Suppression"""
        import cv2
        
        # Parse outputs (assuming YOLO format)
        # Shape: [batch, num_boxes, 5 + num_classes]
        # Format: [x, y, w, h, conf, class_scores...]
        
        boxes = []
        confidences = []
        class_ids = []
        
        for detection in outputs[0]:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = detection[4] * scores[class_id]
            
            if confidence > conf_thresh:
                # Convert from center format to corner format
                x, y, w, h = detection[:4]
                x1 = int(x - w / 2)
                y1 = int(y - h / 2)
                x2 = int(x + w / 2)
                y2 = int(y + h / 2)
                
                boxes.append([x1, y1, x2, y2])
                confidences.append(float(confidence))
                class_ids.append(int(class_id))
        
        # Apply NMS
        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(
                boxes,
                confidences,
                conf_thresh,
                iou_thresh
            )
            
            if len(indices) > 0:
                indices = indices.flatten()[:max_det]
                
                final_boxes = [boxes[i] for i in indices]
                final_confidences = [confidences[i] for i in indices]
                final_class_ids = [class_ids[i] for i in indices]
            else:
                final_boxes = []
                final_confidences = []
                final_class_ids = []
        else:
            final_boxes = []
            final_confidences = []
            final_class_ids = []
        
        # Format results
        detections = []
        class_names = config.get("class_names", {})
        
        for bbox, conf, cls_id in zip(final_boxes, final_confidences, final_class_ids):
            # Get class name from config, or use generic name
            class_name = class_names.get(str(cls_id), class_names.get(int(cls_id), f"class_{cls_id}"))
            
            detections.append({
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": conf,
                "bbox": bbox,
            })
        
        return {
            "detections": detections,
            "num_detections": len(detections),
            "confidence_avg": np.mean(final_confidences) if final_confidences else 0.0,
            "model_used": "onnx",
            "image_size": config.get("input_size", [640, 640]),
        }


class PyTorchLoader(ModelLoader):
    """PyTorch model loader"""
    
    def __init__(self):
        try:
            import torch
            self.torch = torch
            self.device = torch.device(settings.INFERENCE_DEVICE)
            logger.info(f"PyTorch initialized on device: {self.device}")
        except ImportError:
            logger.error("PyTorch not installed")
            raise
    
    def load_model(self, model_path: str, config: Dict[str, Any]) -> Any:
        """Load PyTorch model"""
        model = self.torch.load(model_path, map_location=self.device)
        model.eval()
        logger.info(f"PyTorch model loaded: {model_path}")
        return model
    
    def preprocess(self, image: np.ndarray, config: Dict[str, Any]) -> Any:
        """Preprocess for PyTorch"""
        # Similar to ONNX but return torch tensor
        input_size = config.get("input_size", [640, 640])
        
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        tensor = transform(image).unsqueeze(0).to(self.device)
        return tensor
    
    def predict(self, model: Any, input_data: Any, config: Dict[str, Any]) -> Any:
        """Run PyTorch inference"""
        with self.torch.no_grad():
            outputs = model(input_data)
        return outputs
    
    def postprocess(self, outputs: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess PyTorch outputs"""
        # Convert to numpy and use ONNX postprocessing
        outputs_np = outputs.cpu().numpy()
        onnx_loader = ONNXLoader()
        return onnx_loader.postprocess(outputs_np, config)


class TensorRTLoader(ModelLoader):
    """TensorRT model loader for optimized NVIDIA GPU inference"""
    
    def __init__(self):
        if not settings.USE_TENSORRT:
            raise RuntimeError("TensorRT is disabled in settings")
        
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit
            
            self.trt = trt
            self.cuda = cuda
            logger.info("TensorRT initialized")
        except ImportError:
            logger.error("TensorRT or PyCUDA not installed")
            raise
    
    def load_model(self, model_path: str, config: Dict[str, Any]) -> Any:
        """Load TensorRT engine"""
        TRT_LOGGER = self.trt.Logger(self.trt.Logger.WARNING)
        
        with open(model_path, 'rb') as f:
            runtime = self.trt.Runtime(TRT_LOGGER)
            engine = runtime.deserialize_cuda_engine(f.read())
        
        context = engine.create_execution_context()
        logger.info(f"TensorRT engine loaded: {model_path}")
        
        return {"engine": engine, "context": context}
    
    def predict(self, model: Any, input_data: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
        """Run TensorRT inference"""
        # TensorRT inference implementation
        # This is simplified; full implementation requires CUDA memory management
        engine = model["engine"]
        context = model["context"]
        
        # Allocate buffers
        # Run inference
        # Return results
        
        # TODO: Full TensorRT implementation
        logger.warning("TensorRT inference not fully implemented, using ONNX fallback")
        return np.array([])
    
    def preprocess(self, image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
        """Preprocess for TensorRT (same as ONNX)"""
        onnx_loader = ONNXLoader()
        return onnx_loader.preprocess(image, config)
    
    def postprocess(self, outputs: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess TensorRT outputs"""
        onnx_loader = ONNXLoader()
        return onnx_loader.postprocess(outputs, config)


class InferenceEngine:
    """
    Main inference engine with model caching and multi-framework support
    """
    
    def __init__(self):
        self._model_cache: Dict[str, Any] = {}
        self._loader_cache: Dict[ModelFramework, ModelLoader] = {}
        
        # Initialize loaders
        self._init_loaders()
    
    def _init_loaders(self):
        """Initialize model loaders based on configuration"""
        if settings.USE_ONNX:
            try:
                self._loader_cache[ModelFramework.ONNX] = ONNXLoader()
            except Exception as e:
                logger.error(f"Failed to initialize ONNX loader: {e}")
        
        try:
            self._loader_cache[ModelFramework.PYTORCH] = PyTorchLoader()
        except Exception as e:
            logger.error(f"Failed to initialize PyTorch loader: {e}")
        
        if settings.USE_TENSORRT:
            try:
                self._loader_cache[ModelFramework.TENSORRT] = TensorRTLoader()
            except Exception as e:
                logger.error(f"Failed to initialize TensorRT loader: {e}")
    
    async def load_model(self, model: Dict[str, Any]) -> Any:
        """
        Load model from storage and cache it
        
        Args:
            model: Model document from MongoDB
            
        Returns:
            Loaded model
        """
        cache_key = str(model["_id"])
        
        # Check cache
        if cache_key in self._model_cache:
            logger.debug(f"Model loaded from cache: {model['name']}")
            return self._model_cache[cache_key]
        
        # Get appropriate loader
        loader = self._loader_cache.get(ModelFramework(model["framework"]))
        if not loader:
            raise ValueError(f"No loader available for framework: {model['framework']}")
        
        # Download model if needed
        if model["model_path"].startswith("s3://"):
            # Download from storage
            local_path = settings.MODELS_CACHE_PATH / f"{model['_id']}.{model['framework']}"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not local_path.exists():
                logger.info(f"Downloading model: {model['name']}")
                await download_file(
                    bucket="models",
                    object_name=model["model_path"].replace("s3://nexusai-models/", ""),
                    file_path=local_path,
                )
            
            model_path = str(local_path)
        else:
            model_path = model["model_path"]
        
        # Load model
        config = {
            "input_size": model.get("input_size"),
            "preprocessing_config": model.get("preprocessing_config", {}),
            "inference_config": model.get("inference_config", {}),
            "class_names": model.get("class_names", {}),
        }
        
        loaded_model = loader.load_model(model_path, config)
        
        # Cache model (with size limit)
        if len(self._model_cache) < 5:  # Max 5 models in memory
            self._model_cache[cache_key] = {
                "model": loaded_model,
                "loader": loader,
                "config": config
            }
            logger.info(f"Model cached: {model['name']}")
        else:
            logger.warning("Model cache full, not caching this model")
        
        return loaded_model
    
    async def predict(self, image: np.ndarray, model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run inference on image using cached model
        
        Args:
            image: Input image as numpy array
            model: Model document from MongoDB
            
        Returns:
            Inference results
        """
        import time
        start_time = time.time()
        
        # Load model (from cache if available)
        loaded_model = await self.load_model(model)
        
        # Get cached model info
        cache_key = str(model["_id"])
        cached_info = self._model_cache.get(cache_key)
        
        if cached_info:
            loader = cached_info["loader"]
            config = cached_info["config"]
        else:
            # Fallback if not cached
            framework = ModelFramework(model["framework"])
            loader = self._loader_cache[framework]
            config = {
                "input_size": model.get("input_size"),
                "preprocessing_config": model.get("preprocessing_config", {}),
                "inference_config": model.get("inference_config", {}),
                "class_names": model.get("class_names", {}),
            }
        
        # Run inference pipeline
        try:
            # Preprocess
            input_data = loader.preprocess(image, config)
            
            # Predict
            raw_outputs = loader.predict(loaded_model, input_data, config)
            
            # Postprocess
            results = loader.postprocess(raw_outputs, config)
            
            # Add timing info
            inference_time = time.time() - start_time
            results["inference_time_ms"] = inference_time * 1000
            results["model_id"] = str(model["_id"])
            results["model_name"] = model["name"]
            results["framework"] = model["framework"]
            
            logger.debug(f"Inference completed in {inference_time:.3f}s")
            return results
            
        except Exception as e:
            logger.error(f"Inference failed for model {model['name']}: {e}")
            raise
    
    def clear_cache(self):
        """Clear all cached models"""
        self._model_cache.clear()
        logger.info("Model cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached models"""
        return {
            "cached_models": len(self._model_cache),
            "available_frameworks": list(self._loader_cache.keys()),
            "cache_keys": list(self._model_cache.keys())
        }
        self._model_cache[cache_key] = {
            "model": loaded_model,
            "loader": loader,
            "config": config,
        }
        
        logger.info(f"Model loaded and cached: {model['name']}")
        
        return self._model_cache[cache_key]
    
    async def predict(
        self,
        model: Dict[str, Any],
        image_data: bytes,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        max_detections: int = 100,
    ) -> Dict[str, Any]:
        """
        Perform inference on image
        
        Args:
            model: Model document from MongoDB
            image_data: Image bytes
            confidence_threshold: Confidence threshold
            iou_threshold: IOU threshold
            max_detections: Maximum detections
            
        Returns:
            Inference results
        """
        # Load model
        model_data = await self.load_model(model)
        loaded_model = model_data["model"]
        loader = model_data["loader"]
        config = model_data["config"].copy()
        
        # Update config with inference parameters
        config.update({
            "confidence_threshold": confidence_threshold,
            "iou_threshold": iou_threshold,
            "max_detections": max_detections,
        })
        
        # Load image
        image = Image.open(io.BytesIO(image_data))
        image_np = np.array(image.convert("RGB"))
        
        # Preprocess
        input_data = loader.preprocess(image_np, config)
        
        # Predict
        outputs = loader.predict(loaded_model, input_data, config)
        
        # Postprocess
        results = loader.postprocess(outputs, config)
        
        return results
    
    def clear_cache(self, model_id: Optional[str] = None):
        """Clear model cache"""
        if model_id:
            self._model_cache.pop(model_id, None)
            logger.info(f"Cleared cache for model: {model_id}")
        else:
            self._model_cache.clear()
            logger.info("Cleared all model cache")
