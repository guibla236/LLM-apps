import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "ticket_system")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(MONGODB_URI)
    db.db = db.client[MONGODB_DB_NAME]
    print(f"Connected to MongoDB: {MONGODB_DB_NAME}")

async def close_mongo_connection():
    db.client.close()
    print("Closed MongoDB connection")

def get_database():
    return db.db

async def is_feature_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled in the database."""
    database = get_database()
    if database is None:
        return False
    
    flag = await database.feature_flags.find_one({"name": flag_name})
    if flag:
        return flag.get("enabled", False)
    return False
