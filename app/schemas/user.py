from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class RoleBase(BaseModel):
    role_name: str


class RoleResponse(RoleBase):
    role_id: int
    description: Optional[str] = None

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)



class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)


class PasswordUpdate(BaseModel):
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class UserPasswordUpdate(PasswordUpdate):
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserInDB(UserBase):
    user_id: int
    date_joined: datetime
    is_active: bool

    class Config:
        from_attributes = True




class UserResponse(UserInDB):
    api_key: str


class KeyResponse(BaseModel):
    api_key: str

class UserToken(UserBase):
    user_id: int
    role: int
    key_expires_at:Optional[str]=None



