from functools import wraps
from fastapi import HTTPException

def handle_value_error(func):
    """
    Decorator to handle ValueError exceptions and return a 400 Bad Request response with the error message.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return wrapper