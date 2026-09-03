"""
PhotoCheck AI - Conexión a la base de datos
--------------------------------------------------------------
Lee la URL de conexión desde el archivo .env (variable DATABASE_URL).

Formato esperado:
    postgresql://usuario:password@localhost:5432/photocheck

Copia .env.example a .env y ajusta los valores con tus credenciales
reales de PostgreSQL antes de correr cualquier script de este proyecto.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Carga el .env desde la raíz del proyecto, sin importar desde dónde se ejecute
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/photocheck")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_session():
    """Devuelve una nueva sesión de base de datos. Recuerda cerrarla (session.close())."""
    return SessionLocal()
