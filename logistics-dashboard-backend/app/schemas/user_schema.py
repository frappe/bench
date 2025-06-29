from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import datetime

# Schema for creating a new user (input for /register)
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    role: Optional[str] = "user" # Default role

# Schema for user data returned by the API (output, excludes password)
class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    role: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True # Equivalent to orm_mode = True in Pydantic v1

# Schema for login request
class UserLogin(BaseModel):
    email: EmailStr # Or username, depending on login method
    password: str

# Schema for the data encoded in the JWT token
class TokenData(BaseModel):
    email: Optional[EmailStr] = None
    # sub: Optional[str] = None # 'sub' is a standard JWT claim for subject (often user ID or email)

# Schema for the token response
class Token(BaseModel):
    access_token: str
    token_type: str
    # Optionally, include user details here if needed on login response
    # user: Optional[UserOut] = None

# Schema for updating a user (example, can be expanded)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role: Optional[str] = None
    # Password update should be a separate, dedicated endpoint/schema for security

    class Config:
        from_attributes = True
