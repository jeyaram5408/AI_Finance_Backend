from pydantic import BaseModel
from typing import Optional

class AdminUserStatusUpdate(BaseModel):
    is_active: bool

class AdminUserRoleUpdate(BaseModel):
    role: str

class AdminUserResponse(BaseModel):
    id: int
    user_id: Optional[str] = None
    name: str
    email: str
    role: Optional[str] = None
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True
