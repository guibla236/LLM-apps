from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from modules.config import get_env_var
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

MONGODB_URI = get_env_var("MONGODB_URI")
MONGODB_DB_NAME = get_env_var("MONGODB_DB_NAME")

class Database:
    client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase
    def __init__(self, client: AsyncIOMotorClient, db: AsyncIOMotorDatabase):
        self.client = client
        self.db = db

db: Optional[Database] = None

async def connect_to_mongo():
    global db
    
    if MONGODB_DB_NAME is None:
        raise Exception("MONGODB_DB_NAME environment variable is not set.")
    
    client = AsyncIOMotorClient(MONGODB_URI)
    db_instance = client[MONGODB_DB_NAME]
    
    if not isinstance(db_instance, AsyncIOMotorDatabase):
        raise Exception("Failed to connect to the MongoDB database.")
    
    db = Database(client, db_instance)
    
    # Create unique indexes
    await db.db.users.create_index("username", unique=True)
    await db.db.users.create_index("email", unique=True)
    await db.db.feature_flags.create_index("name", unique=True)
    await db.db.registrations.create_index("timestamp")
    
    # Indexes for qa_pairs collection (Stack Exchange corpus + future)
    await db.db.qa_pairs.create_index("ticketId", unique=True)
    await db.db.qa_pairs.create_index("community")
    
    print(f"Connected to MongoDB: {MONGODB_DB_NAME} (Indexes ensured)")

async def close_mongo_connection():
    if db is not None:
        db.client.close()
        print("Closed MongoDB connection")
    else:
        print("No MongoDB connection to close")

def get_database():
    if db is None:
        raise Exception("Database connection is not established. Please call connect_to_mongo() first.")
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
