"""
PhotoCheck AI - Crear usuarios (operario / administrador)
--------------------------------------------------------------
Uso:
    python -m db.create_user --username juan --password ClaveSegura123 --role operario --name "Juan Pérez"
    python -m db.create_user --username admin --password ClaveSegura456 --role administrador --name "María Supervisora"
"""

import argparse

from db.database import get_session
from db.models import User
from auth.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Crea un usuario operario o administrador.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", required=True, choices=["operario", "administrador"])
    parser.add_argument("--name", default=None)
    args = parser.parse_args()

    session = get_session()
    try:
        existing = session.query(User).filter_by(username=args.username).first()
        if existing:
            print(f"❌ Ya existe un usuario con el username '{args.username}'.")
            return

        user = User(
            username=args.username,
            hashed_password=hash_password(args.password),
            role=args.role,
            full_name=args.name,
        )
        session.add(user)
        session.commit()
        print(f"✅ Usuario '{args.username}' creado con rol '{args.role}'.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
