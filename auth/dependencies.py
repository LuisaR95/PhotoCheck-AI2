"""
PhotoCheck AI - Dependencias de autenticación para FastAPI
--------------------------------------------------------------
get_current_user: valida el token JWT que envía el navegador.
require_role(...): además exige que el usuario tenga uno de los
roles permitidos (ej. solo "administrador" puede ver el dashboard).
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from auth.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión. Vuelve a iniciar sesión.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Tu sesión expiró, inicia sesión de nuevo.")
    except jwt.InvalidTokenError:
        raise credentials_error

    username, role = payload.get("sub"), payload.get("role")
    if username is None or role is None:
        raise credentials_error
    return {"username": username, "role": role}


def require_role(*allowed_roles: str):
    """Uso: Depends(require_role("administrador")) o Depends(require_role("operario", "administrador"))"""
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu rol ('{current_user['role']}') no tiene acceso a este recurso.",
            )
        return current_user
    return checker
