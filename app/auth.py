from passlib.hash import bcrypt

from app.config import settings
from app.db import db


async def authenticate_user(email: str, password: str) -> dict | None:
    if (
        settings.admin_email
        and settings.admin_password
        and email == settings.admin_email
        and password == settings.admin_password
    ):
        return {"email": email, "is_admin": True}
    user = await db.users.find_one({"email": email})
    if not user:
        return None
    if not bcrypt.verify(password, user.get("password_hash", "")):
        return None
    return user


async def create_user(email: str, password: str) -> dict:
    password_hash = bcrypt.hash(password)
    user = {
        "email": email,
        "password_hash": password_hash,
        "is_admin": False,
        "permissions": {
            "photos": False,
            "blog": False,
            "activities": False,
            "photos_supervised": False,
            "blog_supervised": False,
            "activities_supervised": False,
        },
    }
    await db.users.insert_one(user)
    return user
