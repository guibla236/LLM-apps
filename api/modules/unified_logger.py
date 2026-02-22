import asyncio
from typing import Any, Optional

try:
    from agent_app.backend.core.logger import agent_logger
except Exception:
    # Fallback: agent_logger may not be importable in some test contexts
    agent_logger = None


async def _alog_execution(ticket_id: str, user: str, input_data: Any, solution: Any, execution_time: Optional[float] = None, status: str = "success", error_message: Optional[str] = None):
    if agent_logger is None:
        return None
    return await agent_logger.log_execution(ticket_id=ticket_id, user=user, input_data=input_data, solution=solution, execution_time=execution_time, status=status, error_message=error_message)


def log_execution(ticket_id: str, user: str, input_data: Any, solution: Any, execution_time: Optional[float] = None, status: str = "success", error_message: Optional[str] = None):
    """Sync-friendly wrapper to log an execution entry.

    If called inside a running event loop, the actual async logging is scheduled
    as a background task. Otherwise it runs to completion synchronously.
    """
    if agent_logger is None:
        return None

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop; run synchronously
        return asyncio.run(_alog_execution(ticket_id, user, input_data, solution, execution_time, status, error_message))
    else:
        # Schedule background task
        loop.create_task(_alog_execution(ticket_id, user, input_data, solution, execution_time, status, error_message))
        return None


async def _alog_error(user: str, path: str, method: str, error_message: str, traceback_data: str):
    if agent_logger is None:
        return None
    return await agent_logger.log_error(user=user, path=path, method=method, error_message=error_message, traceback_data=traceback_data)


def log_error(user: str, path: str, method: str, error_message: str, traceback_data: str):
    if agent_logger is None:
        return None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_alog_error(user, path, method, error_message, traceback_data))
    else:
        loop.create_task(_alog_error(user, path, method, error_message, traceback_data))
        return None
