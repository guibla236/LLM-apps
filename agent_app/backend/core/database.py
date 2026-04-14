from core.checkpoint import AsyncMongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_env_var

# Initialize MongoDB Connection for Checkpointer

MONGODB_URI = get_env_var("MONGODB_URI")
DB_NAME = get_env_var("MONGODB_DB_NAME")

if MONGODB_URI is None or DB_NAME is None:
    raise Exception("MONGODB_URI and MONGODB_DB_NAME environment variables must be set.")
if DB_NAME is None:
    raise Exception("MONGODB_DB_NAME environment variable is not set.")

mongo_client = AsyncIOMotorClient(MONGODB_URI)
db = mongo_client[DB_NAME]

get_db = lambda: db

get_checkpointer = lambda: AsyncMongoDBSaver(get_db())