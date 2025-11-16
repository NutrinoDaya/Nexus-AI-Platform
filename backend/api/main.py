"""
NexusAI Platform - Main FastAPI Application
Production-ready AI inference platform with streaming and monitoring
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import make_asgi_app
import time

from backend.core.config import settings
from backend.core.database import init_database, check_database_health
from backend.core.logging_config import get_logger
from backend.api.v1.router import api_v1_router
from backend.services.camera.stream_manager import stream_manager
from backend.services.inference.inference_queue import inference_queue

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting NexusAI Platform...")
    
    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Start stream manager
    try:
        await stream_manager.start()
        logger.info("Stream manager started")
    except Exception as e:
        logger.error(f"Stream manager initialization failed: {e}")
        # Non-critical, continue
    
    # Start inference queue
    try:
        await inference_queue.start()
        logger.info("Inference queue started")
    except Exception as e:
        logger.error(f"Inference queue initialization failed: {e}")
        # Non-critical, continue
    
    logger.info("NexusAI Platform started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NexusAI Platform...")
    
    # Stop stream manager
    try:
        await stream_manager.stop()
        logger.info("Stream manager stopped")
    except Exception as e:
        logger.error(f"Error stopping stream manager: {e}")
    
    # Stop inference queue
    try:
        await inference_queue.stop()
        logger.info("Inference queue stopped")
    except Exception as e:
        logger.error(f"Error stopping inference queue: {e}")
    
    logger.info("NexusAI Platform shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="NexusAI Platform",
    description="Production-ready AI inference platform with camera streaming and model management",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s"
            )
        
        return response
    except Exception as e:
        logger.error(f"Request error: {request.method} {request.url.path} - {e}")
        raise


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request"""
    import uuid
    
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "NexusAI Platform"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check with database connection"""
    try:
        db_healthy = await check_database_health()
        
        if not db_healthy:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "reason": "database connection failed"},
            )
        
        return {
            "status": "ready",
            "database": "connected",
            "stream_manager": "active" if stream_manager._running else "inactive",
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)},
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NexusAI Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled in production",
    }


# Include API v1 router
app.include_router(api_v1_router)


# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.API_WORKERS,
        log_level="info",
    )
