from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    id: str | None = None
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str
    password_hash: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
