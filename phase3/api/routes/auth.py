# phase3/api/routes/auth.py

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import structlog

from vault.db import vault_db
from vault.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

router = APIRouter()
logger = structlog.get_logger()

# We will import the auth dependency dynamically or inline in Phase 3 to avoid circular dependency
# if we protect /auth/create-user now.
# To do it cleanly, we can import get_current_active_user inside the endpoint or define it at module level.
from api.middleware.auth_dep import get_current_active_user

class LoginRequest(BaseModel):
    username: str = Field(..., description="Analyst or Admin username")
    password: str = Field(..., description="Password")

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    role: str

class RefreshRequest(BaseModel):
    refresh_token: str

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, description="New user's username")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    full_name: str = Field(..., description="User's full name")
    role: str = Field(..., pattern="^(admin|analyst)$", description="Role: admin or analyst")


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    username = body.username.lower().strip()
    password = body.password
    
    user = vault_db.get_user(username)
    if not user:
        logger.warning("login_failed_user_not_found", username=username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if account is active
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
        
    # Check if user is locked
    locked_until_str = user.get("locked_until")
    if locked_until_str:
        try:
            locked_until = datetime.fromisoformat(locked_until_str)
            now = datetime.now(timezone.utc)
            if now < locked_until:
                minutes_left = int((locked_until - now).total_seconds() / 60) + 1
                logger.warning("login_failed_account_locked", username=username, minutes_left=minutes_left)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account is temporarily locked due to multiple failed login attempts. Try again in {minutes_left} minutes."
                )
        except Exception as e:
            logger.error("parse_lock_time_failed", username=username, error=str(e))
            
    # Verify password
    if verify_password(password, user["hashed_password"]):
        # Success: reset attempts
        vault_db.reset_failed_attempts(username)
        
        token_data = {"sub": username, "role": user["role"]}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        logger.info("login_successful", username=username, role=user["role"])
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            username=username,
            role=user["role"]
        )
    else:
        # Failure: increment attempts and potentially lock
        failed_count = vault_db.increment_failed_attempts(username)
        logger.warning("login_failed_invalid_password", username=username, failed_attempts=failed_count)
        
        if failed_count >= 5:
            vault_db.lock_user(username, lock_minutes=15)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is temporarily locked for 15 minutes due to 5 consecutive failed login attempts."
            )
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )


@router.post("/auth/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
        
        # Verify it is actually a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
            
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
            
        user = vault_db.get_user(username)
        if not user or not user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found"
            )
            
        # Issue new access token
        new_data = {"sub": username, "role": user["role"]}
        new_access_token = create_access_token(data=new_data)
        
        logger.info("token_refreshed_successfully", username=username)
        return RefreshResponse(access_token=new_access_token)
        
    except Exception as e:
        logger.warning("token_refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.post("/auth/create-user", status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateRequest, current_user: dict = Depends(get_current_active_user)):
    # Restrict to Admin
    if current_user.get("role") != "admin":
        logger.warning("create_user_unauthorized_attempt", actor=current_user.get("sub"))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can register new accounts"
        )
        
    # Check if user already exists
    existing_user = vault_db.get_user(body.username.lower().strip())
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )
        
    hashed_pw = hash_password(body.password)
    success = vault_db.create_user(
        username=body.username,
        hashed_password=hashed_pw,
        full_name=body.full_name,
        role=body.role
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register new account in the database"
        )
        
    logger.info("user_created_successfully", creator=current_user.get("sub"), username=body.username, role=body.role)
    return {"success": True, "message": f"User '{body.username}' registered successfully with role '{body.role}'"}
