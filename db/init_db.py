"""
PhotoCheck AI - Inicialización de tablas
--------------------------------------------------------------
Crea las tablas 'properties' y 'visits' dentro de la base de datos
(que ya debe existir — corre antes db/create_database.py).

Uso:
    python -m db.init_db
"""

from db.database import engine, Base
from db import models  # noqa: F401  (necesario para que SQLAlchemy registre los modelos)


def main():
    print("🗄️  Creando tablas en PostgreSQL (si no existen)...")
    Base.metadata.create_all(bind=engine)
    print("✅ Listo: 'properties' y 'visits' están creadas.")


if __name__ == "__main__":
    main()
