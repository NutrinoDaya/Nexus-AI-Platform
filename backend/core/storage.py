"""
NexusAI Platform - Object Storage Manager (MinIO/S3)
Handles file uploads, downloads, and bucket management
"""

import asyncio
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, List, Optional, Union

from minio import Minio
from minio.error import S3Error

from backend.core.config import settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

# Global MinIO client
minio_client: Optional[Minio] = None

# Bucket names
BUCKETS = {
    "models": "nexusai-models",
    "inputs": "nexusai-inputs",
    "outputs": "nexusai-outputs",
    "cameras": "nexusai-cameras",
    "datasets": "nexusai-datasets",
}


async def init_storage():
    """
    Initialize MinIO client and create buckets.
    
    Creates all required buckets if they don't exist.
    """
    global minio_client
    
    try:
        # Create MinIO client
        minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=settings.MINIO_REGION,
        )
        
        # Create buckets
        for bucket_name in BUCKETS.values():
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            else:
                logger.info(f"Bucket exists: {bucket_name}")
        
        logger.info("Object storage initialized successfully")
        
    except S3Error as e:
        logger.error(f"Failed to initialize storage: {e}", exc_info=True)
        raise


async def upload_file(
    bucket: str,
    object_name: str,
    file_data: Union[bytes, BinaryIO, Path],
    content_type: str = "application/octet-stream",
    metadata: Optional[dict] = None,
) -> str:
    """
    Upload file to object storage.
    
    Args:
        bucket: Bucket name (use BUCKETS dict keys)
        object_name: Object name/path in bucket
        file_data: File data (bytes, file object, or path)
        content_type: MIME type of the file
        metadata: Additional metadata
        
    Returns:
        Object URL
        
    Raises:
        S3Error: If upload fails
    """
    try:
        bucket_name = BUCKETS.get(bucket, bucket)
        
        # Handle different input types
        if isinstance(file_data, Path):
            minio_client.fput_object(
                bucket_name,
                object_name,
                str(file_data),
                content_type=content_type,
                metadata=metadata,
            )
        elif isinstance(file_data, bytes):
            data = BytesIO(file_data)
            minio_client.put_object(
                bucket_name,
                object_name,
                data,
                length=len(file_data),
                content_type=content_type,
                metadata=metadata,
            )
        else:
            # Assume file object
            file_data.seek(0)
            data_bytes = file_data.read()
            data = BytesIO(data_bytes)
            minio_client.put_object(
                bucket_name,
                object_name,
                data,
                length=len(data_bytes),
                content_type=content_type,
                metadata=metadata,
            )
        
        # Generate URL
        url = f"s3://{bucket_name}/{object_name}"
        logger.info(f"Uploaded file: {url}")
        
        return url
        
    except S3Error as e:
        logger.error(f"Failed to upload file: {e}", exc_info=True)
        raise


async def download_file(
    bucket: str,
    object_name: str,
    file_path: Optional[Path] = None,
) -> Union[bytes, Path]:
    """
    Download file from object storage.
    
    Args:
        bucket: Bucket name
        object_name: Object name/path
        file_path: Local path to save file (if None, returns bytes)
        
    Returns:
        Downloaded file bytes or path
        
    Raises:
        S3Error: If download fails
    """
    try:
        bucket_name = BUCKETS.get(bucket, bucket)
        
        if file_path:
            # Download to file
            minio_client.fget_object(bucket_name, object_name, str(file_path))
            logger.info(f"Downloaded file to: {file_path}")
            return file_path
        else:
            # Download to memory
            response = minio_client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"Downloaded file: {object_name}")
            return data
            
    except S3Error as e:
        logger.error(f"Failed to download file: {e}", exc_info=True)
        raise


async def delete_file(bucket: str, object_name: str):
    """
    Delete file from object storage.
    
    Args:
        bucket: Bucket name
        object_name: Object name/path
        
    Raises:
        S3Error: If deletion fails
    """
    try:
        bucket_name = BUCKETS.get(bucket, bucket)
        minio_client.remove_object(bucket_name, object_name)
        logger.info(f"Deleted file: {object_name}")
        
    except S3Error as e:
        logger.error(f"Failed to delete file: {e}", exc_info=True)
        raise


async def list_files(bucket: str, prefix: str = "") -> List[str]:
    """
    List files in bucket.
    
    Args:
        bucket: Bucket name
        prefix: Object prefix filter
        
    Returns:
        List of object names
    """
    try:
        bucket_name = BUCKETS.get(bucket, bucket)
        objects = minio_client.list_objects(bucket_name, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]
        
    except S3Error as e:
        logger.error(f"Failed to list files: {e}", exc_info=True)
        raise


async def get_file_url(bucket: str, object_name: str, expires: int = 3600) -> str:
    """
    Get presigned URL for file access.
    
    Args:
        bucket: Bucket name
        object_name: Object name/path
        expires: URL expiration in seconds
        
    Returns:
        Presigned URL
    """
    try:
        bucket_name = BUCKETS.get(bucket, bucket)
        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=expires,
        )
        return url
        
    except S3Error as e:
        logger.error(f"Failed to generate presigned URL: {e}", exc_info=True)
        raise


async def check_storage_health() -> bool:
    """
    Check storage connectivity for health checks.
    
    Returns:
        bool: True if storage is healthy
    """
    try:
        # Try to list buckets
        buckets = minio_client.list_buckets()
        return True
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return False


# Export
__all__ = [
    "BUCKETS",
    "init_storage",
    "upload_file",
    "download_file",
    "delete_file",
    "list_files",
    "get_file_url",
    "check_storage_health",
]
