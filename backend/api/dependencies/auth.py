"""
NexusAI Platform - Authentication Dependencies
FastAPI dependencies for authentication and authorization
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.mongodb import get_database
from backend.core.logging_config import get_logger
from backend.core.security import decode_token
from backend.models.mongodb_models import UserRole

logger = get_logger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """
    Get the current authenticated user from JWT token or API key.
    
    Args:
        credentials: Bearer token credentials
        api_key: API key from header
        db: Database session
        
    Returns:
        Authenticated user document
        
    Raises:
        HTTPException: If authentication fails
    """
    # Try JWT token first
    if credentials:
        token = credentials.credentials
        payload = decode_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Get user from database
        user = await db.users.find_one({"_id": user_id})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
        
        return user
    
    # Try API key
    elif api_key:
        user = await db.users.find_one({"api_key": api_key})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        
        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
        
        return user
    
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get current active user.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def require_role(required_role: UserRole):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: dict = Depends(get_current_active_user)) -> dict:
        # Admin has access to everything
        if current_user.get("role") == UserRole.ADMIN:
            return current_user
        
        # Check specific role
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}",
            )
        
        return current_user
    
    return role_checker


# Convenience dependencies
require_admin = require_role(UserRole.ADMIN)
require_user = require_role(UserRole.USER)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.
    Used for endpoints that work with or without authentication.
    
    Args:
        credentials: Bearer token credentials
        api_key: API key from header
        db: Database session
        
    Returns:
        User if authenticated, None otherwise
    """
    try:
        return await get_current_user(credentials, api_key, db)
    except HTTPException:
        return None
