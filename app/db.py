from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_db]


async def ensure_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.pending_registrations.create_index("email", unique=True)
    await db.photos.create_index("uploaded_at")
    await db.blog_entries.create_index("published_at")
    await db.activities.create_index("published_at")
