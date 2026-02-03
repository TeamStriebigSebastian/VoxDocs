from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum
from app.models.practice import UserRole

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: Optional[bool] = True
    role: UserRole = UserRole.ASSISTANT
    language: str = "de"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    language: Optional[str] = None

class UserInDBBase(UserBase):
    id: int
    practice_id: int
    
    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
