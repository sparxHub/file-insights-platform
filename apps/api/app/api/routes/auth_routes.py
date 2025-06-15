from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel, EmailStr

from ...core.config import settings


class LoginBody(BaseModel):
    email: EmailStr
    password: str

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(body: LoginBody):
    if body.email != "demo@example.com" or body.password != "secret":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad creds")
    exp = datetime.utcnow() + timedelta(minutes=settings.jwt_expires_minutes)
    token = jwt.encode({"sub": "demo-user-id", "exp": exp}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {"access_token": token, "token_type": "bearer"}
