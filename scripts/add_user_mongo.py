#!/usr/bin/env python3
"""Add a user directly to MongoDB.

Usage:
    python scripts/add_user_mongo.py my_user_name my_secret_password --email a_email@gmail.com
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from passlib.hash import bcrypt
from pymongo import MongoClient


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Añade un usuario a MongoDB directamente.")
    parser.add_argument("username", help="Nombre de usuario (si no se indica email, se usará aquí).")
    parser.add_argument("password", help="Contraseña del usuario.")
    parser.add_argument("--email", help="Email del usuario.")
    parser.add_argument("--full-name", dest="full_name", help="Nombre completo del usuario.")
    parser.add_argument("--phone", help="Teléfono de contacto.")
    parser.add_argument("--city", help="Ciudad del usuario.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    email = args.email or args.username

    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_db]

    existing = db.users.find_one({"email": email})
    if existing:
        print(f"El usuario con email '{email}' ya existe.")
        return 1

    payload = {
        "email": email,
        "password_hash": bcrypt.hash(args.password),
        "is_admin": False,
        "created_at": datetime.utcnow(),
        "username": args.username,
    }
    if args.full_name:
        payload["full_name"] = args.full_name
    if args.phone:
        payload["phone"] = args.phone
    if args.city:
        payload["city"] = args.city

    db.users.insert_one(payload)
    print(f"Usuario '{email}' creado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
