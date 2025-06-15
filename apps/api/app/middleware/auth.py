from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from ..core.config import settings

_security = HTTPBearer()

def _decode(token: str):
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(_security),
):
    payload = _decode(cred.credentials)
    return {"user_id": payload["sub"]}
