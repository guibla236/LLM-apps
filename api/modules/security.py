import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Union

from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
# from passlib.context import CryptContext
from modules.database import get_database
from slowapi import Limiter
from slowapi.util import get_remote_address

# --- Configuration ---
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

# --- Security Schemes ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login", auto_error=False)
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)

import bcrypt

# --- Password Utilities ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    # bcrypt requirement: password cannot be longer than 72 bytes
    if len(password.encode('utf-8')) > 72:
        # We can truncate or hash it first with SHA256 if we want to support longer pws,
        # but for now, simple truncation or just rejecting it is safer.
        # Actually, let's just use the first 72 bytes as per standard practice if needed.
        password = password[:72]
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# --- Token Utilities ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_api_key():
    return secrets.token_urlsafe(32)

# --- Hybrid Dependency ---
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header)
):
    db = get_database()
    user = None

    # 1. Try JWT validation
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = await db.users.find_one({"username": username})
        except JWTError:
            pass # Invalid token, try API Key

    # 2. Try API Key validation if no user found yet
    if not user and api_key:
        user = await db.users.find_one({"api_key": api_key})

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Quota Management
    if user.get("daily_usage", 0) >= user.get("quota_limit", 100):
        raise HTTPException(status_code=403, detail="Daily quota exceeded")
    
    # 4. Increment usage
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$inc": {"daily_usage": 1}}
    )
    
    return user

# Backward compatibility for existing endpoint decorations
async def validate_api_key_and_quota(request: Request, user: dict = Depends(get_current_user)):
    return user

async def is_admin(user: dict = Depends(get_current_user)):
    """Dependency to verify if a user has administrative privileges."""
    db = get_database()
    is_admin_user = await db.admins.find_one({"username": user["username"]})
    if not is_admin_user:
        raise HTTPException(
            status_code=403,
            detail="No tienes privilegios administrativos para acceder a este recurso."
        )
    return user
