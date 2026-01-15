from passlib.hash import bcrypt

from app.db import db


async def authenticate_user(email: str, password: str) -> dict | None:
    user = await db.users.find_one({"email": email})
    if not user:
        return None
    if not bcrypt.verify(password, user.get("password_hash", "")):
        return None
    return user


async def create_user(email: str, password: str) -> dict:
    password_hash = bcrypt.hash(password)
    user = {"email": email, "password_hash": password_hash, "is_admin": False}
    await db.users.insert_one(user)
    return user
