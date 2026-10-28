"""
Authentication service — JWT tokens + bcrypt password hashing.
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import RefreshSession, User

settings = get_settings()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, role: str) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "jti": token_urlsafe(24),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


async def issue_refresh_token(db: AsyncSession, user_id: str) -> str:
    token = create_refresh_token(user_id)
    db.add(RefreshSession(
        user_id=user_id,
        token_hash=token_hash(token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    ))
    return token


async def rotate_refresh_token(db: AsyncSession, token: str) -> str | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    session = await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash(token),
            RefreshSession.revoked_at.is_(None),
        )
    )
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return None
    session.revoked_at = datetime.now(timezone.utc)
    return await issue_refresh_token(db, payload["sub"])


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def register_user(
    db: AsyncSession,
    email: str,
    username: str,
    password: str,
    role: str = "student",
) -> dict:
    """Register a new user."""
    # Check existing
    stmt = select(User).where((User.email == email) | (User.username == username))
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.email == email:
            return {"error": "Email already registered"}
        return {"error": "Username already taken"}

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    refresh_token = await issue_refresh_token(db, user.id)
    await db.commit()
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
    }


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[dict]:
    """Authenticate a user and return tokens."""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    refresh_token = await issue_refresh_token(db, user.id)
    await db.commit()

    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
        },
    }


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[dict]:
    """Get user info by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
