"""
Authentication core module.
Handles JWT tokens and password hashing per V1 requirements.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration (per V1 requirements §4.1)
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 14
ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # user_id
    tenant_id: int
    type: str  # "access" or "refresh"
    exp: Optional[datetime] = None


class TokenPair(BaseModel):
    """Login response with access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def create_access_token(user_id: int, tenant_id: int) -> str:
    """Create a short-lived access token (15 minutes)."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "type": "access",
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, tenant_id: int) -> str:
    """Create a long-lived refresh token (14 days)."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "type": "refresh",
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_token_pair(user_id: int, tenant_id: int) -> TokenPair:
    """Create both access and refresh tokens for login."""
    return TokenPair(
        access_token=create_access_token(user_id, tenant_id),
        refresh_token=create_refresh_token(user_id, tenant_id)
    )


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        return None
