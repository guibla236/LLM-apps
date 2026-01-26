import asyncio
import bcrypt
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def create_user():
    load_dotenv()
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))
    db = client['ticket_system']
    
    username = "testuser"
    password = "testpassword"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "username": username,
        "email": "test@example.com",
        "hashed_password": hashed,
        "api_key": "test_key",
        "quota_limit": 1000,
        "daily_usage": 0,
        "is_active": True
    }
    
    await db['users'].update_one({"username": username}, {"$set": user_doc}, upsert=True)
    print(f"User {username} created/updated successfully.")

if __name__ == "__main__":
    asyncio.run(create_user())
