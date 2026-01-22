from checkpoint import AsyncMongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize MongoDB Connection for Checkpointer

MONGODB_URI = os.getenv("MONGODB_URI")
mongo_client = AsyncIOMotorClient(MONGODB_URI)
db_name = os.getenv("MONGODB_DB_NAME", "ticket_system")
db = mongo_client[db_name]

get_db = lambda: db

get_checkpointer = lambda: AsyncMongoDBSaver(get_db())