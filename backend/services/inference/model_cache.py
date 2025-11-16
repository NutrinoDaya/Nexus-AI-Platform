"""
NexusAI Platform - Model Cache
Efficient model caching with LRU eviction for inference optimization
"""

import asyncio
from collections import OrderedDict
from typing import Any, Dict, Optional
import threading
from pathlib import Path
import psutil
import gc

from backend.core.config import settings
from backend.core.logging_config import get_logger
from backend.core.storage import download_file

logger = get_logger(__name__)


class ModelCache:
    """
    LRU cache for loaded ML models with memory management
    
    Features:
    - Least Recently Used (LRU) eviction
    - Memory-aware caching
    - Thread-safe operations
    - Async model loading
    """
    
    def __init__(
        self, 
        max_models: int = 5,
        max_memory_mb: int = 4096,  # 4GB default
        cache_ttl_seconds: int = 3600  # 1 hour
    ):
        self.max_models = max_models
        self.max_memory_mb = max_memory_mb
        self.cache_ttl = cache_ttl_seconds
        
        # Cache storage
        self.models: Dict[str, Any] = {}
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.access_order: OrderedDict = OrderedDict()
        self.load_times: Dict[str, float] = {}
        self.model_sizes: Dict[str, int] = {}  # Size in MB
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "loads": 0
        }
        
        logger.info(f"Model cache initialized: max_models={max_models}, max_memory={max_memory_mb}MB")
    
    async def get_model(self, model_id: str, config: Dict[str, Any]) -> Any:
        """
        Get model from cache or load if not cached
        
        Args:
            model_id: Unique model identifier
            config: Model configuration dictionary
            
        Returns:
            Loaded model instance
        """
        with self.lock:
            # Check if model is cached
            if model_id in self.models:
                # Update access order (move to end = most recent)
                self.access_order.move_to_end(model_id)
                self.stats["hits"] += 1
                
                logger.debug(f"Model cache HIT: {model_id}")
                return self.models[model_id]
            
            # Cache miss - need to load model
            self.stats["misses"] += 1
            logger.debug(f"Model cache MISS: {model_id}")
        
        # Load model (outside lock to prevent blocking)
        model = await self._load_model(model_id, config)
        
        # Add to cache
        await self._add_to_cache(model_id, model, config)
        
        return model
    
    async def _load_model(self, model_id: str, config: Dict[str, Any]) -> Any:
        """Load model from storage"""
        import time
        
        start_time = time.time()
        
        try:
            # Determine model framework and loader
            framework = config.get("framework", "pytorch").lower()
            
            if framework == "onnx":
                from backend.services.inference.engine import ONNXLoader
                loader = ONNXLoader()
            elif framework == "tensorrt":
                from backend.services.inference.engine import TensorRTLoader
                loader = TensorRTLoader()
            else:
                from backend.services.inference.engine import PyTorchLoader
                loader = PyTorchLoader()
            
            # Download model file if needed
            model_path = config.get("file_path")
            if model_path.startswith("s3://") or model_path.startswith("minio://"):
                local_path = f"/tmp/models/{model_id}.{framework}"
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                await download_file(model_path, local_path)
                model_path = local_path
            
            # Load model
            model = loader.load_model(model_path, config)
            
            load_time = time.time() - start_time
            model_size = self._estimate_model_size(model_path)
            
            logger.info(
                f"Model loaded: {model_id} "
                f"({framework}) in {load_time:.2f}s, "
                f"size: {model_size}MB"
            )
            
            self.stats["loads"] += 1
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            raise
    
    async def _add_to_cache(self, model_id: str, model: Any, config: Dict[str, Any]):
        """Add model to cache with eviction if needed"""
        import time
        
        model_size = self._estimate_model_memory(model)
        
        with self.lock:
            # Check if we need to evict models
            await self._ensure_cache_capacity(model_size)
            
            # Add to cache
            self.models[model_id] = model
            self.configs[model_id] = config
            self.access_order[model_id] = time.time()
            self.load_times[model_id] = time.time()
            self.model_sizes[model_id] = model_size
            
            logger.debug(f"Model cached: {model_id} ({model_size}MB)")
    
    async def _ensure_cache_capacity(self, new_model_size: int):
        """Evict models if needed to make space"""
        current_memory = sum(self.model_sizes.values())
        
        # Evict by count limit
        while len(self.models) >= self.max_models:
            await self._evict_lru_model()
        
        # Evict by memory limit
        while (current_memory + new_model_size) > self.max_memory_mb:
            if not self.models:  # No models to evict
                break
            await self._evict_lru_model()
            current_memory = sum(self.model_sizes.values())
    
    async def _evict_lru_model(self):
        """Evict least recently used model"""
        if not self.access_order:
            return
        
        # Get least recently used model
        lru_model_id = next(iter(self.access_order))
        
        # Remove from all caches
        evicted_size = self.model_sizes.pop(lru_model_id, 0)
        self.models.pop(lru_model_id, None)
        self.configs.pop(lru_model_id, None)
        self.access_order.pop(lru_model_id, None)
        self.load_times.pop(lru_model_id, None)
        
        self.stats["evictions"] += 1
        
        logger.info(f"Model evicted: {lru_model_id} ({evicted_size}MB)")
        
        # Force garbage collection
        gc.collect()
    
    def _estimate_model_size(self, model_path: str) -> int:
        """Estimate model file size in MB"""
        try:
            return int(Path(model_path).stat().st_size / (1024 * 1024))
        except:
            return 100  # Default estimate
    
    def _estimate_model_memory(self, model: Any) -> int:
        """Estimate model memory usage in MB"""
        try:
            # Try to get actual memory usage
            process = psutil.Process()
            memory_mb = int(process.memory_info().rss / (1024 * 1024))
            return max(memory_mb // 10, 50)  # Rough estimate
        except:
            return 100  # Default estimate
    
    def invalidate(self, model_id: str):
        """Remove specific model from cache"""
        with self.lock:
            if model_id in self.models:
                self.models.pop(model_id, None)
                self.configs.pop(model_id, None)
                self.access_order.pop(model_id, None)
                self.load_times.pop(model_id, None)
                self.model_sizes.pop(model_id, None)
                
                logger.info(f"Model invalidated: {model_id}")
    
    def clear(self):
        """Clear all cached models"""
        with self.lock:
            self.models.clear()
            self.configs.clear()
            self.access_order.clear()
            self.load_times.clear()
            self.model_sizes.clear()
            
            logger.info("Model cache cleared")
            gc.collect()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            hit_rate = (
                self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
                if (self.stats["hits"] + self.stats["misses"]) > 0 
                else 0
            )
            
            total_memory = sum(self.model_sizes.values())
            
            return {
                "cached_models": len(self.models),
                "max_models": self.max_models,
                "total_memory_mb": total_memory,
                "max_memory_mb": self.max_memory_mb,
                "memory_usage_pct": (total_memory / self.max_memory_mb) * 100,
                "hit_rate": hit_rate,
                "stats": self.stats.copy(),
                "model_list": list(self.models.keys())
            }


# Global cache instance
_model_cache: Optional[ModelCache] = None


def get_model_cache() -> ModelCache:
    """Get the global model cache instance"""
    global _model_cache
    
    if _model_cache is None:
        cache_config = getattr(settings, 'MODEL_CACHE', {})
        _model_cache = ModelCache(
            max_models=cache_config.get('max_models', 5),
            max_memory_mb=cache_config.get('max_memory_mb', 4096),
            cache_ttl_seconds=cache_config.get('ttl_seconds', 3600)
        )
    
    return _model_cache


# Dependency for FastAPI
async def get_cached_model(model_id: str, config: Dict[str, Any]) -> Any:
    """FastAPI dependency to get cached model"""
    cache = get_model_cache()
    return await cache.get_model(model_id, config)