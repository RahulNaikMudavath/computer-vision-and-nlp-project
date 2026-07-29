import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.models.database import get_db, User, UserSettings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user
)
from app.core.config import settings

logger = logging.getLogger("document_ocr.api.auth")

# Initialize router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# =====================================================================
# Request & Response Schemas (DTOs)
# =====================================================================

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters.")
    full_name: Optional[str] = Field(None, description="Full name of the user.")


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserSettingsSchema(BaseModel):
    theme: str
    language: str
    default_ocr_language: str
    email_notifications: bool


class UserProfileResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    role: str
    avatar_url: Optional[str]
    created_at: str
    settings: Optional[UserSettingsSchema]

# =====================================================================
# Endpoints
# =====================================================================

@router.post(
    "/register",
    response_model=UserProfileResponse,
    summary="Register a new user account",
    description="Registers a new user, hashes password, creates default settings, and designates the first account as Admin."
)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)) -> dict:
    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered."
        )

    # First user registered in the system is designated as Admin to simplify setup
    user_count = db.query(User).count()
    assigned_role = "Admin" if user_count == 0 else "Standard User"
    
    # Hash password
    hashed_pwd = get_password_hash(request.password)
    
    # Create user
    new_user = User(
        email=request.email,
        hashed_password=hashed_pwd,
        full_name=request.full_name,
        role=assigned_role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create default settings
    new_settings = UserSettings(
        user_id=new_user.id,
        theme="light",
        language="en",
        default_ocr_language="en",
        email_notifications=True
    )
    db.add(new_settings)
    db.commit()
    db.refresh(new_user) # reload user relationships
    
    logger.info(f"Successfully registered user: {new_user.email} (Role: {new_user.role})")
    
    # Formulate profile response
    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "avatar_url": new_user.avatar_url,
        "created_at": new_user.created_at.isoformat(),
        "settings": {
            "theme": new_settings.theme,
            "language": new_settings.language,
            "default_ocr_language": new_settings.default_ocr_language,
            "email_notifications": new_settings.email_notifications
        }
    }


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to receive JWT tokens",
    description="Authenticates user credentials and returns access and refresh tokens."
)
async def login(request: UserLoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )
        
    # Generate tokens
    access = create_access_token({"sub": user.email, "role": user.role})
    refresh = create_refresh_token({"sub": user.email})
    
    logger.info(f"User logged in: {user.email}")
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access tokens",
    description="Validate refresh token and issue a fresh access token."
)
async def refresh_tokens(request: RefreshTokenRequest, db: Session = Depends(get_db)) -> dict:
    try:
        # Decode and validate refresh token
        payload = decode_token(request.refresh_token, settings.JWT_REFRESH_SECRET_KEY)
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token context."
            )
    except Exception:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token."
         )
         
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated or missing."
        )
        
    access = create_access_token({"sub": user.email, "role": user.role})
    refresh = create_refresh_token({"sub": user.email})
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }


@router.post(
    "/logout",
    summary="User logout",
    description="Logs user out. Note: in stateless JWTs this API immediately signals client clearing."
)
async def logout(current_user: User = Depends(get_current_user)) -> dict:
    logger.info(f"User logged out: {current_user.email}")
    return {"success": True, "message": "Successfully logged out."}


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get profile of authenticated user",
    description="Returns the profile structure of the currently logged in user."
)
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    # Ensure default settings exist just in case
    user_settings = current_user.settings
    if not user_settings:
        user_settings = UserSettings(
            theme="light",
            language="en",
            default_ocr_language="en",
            email_notifications=True
        )
        
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at.isoformat(),
        "settings": {
            "theme": user_settings.theme,
            "language": user_settings.language,
            "default_ocr_language": user_settings.default_ocr_language,
            "email_notifications": user_settings.email_notifications
        }
    }
