"""
PhotoCheck AI - Crear la base de datos en PostgreSQL
--------------------------------------------------------------
PostgreSQL no te deja crear una base de datos automáticamente ANTES
de conectarte a ella, así que este script se conecta a la base de
datos de mantenimiento "postgres" (que siempre existe) y crea la
base de datos indicada en DATABASE_URL si todavía no existe.

Uso:
    python -m db.create_database

Requisito: ajusta DATABASE_URL en tu .env con el usuario/password
correctos de tu instalación local de PostgreSQL.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/photocheck")
parsed = urlparse(DATABASE_URL)

DB_NAME = parsed.path.lstrip("/")
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432


def main():
    print(f"🔌 Conectando a PostgreSQL en {DB_HOST}:{DB_PORT} como '{DB_USER}'...")
    conn = psycopg2.connect(
        dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
    )
    conn.autocommit = True  # CREATE DATABASE no puede correr dentro de una transacción
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()

    if exists:
        print(f"ℹ️  La base de datos '{DB_NAME}' ya existe, no se crea de nuevo.")
    else:
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"✅ Base de datos '{DB_NAME}' creada.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
