"""
MongoDB Document Models

This module defines document schemas for MongoDB collections.
Uses Pydantic for validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, EmailStr, validator


# ================================
# Enums
# ================================

class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class ModelStatus(str, Enum):
    """Model status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ModelFramework(str, Enum):
    """Supported ML frameworks"""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    ONNX = "onnx"
    TENSORRT = "tensorrt"
    OPENVINO = "openvino"


class InferenceStatus(str, Enum):
    """Inference job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CameraProtocol(str, Enum):
    """Camera streaming protocols"""
    RTSP = "rtsp"
    RTMP = "rtmp"
    HTTP = "http"
    ONVIF = "onvif"


# ================================
# User Model
# ================================

class UserModel(BaseModel):
    """
    User document model.
    
    Represents a user account with authentication and authorization information.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# Model (AI Model) Document
# ================================

class ModelDocument(BaseModel):
    """
    AI Model document.
    
    Stores metadata about uploaded AI models for inference.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    framework: ModelFramework
    version: str = "1.0.0"
    file_path: str
    file_size_bytes: int = 0
    status: ModelStatus = ModelStatus.DRAFT
    
    # Model configuration
    input_shape: Optional[List[int]] = None
    output_classes: Optional[List[str]] = None
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.4
    
    # Performance metrics
    accuracy: Optional[float] = None
    inference_time_ms: Optional[float] = None
    
    # Metadata
    created_by: str  # User ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# Model Access Control
# ================================

class ModelAccessDocument(BaseModel):
    """
    Model Access Control document.
    
    Manages granular per-user permissions for AI models.
    Supports time-based access expiration and audit trails.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    user_id: str
    model_id: str
    
    # Granular permissions
    can_use: bool = True  # Can run inference
    can_view: bool = True  # Can view model details
    can_edit: bool = False  # Can modify model settings
    can_delete: bool = False  # Can delete model
    
    # Audit and expiry
    granted_by_id: str  # User who granted access
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
    
    def is_expired(self) -> bool:
        """Check if access has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            permission: Permission to check (use, view, edit, delete)
            
        Returns:
            True if permission is granted and not expired
        """
        if self.is_expired():
            return False
        
        permission_map = {
            "use": self.can_use,
            "view": self.can_view,
            "edit": self.can_edit,
            "delete": self.can_delete
        }
        
        return permission_map.get(permission, False)


# ================================
# Inference Job
# ================================

class InferenceJobDocument(BaseModel):
    """
    Inference Job document.
    
    Tracks inference tasks for async processing via Celery.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    model_id: str
    user_id: Optional[str] = None
    
    # Input/Output
    input_path: str
    output_path: Optional[str] = None
    
    # Status tracking
    status: InferenceStatus = InferenceStatus.PENDING
    celery_task_id: Optional[str] = None
    
    # Results
    processing_time_ms: Optional[float] = None
    num_detections: Optional[int] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# Camera
# ================================

class CameraDocument(BaseModel):
    """
    Camera document.
    
    Stores camera configuration for video stream processing.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Stream configuration
    stream_url: str
    protocol: CameraProtocol
    username: Optional[str] = None
    encrypted_password: Optional[str] = None
    
    # Stream settings
    fps: int = 30
    resolution: str = "1920x1080"
    
    # Status
    is_active: bool = True
    is_streaming: bool = False
    last_seen_at: Optional[datetime] = None
    
    # Owner
    owner_id: str
    
    # Metadata
    location: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# Camera Event
# ================================

class CameraEventDocument(BaseModel):
    """
    Camera Event document.
    
    Stores camera events (motion detection, alerts, etc.)
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    camera_id: str
    event_type: str  # motion, person_detected, vehicle_detected, etc.
    confidence: Optional[float] = None
    
    # Event data
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# Audit Log
# ================================

class AuditLogDocument(BaseModel):
    """
    Audit Log document.
    
    Tracks all important system actions for security and compliance.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    user_id: Optional[str] = None
    action: str  # login, logout, model_upload, inference_run, etc.
    resource_type: Optional[str] = None  # model, camera, user, etc.
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# System Setting
# ================================

class SystemSettingDocument(BaseModel):
    """
    System Setting document.
    
    Stores application-wide configuration settings.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    key: str = Field(..., unique=True)
    value: Any
    category: str = "general"
    description: Optional[str] = None
    is_public: bool = False  # Can be accessed by non-admin users
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
