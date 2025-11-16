"""
NexusAI Platform - Rate Limiting Middleware
Token bucket rate limiting per user/IP
"""

import time
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from backend.core.config import settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm
    Supports per-user and per-IP limits
    """
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.redis_client = redis_client
        self.local_cache: Dict[str, Dict] = {}  # Fallback if Redis unavailable
        
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # Skip health check endpoints
        if request.url.path in ["/health", "/health/ready", "/metrics"]:
            return await call_next(request)
        
        # Get identifier (user ID or IP)
        identifier = self._get_identifier(request)
        
        # Check rate limit
        allowed, retry_after = await self._check_rate_limit(identifier, request.url.path)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded: {identifier} on {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(int(retry_after))},
            )
        
        response = await call_next(request)
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier from request"""
        # Try to get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user:
            return f"user:{user.id}"
        
        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    async def _check_rate_limit(self, identifier: str, path: str) -> tuple[bool, float]:
        """
        Check if request is within rate limit
        
        Returns:
            (allowed: bool, retry_after: float)
        """
        # Get rate limit config
        rate_limit = self._get_rate_limit_for_path(path)
        max_requests = rate_limit["requests"]
        window_seconds = rate_limit["window"]
        
        # Use Redis if available
        if self.redis_client:
            return await self._check_redis_rate_limit(
                identifier, max_requests, window_seconds
            )
        else:
            return self._check_local_rate_limit(identifier, max_requests, window_seconds)
    
    def _get_rate_limit_for_path(self, path: str) -> Dict:
        """Get rate limit configuration for path"""
        # Check if path matches specific endpoints
        if "/auth/login" in path:
            return {"requests": 5, "window": 60}  # 5 login attempts per minute
        elif "/inference" in path:
            return {"requests": 100, "window": 60}  # 100 inferences per minute
        else:
            # Default rate limit
            return {"requests": 1000, "window": 60}  # 1000 requests per minute
    
    async def _check_redis_rate_limit(
        self, identifier: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, float]:
        """Check rate limit using Redis"""
        try:
            key = f"ratelimit:{identifier}"
            current_time = time.time()
            
            # Use Redis sorted set for sliding window
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, current_time - window_seconds)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            request_count = results[1]
            
            if request_count >= max_requests:
                # Calculate retry after
                oldest_result = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_result:
                    oldest_time = oldest_result[0][1]
                    retry_after = (oldest_time + window_seconds) - current_time
                    return False, max(retry_after, 0)
                return False, window_seconds
            
            return True, 0
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to local
            return self._check_local_rate_limit(identifier, max_requests, window_seconds)
    
    def _check_local_rate_limit(
        self, identifier: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, float]:
        """Check rate limit using local memory (fallback)"""
        current_time = time.time()
        
        if identifier not in self.local_cache:
            self.local_cache[identifier] = {"requests": [], "window": window_seconds}
        
        cache = self.local_cache[identifier]
        
        # Remove old requests
        cache["requests"] = [
            req_time
            for req_time in cache["requests"]
            if current_time - req_time < window_seconds
        ]
        
        # Check limit
        if len(cache["requests"]) >= max_requests:
            oldest_time = min(cache["requests"])
            retry_after = (oldest_time + window_seconds) - current_time
            return False, max(retry_after, 0)
        
        # Add current request
        cache["requests"].append(current_time)
        
        # Clean up old caches periodically
        if len(self.local_cache) > 10000:
            self._cleanup_local_cache(current_time, window_seconds)
        
        return True, 0
    
    def _cleanup_local_cache(self, current_time: float, window_seconds: int):
        """Clean up expired entries from local cache"""
        keys_to_delete = []
        
        for identifier, cache in self.local_cache.items():
            cache["requests"] = [
                req_time
                for req_time in cache["requests"]
                if current_time - req_time < window_seconds
            ]
            
            if not cache["requests"]:
                keys_to_delete.append(identifier)
        
        for key in keys_to_delete:
            del self.local_cache[key]
