"""
NexusAI Platform - Core Configuration Module
Loads and manages all system configurations from YAML files and environment variables

This module provides centralized configuration management with:
- Environment variable loading
- YAML configuration parsing
- Type validation
- Default values
- Production-ready settings
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """
    Main application settings loaded from environment variables and config files.
    
    Attributes are loaded with priority:
    1. Environment variables
    2. .env file
    3. Default values
    """
    
    # ================================
    # System Settings
    # ================================
    SYSTEM_NAME: str = "NexusAI Platform"
    SYSTEM_VERSION: str = "1.0.0"
    SYSTEM_DESCRIPTION: str = "Advanced modular AI inference platform"
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # ================================
    # API Settings
    # ================================
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_WORKERS: int = Field(default=8, env="API_WORKERS")
    API_TIMEOUT: int = Field(default=120, env="API_TIMEOUT")
    API_VERSION: str = Field(default="v1", env="API_VERSION")
    API_DOCS_ENABLED: bool = Field(default=False, env="API_DOCS_ENABLED")
    SWAGGER_UI_PATH: str = "/docs"
    REDOC_PATH: str = "/redoc"
    LIMIT_CONCURRENCY: int = Field(default=1000, env="LIMIT_CONCURRENCY")
    BACKLOG: int = Field(default=2048, env="BACKLOG")
    
    # ================================
    # Security Settings
    # ================================
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    PASSWORD_MIN_LENGTH: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    LOCKOUT_DURATION_MINUTES: int = Field(default=15, env="LOCKOUT_DURATION_MINUTES")
    
    # ================================
    # Database Settings
    # ================================
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=50, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=25, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=10, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=1800, env="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(default=True, env="DB_POOL_PRE_PING")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")
    
    # ================================
    # Redis Settings
    # ================================
    REDIS_HOST: str = Field(default="redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_MAXMEMORY: str = Field(default="2gb", env="REDIS_MAXMEMORY")
    
    # ================================
    # Storage Settings (MinIO/S3)
    # ================================
    MINIO_ENDPOINT: str = Field(default="minio:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(..., env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(..., env="MINIO_SECRET_KEY")
    MINIO_SECURE: bool = Field(default=False, env="MINIO_SECURE")
    MINIO_REGION: str = Field(default="us-east-1", env="MINIO_REGION")
    
    # ================================
    # Celery Settings
    # ================================
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")
    CELERY_CONCURRENCY: int = Field(default=8, env="CELERY_CONCURRENCY")
    CELERY_MAX_TASKS_PER_CHILD: int = Field(default=100, env="CELERY_MAX_TASKS_PER_CHILD")
    
    # ================================
    # MLflow Settings
    # ================================
    MLFLOW_TRACKING_URI: str = Field(default="http://mlflow:5000", env="MLFLOW_TRACKING_URI")
    MLFLOW_EXPERIMENT_NAME: str = Field(default="nexusai-models", env="MLFLOW_EXPERIMENT_NAME")
    
    # ================================
    # Inference Settings
    # ================================
    INFERENCE_DEVICE: str = Field(default="cuda", env="INFERENCE_DEVICE")
    INFERENCE_BATCH_SIZE: int = Field(default=16, env="INFERENCE_BATCH_SIZE")
    INFERENCE_WORKERS: int = Field(default=8, env="INFERENCE_WORKERS")
    INFERENCE_MAX_WORKERS: int = Field(default=4, env="INFERENCE_MAX_WORKERS")
    INFERENCE_QUEUE_SIZE: int = Field(default=256, env="INFERENCE_QUEUE_SIZE")
    USE_ONNX: bool = Field(default=True, env="USE_ONNX")
    USE_TENSORRT: bool = Field(default=True, env="USE_TENSORRT")
    USE_FP16: bool = Field(default=True, env="USE_FP16")
    
    # ================================
    # Model Settings
    # ================================
    MODELS_PATH: Path = Field(default=Path("/app/models"), env="MODELS_PATH")
    MODELS_CACHE_PATH: Path = Field(default=Path("/app/cache/models"), env="MODELS_CACHE_PATH")
    AUTO_DOWNLOAD_MODELS: bool = Field(default=True, env="AUTO_DOWNLOAD_MODELS")
    MODEL_WARMUP_ENABLED: bool = Field(default=True, env="MODEL_WARMUP_ENABLED")
    
    # ================================
    # Camera Settings
    # ================================
    MAX_CAMERAS: int = Field(default=100, env="MAX_CAMERAS")
    CAMERA_BUFFER_SIZE: int = Field(default=60, env="CAMERA_BUFFER_SIZE")
    CAMERA_RECONNECT_INTERVAL: int = Field(default=5, env="CAMERA_RECONNECT_INTERVAL")
    RECORDINGS_PATH: Path = Field(default=Path("/data/recordings"), env="RECORDINGS_PATH")
    RECORDINGS_RETENTION_DAYS: int = Field(default=7, env="RECORDINGS_RETENTION_DAYS")
    
    # ================================
    # Logging Settings
    # ================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # ================================
    # Monitoring Settings
    # ================================
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    JAEGER_ENABLED: bool = Field(default=True, env="JAEGER_ENABLED")
    JAEGER_HOST: str = Field(default="jaeger", env="JAEGER_HOST")
    JAEGER_PORT: int = Field(default=6831, env="JAEGER_PORT")
    
    # ================================
    # Rate Limiting
    # ================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # ================================
    # File Upload Settings
    # ================================
    MAX_UPLOAD_SIZE_MB: int = Field(default=100, env="MAX_UPLOAD_SIZE_MB")
    ALLOWED_UPLOAD_EXTENSIONS: str = Field(
        default="jpg,jpeg,png,bmp,webp,mp4,avi,mov",
        env="ALLOWED_UPLOAD_EXTENSIONS"
    )
    
    # ================================
    # CORS Settings
    # ================================
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # ================================
    # Hot Reload (Development)
    # ================================
    HOT_RELOAD: bool = Field(default=False, env="HOT_RELOAD")
    
    # ================================
    # Configuration File Paths
    # ================================
    CONFIG_DIR: Path = Field(default=Path(__file__).parent.parent.parent / "config")
    
    @validator("CORS_ORIGINS", "ALLOWED_HOSTS", pre=True)
    def parse_list_from_string(cls, v):
        """Parse comma-separated string into list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    @validator("ALLOWED_UPLOAD_EXTENSIONS")
    def validate_extensions(cls, v):
        """Validate and normalize file extensions."""
        if isinstance(v, str):
            return v.lower().replace(" ", "")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class ConfigManager:
    """
    Manages loading and caching of YAML configuration files.
    
    This class handles:
    - Loading YAML config files
    - Caching configurations
    - Hot-reloading (if enabled)
    - Config validation
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing YAML config files
        """
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self._cache: Dict[str, Any] = {}
        self._load_all_configs()
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load YAML configuration file.
        
        Args:
            filename: Name of the YAML file (with or without .yaml extension)
            
        Returns:
            Parsed YAML content as dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename = f"{filename}.yaml"
        
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config or {}
    
    def _load_all_configs(self):
        """Load all configuration files into cache."""
        config_files = [
            "system_config",
            "models_config",
            "inference_config",
            "cameras_config",
        ]
        
        for config_name in config_files:
            try:
                self._cache[config_name] = self._load_yaml(config_name)
            except FileNotFoundError:
                # Config file is optional
                self._cache[config_name] = {}
            except Exception as e:
                print(f"Warning: Failed to load {config_name}.yaml: {e}")
                self._cache[config_name] = {}
    
    def get(self, config_name: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            config_name: Name of the config file (without .yaml)
            key: Dot-separated key path (e.g., "api.host")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        config = self._cache.get(config_name, {})
        
        if key is None:
            return config
        
        # Navigate nested keys
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def reload(self, config_name: Optional[str] = None):
        """
        Reload configuration files.
        
        Args:
            config_name: Specific config to reload, or None to reload all
        """
        if config_name:
            self._cache[config_name] = self._load_yaml(config_name)
        else:
            self._load_all_configs()
    
    @property
    def system_config(self) -> Dict[str, Any]:
        """Get system configuration."""
        return self._cache.get("system_config", {})
    
    @property
    def models_config(self) -> Dict[str, Any]:
        """Get models configuration."""
        return self._cache.get("models_config", {})
    
    @property
    def inference_config(self) -> Dict[str, Any]:
        """Get inference configuration."""
        return self._cache.get("inference_config", {})
    
    @property
    def cameras_config(self) -> Dict[str, Any]:
        """Get cameras configuration."""
        return self._cache.get("cameras_config", {})


# Global instances
settings = Settings()
config = ConfigManager()


# Export
__all__ = ["settings", "config", "Settings", "ConfigManager"]
