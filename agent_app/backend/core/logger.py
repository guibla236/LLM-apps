import uuid
import asyncio
import threading
from datetime import datetime
from core.database import get_db
from typing import Literal

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

# helpers for fire-and-forget logging

def _run_coro_background(coro):
    """Schedule a coroutine without waiting for it to finish.

    If an event loop is already running on the current thread, the coroutine
    is scheduled on that loop via ``create_task``. Otherwise a new loop is
    spun up inside a daemon thread so the caller is not blocked.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        loop.create_task(coro)
    else:
        # run in new thread so we don't block synchronous callers
        threading.Thread(target=lambda: asyncio.run(coro), daemon=True).start()


def log_background(kind: Literal['error', 'execution'], *args, **kwargs):
    """Public helper usable from synchronous code.

    Calls the appropriate :class:`AgentLogger` coroutine in a background task
    so the caller does not need to ``await`` anything. ``kind`` must be
    either ``'error'`` or ``'execution'``; remaining positional/keyword
    arguments are forwarded to ``log_error`` or ``log_execution``.
    """
    if kind == 'error':
        _run_coro_background(agent_logger.log_error(*args, **kwargs))
    elif kind == 'execution':
        _run_coro_background(agent_logger.log_execution(*args, **kwargs))
    else:
        raise ValueError(f"unexpected kind {kind!r}")
