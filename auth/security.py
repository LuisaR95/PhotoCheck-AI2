"""
PhotoCheck AI - Seguridad: contraseñas y tokens JWT
--------------------------------------------------------------
- Las contraseñas NUNCA se guardan en texto plano — se guarda un
  hash (bcrypt) que no se puede revertir.
- Al iniciar sesión, se emite un token JWT (un "pase" firmado que
  el navegador guarda y reenvía en cada petición) con el usuario y
  su rol adentro. Expira después de 8 horas.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cambia-esto-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas, una jornada laboral


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Lanza jwt.ExpiredSignatureError o jwt.InvalidTokenError si el token no sirve."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
