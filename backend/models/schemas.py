"""
Pydantic Schemas for API Request/Response Validation
Complete schema definitions for NexusAI Platform
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


# ================================
# User Schemas
# ================================

class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user creation"""
    password: str = Field(..., min_length=8)
    role: str = "user"


class UserUpdate(BaseModel):
    """Schema for user updates"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserWithToken(UserResponse):
    """User response with authentication token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ================================
# Authentication Schemas
# ================================

class TokenRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# ================================
# Model Schemas
# ================================

class ModelBase(BaseModel):
    """Base model schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: str
    framework: str
    version: str


class ModelCreate(ModelBase):
    """Schema for model registration"""
    model_path: str
    config_path: Optional[str] = None
    input_size: Optional[List[int]] = None
    output_classes: Optional[int] = None
    class_names: Optional[List[str]] = None
    expected_fps: Optional[float] = None
    max_latency_ms: Optional[float] = None
    preprocessing_config: Optional[Dict[str, Any]] = None
    inference_config: Optional[Dict[str, Any]] = None
    device: str = "cuda"
    batch_size: int = 1
    access_level: str = "authenticated"


class ModelUpdate(BaseModel):
    """Schema for model updates"""
    description: Optional[str] = None
    status: Optional[str] = None
    is_default: Optional[bool] = None
    access_level: Optional[str] = None
    inference_config: Optional[Dict[str, Any]] = None


class ModelResponse(ModelBase):
    """Schema for model response"""
    id: UUID
    slug: str
    status: str
    is_default: bool
    access_level: str
    device: str
    batch_size: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ================================
# Inference Schemas
# ================================

class InferenceRequest(BaseModel):
    """Schema for inference request"""
    model_id: UUID
    confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_detections: int = Field(default=100, ge=1, le=1000)
    return_visualization: bool = False
    metadata: Optional[Dict[str, Any]] = None


class DetectionResult(BaseModel):
    """Single detection result"""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    
    
class InferenceResult(BaseModel):
    """Inference result schema"""
    detections: List[DetectionResult]
    num_detections: int
    processing_time_ms: float
    model_used: str
    image_size: List[int]  # [width, height]


class InferenceJobResponse(BaseModel):
    """Schema for inference job response"""
    id: UUID
    status: str
    model_id: UUID
    user_id: Optional[UUID] = None
    input_path: str
    output_path: Optional[str] = None
    processing_time_ms: Optional[float] = None
    num_detections: Optional[int] = None
    result_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


# ================================
# Model Access Control Schemas
# ================================

class ModelAccessBase(BaseModel):
    """Base model access schema"""
    can_use: bool = True
    can_view: bool = True
    can_edit: bool = False
    can_delete: bool = False
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ModelAccessCreate(ModelAccessBase):
    """Schema for creating model access"""
    user_id: UUID


class ModelAccessUpdate(BaseModel):
    """Schema for updating model access"""
    can_use: Optional[bool] = None
    can_view: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ModelAccessResponse(ModelAccessBase):
    """Schema for model access response"""
    id: UUID
    user_id: UUID
    model_id: UUID
    granted_by_id: UUID
    granted_at: datetime
    
    class Config:
        from_attributes = True


# ================================
# Camera Schemas
# ================================

class CameraBase(BaseModel):
    """Base camera schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    stream_url: str
    protocol: str
    username: Optional[str] = None
    password: Optional[str] = None


class CameraCreate(CameraBase):
    """Schema for camera creation"""
    fps: int = 30
    resolution: List[int] = [1920, 1080]
    buffer_size: int = 60
    enable_inference: bool = False
    model_id: Optional[UUID] = None
    enable_recording: bool = False
    enable_motion_detection: bool = False
    location: Optional[str] = None


class CameraUpdate(BaseModel):
    """Schema for camera updates"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    fps: Optional[int] = None
    enable_inference: Optional[bool] = None
    model_id: Optional[UUID] = None
    enable_recording: Optional[bool] = None
    enable_motion_detection: Optional[bool] = None


class CameraResponse(CameraBase):
    """Schema for camera response"""
    id: UUID
    status: str
    is_active: bool
    fps: int
    current_fps: Optional[float] = None
    resolution: List[int]
    enable_inference: bool
    enable_recording: bool
    enable_motion_detection: bool
    last_frame_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CameraEventResponse(BaseModel):
    """Schema for camera event"""
    id: UUID
    camera_id: UUID
    event_type: str
    severity: str
    description: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    thumbnail_path: Optional[str] = None
    detected_at: datetime
    acknowledged: bool
    
    class Config:
        from_attributes = True


# ================================
# Settings Schemas
# ================================

class SystemSettingBase(BaseModel):
    """Base system setting schema"""
    key: str
    value: Any
    category: str
    description: Optional[str] = None


class SystemSettingCreate(SystemSettingBase):
    """Schema for creating system setting"""
    is_public: bool = False


class SystemSettingUpdate(BaseModel):
    """Schema for updating system setting"""
    value: Any
    description: Optional[str] = None


class SystemSettingResponse(SystemSettingBase):
    """Schema for system setting response"""
    id: UUID
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ================================
# Common Schemas
# ================================

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Any] = None


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: Dict[str, Any]
    request_id: Optional[str] = None


# ================================
# Health Check Schemas
# ================================

class HealthCheckResponse(BaseModel):
    """Health check response"""
    success: bool
    status: str
    service: str
    version: str


class ReadinessCheckResponse(BaseModel):
    """Readiness check response"""
    success: bool
    status: str
    checks: Dict[str, bool]


# Export all schemas
__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserWithToken",
    "TokenRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "ModelCreate",
    "ModelUpdate",
    "ModelResponse",
    "ModelAccessCreate",
    "ModelAccessUpdate",
    "ModelAccessResponse",
    "InferenceRequest",
    "InferenceResult",
    "DetectionResult",
    "InferenceJobResponse",
    "CameraCreate",
    "CameraUpdate",
    "CameraResponse",
    "CameraEventResponse",
    "SystemSettingCreate",
    "SystemSettingUpdate",
    "SystemSettingResponse",
    "MessageResponse",
    "PaginationParams",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "HealthCheckResponse",
    "ReadinessCheckResponse",
]
