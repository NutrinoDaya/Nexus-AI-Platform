"""
NexusAI Platform - Authentication Routes (MongoDB Version)
User registration, login, token refresh, and profile management
"""

from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.api.dependencies.auth import get_current_active_user, get_current_user
from backend.core.config import settings
from backend.core.mongodb import get_database
from backend.core.logging_config import get_logger
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    get_password_hash,
    verify_password,
)
from backend.models.mongodb_models import UserRole
from backend.models.schemas import (
    RefreshTokenRequest,
    TokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
    UserWithToken,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserWithToken, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Register a new user account.
    
    - **username**: Unique username (3-100 characters)
    - **email**: Valid email address
    - **password**: Password (min 8 characters)
    - **full_name**: Optional full name
    - **role**: User role (default: user)
    """
    # Check if username exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    # Check if email exists
    existing_email = await db.users.find_one({"email": user_data.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create new user document
    hashed_password = get_password_hash(user_data.password)
    user_id = str(uuid.uuid4())
    
    new_user = {
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "full_name": user_data.full_name,
        "role": user_data.role,
        "is_active": True,
        "is_verified": False,
        "failed_login_attempts": 0,
        "locked_until": None,
        "api_key": None,
        "api_key_created_at": None,
        "last_login_at": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await db.users.insert_one(new_user)
    
    logger.info(f"New user registered: {new_user['username']}")
    
    # Generate tokens
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    
    return UserWithToken(
        id=user_id,
        username=new_user["username"],
        email=new_user["email"],
        full_name=new_user.get("full_name"),
        role=new_user["role"],
        is_active=new_user["is_active"],
        is_verified=new_user["is_verified"],
        created_at=new_user["created_at"],
        updated_at=new_user["updated_at"],
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: TokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Authenticate user and return access/refresh tokens.
    
    - **username**: Username or email
    - **password**: User password
    """
    # Find user by username or email
    user = await db.users.find_one({
        "$or": [
            {"username": credentials.username},
            {"email": credentials.username}
        ]
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Verify password
    if not verify_password(credentials.password, user["hashed_password"]):
        # Increment failed login attempts
        failed_attempts = user.get("failed_login_attempts", 0) + 1
        
        # Lock account after max attempts
        if failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            locked_until = datetime.utcnow() + timedelta(
                minutes=settings.LOCKOUT_DURATION_MINUTES
            )
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "failed_login_attempts": failed_attempts,
                    "locked_until": locked_until
                }}
            )
            
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked due to too many failed login attempts. Try again in {settings.LOCKOUT_DURATION_MINUTES} minutes.",
            )
        
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"failed_login_attempts": failed_attempts}}
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Check if account is locked
    locked_until = user.get("locked_until")
    if locked_until and locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked. Please try again later.",
        )
    
    # Check if user is active
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    # Reset failed login attempts and update last login
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_at": datetime.utcnow()
        }}
    )
    
    # Generate tokens
    access_token = create_access_token(data={"sub": user["_id"]})
    refresh_token = create_refresh_token(data={"sub": user["_id"]})
    
    logger.info(f"User logged in: {user['username']}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    payload = decode_token(refresh_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Get user
    user = await db.users.find_one({"_id": user_id})
    
    if not user or not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Generate new tokens
    access_token = create_access_token(data={"sub": user["_id"]})
    new_refresh_token = create_refresh_token(data={"sub": user["_id"]})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get current user profile.
    
    Requires authentication.
    """
    return UserResponse(
        id=current_user["_id"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        role=current_user["role"],
        is_active=current_user["is_active"],
        is_verified=current_user.get("is_verified", False),
        created_at=current_user["created_at"],
        updated_at=current_user["updated_at"],
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Update current user profile.
    
    - **email**: New email address
    - **full_name**: New full name
    """
    update_data = user_update.dict(exclude_unset=True)
    
    # Check email uniqueness if being updated
    if "email" in update_data and update_data["email"] != current_user["email"]:
        existing = await db.users.find_one({"email": update_data["email"]})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    
    # Update user
    update_data["updated_at"] = datetime.utcnow()
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": update_data}
    )
    
    # Retrieve updated user
    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    
    logger.info(f"User profile updated: {updated_user['username']}")
    
    return UserResponse(
        id=updated_user["_id"],
        username=updated_user["username"],
        email=updated_user["email"],
        full_name=updated_user.get("full_name"),
        role=updated_user["role"],
        is_active=updated_user["is_active"],
        is_verified=updated_user.get("is_verified", False),
        created_at=updated_user["created_at"],
        updated_at=updated_user["updated_at"],
    )


@router.post("/api-key/generate", response_model=dict)
async def generate_user_api_key(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Generate a new API key for the current user.
    
    **Warning**: This will invalidate the previous API key.
    """
    api_key = generate_api_key()
    api_key_created_at = datetime.utcnow()
    
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "api_key": api_key,
            "api_key_created_at": api_key_created_at
        }}
    )
    
    logger.info(f"API key generated for user: {current_user['username']}")
    
    return {
        "api_key": api_key,
        "created_at": api_key_created_at,
        "message": "Store this API key securely. It will not be shown again.",
    }


@router.delete("/api-key/revoke")
async def revoke_api_key(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Revoke the current user's API key.
    """
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "api_key": None,
            "api_key_created_at": None
        }}
    )
    
    logger.info(f"API key revoked for user: {current_user['username']}")
    
    return {"success": True, "message": "API key revoked successfully"}


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
):
    """
    Logout current user.
    
    Note: With JWT, actual logout requires token blacklisting on the client side.
    This endpoint is provided for consistency and future enhancements.
    """
    logger.info(f"User logged out: {current_user['username']}")
    
    return {
        "success": True,
        "message": "Logged out successfully. Please discard your access token.",
    }
