import uuid
from datetime import datetime
from core.database import get_db

class AgentLogger:
    def __init__(self):
        self.db = get_db()
    async def log_execution(self, ticket_id, user, input_data, solution, execution_time=None, status="success", error_message=None):
        if self.db is None:
            raise Exception("Database connection not established for logging.")
        execution_id = str(uuid.uuid4())
        log_entry = {
            "execution_id": execution_id,
            "timestamp": datetime.now(),
            "ticket_id": ticket_id,
            "user": user,
            "input_data": input_data,
            "solution": solution,
            "execution_time": execution_time,
            "status": status,
            "error_message": error_message
        }
        await self.db.agent_executions.insert_one(log_entry)
        return execution_id

    async def log_error(self, user, path, method, error_message, traceback_data):
        if self.db is None:
            raise Exception("Database connection not established for logging.")
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
