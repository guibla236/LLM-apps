import os
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "ticket_system")

class AgentLogger:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        if self.db is None:
            self.client = AsyncIOMotorClient(MONGODB_URI)
            self.db = self.client[MONGODB_DB_NAME]
            
    async def log_execution(self, ticket_id, user, input_data, solution, status="success", error_message=None):
        await self.connect()
        execution_id = str(uuid.uuid4())
        log_entry = {
            "execution_id": execution_id,
            "timestamp": datetime.utcnow(),
            "ticket_id": ticket_id,
            "user": user,
            "input_data": input_data,
            "solution": solution,
            "status": status,
            "error_message": error_message
        }
        await self.db.agent_executions.insert_one(log_entry)
        return execution_id

    async def log_error(self, user, path, method, error_message, traceback_data):
        await self.connect()
        error_id = str(uuid.uuid4())
        error_log = {
            "error_id": error_id,
            "timestamp": datetime.utcnow(),
            "user": user,
            "path": path,
            "method": method,
            "traceback": traceback_data,
            "error_message": error_message
        }
        await self.db.error_logs.insert_one(error_log)
        return error_id

agent_logger = AgentLogger()
