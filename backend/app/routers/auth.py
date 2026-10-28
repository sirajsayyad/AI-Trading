"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import (
    register_user, authenticate_user, get_user_by_id,
    decode_token, create_access_token, rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── Schemas ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=10, max_length=72)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        categories = (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if not all(categories):
            raise ValueError("Password must include upper, lower, number, and symbol")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# ─── Auth Dependency ─────────────────────────────────────

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FastAPI dependency to extract current user from JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# ─── Endpoints ───────────────────────────────────────────

@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    result = await register_user(
        db=db,
        email=req.email,
        username=req.username,
        password=req.password,
        role="student",
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"message": "Registration successful", "user": result}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive JWT tokens."""
    result = await authenticate_user(db, req.email, req.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return result


@router.post("/refresh")
async def refresh_token(req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an access token using a refresh token."""
    payload = decode_token(req.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    replacement = await rotate_refresh_token(db, req.refresh_token)
    if not replacement:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = create_access_token(user["id"], user["role"])

    return {
        "access_token": new_access,
        "refresh_token": replacement,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user
