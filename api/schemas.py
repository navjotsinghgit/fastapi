from typing import Optional
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str            # replaced EmailStr -> str to avoid email-validator
    password: str
    name: Optional[str] = None
    role: Optional[str] = None
    theme_preference: Optional[str] = "dark"

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    email: str
    name: Optional[str] = None
    role: Optional[str] = None
    theme_preference: Optional[str] = "dark"

    class Config:
        from_attributes = True