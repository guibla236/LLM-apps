from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from modules.news_summarizer import NewsInput, NewsSummary, summarize_news
from modules.rag_tickets_ingestor import TicketModel, ingest_individual_ticket, run_ingestion_from
from modules.rag_tickets_retriever import retrieve_relevant_tickets, augment_similar_tickets
from modules.database import connect_to_mongo, close_mongo_connection, get_database, is_feature_enabled
from modules.security import get_current_user, limiter, get_password_hash, verify_password, create_access_token, generate_api_key, validate_api_key_and_quota, is_admin
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta
import sys
import shutil
import os
import uuid
import traceback

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    db = get_database()
    
    # Try to get user info if possible (might fail if auth fails)
    user_info = "anonymous"
    try:
        # We don't want to trigger Depends here, just try to peek at the header/token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            from jose import jwt
            from modules.security import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_info = payload.get("sub", "anonymous")
        else:
            api_key = request.headers.get("X-API-KEY")
            if api_key:
                user_info = f"api_key:{api_key[:8]}..."
    except Exception:
        pass

    error_log = {
        "error_id": error_id,
        "timestamp": datetime.utcnow(),
        "user": user_info,
        "path": request.url.path,
        "method": request.method,
        "traceback": traceback.format_exc(),
        "error_message": str(exc)
    }
    
    # Log to MongoDB if connected
    if db is not None:
        try:
            await db.error_logs.insert_one(error_log)
        except Exception as e:
            sys.stderr.write(f"CRITICAL: Failed to log error to MongoDB: {str(e)}\n")
    
    # Also log to stderr for safety
    sys.stderr.write(f"\n[ERROR_ID: {error_id}] Global exception caught:\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.flush()

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ha ocurrido un error interno del servidor.",
            "error_id": error_id
        }
    )

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Configurar CORS para permitir solicitudes desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos (CSS, JS, imágenes, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Auth Models ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)

class UserLogin(BaseModel):
    username: str
    password: str

# --- Auth Endpoints ---
@app.post("/api/register")
async def register(user_in: UserRegister, request: Request):
    db = get_database()
    ip_address = request.client.host
    
    # 1. IP Check (Limit: 3 registrations per IP per 24h)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    reg_count = await db.registrations.count_documents({
        "ip": ip_address,
        "timestamp": {"$gte": one_day_ago}
    })
    
    if reg_count >= 3:
        raise HTTPException(
            status_code=429, 
            detail="Has superado el límite de registros permitidos desde esta conexión por hoy."
        )
    
    # 2. Check if user already exists (Atomic check handled by unique index too)
    if await db.users.find_one({"$or": [{"username": user_in.username}, {"email": user_in.email}]}):
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    new_user = {
        "username": user_in.username,
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
        "api_key": generate_api_key(),
        "quota_limit": 100,
        "daily_usage": 0,
        "is_active": True
    }
    
    try:
        await db.users.insert_one(new_user)
        # Log successful registration
        await db.registrations.insert_one({
            "ip": ip_address,
            "username": user_in.username,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        # Check if it's a duplicate key error (if race condition occurred)
        if "duplicate key error" in str(e):
             raise HTTPException(status_code=400, detail="Username or email already registered")
        raise e

    return {"message": "User registered successfully", "api_key": new_user["api_key"]}

@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Validates token and returns current user info."""
    return {
        "username": user["username"],
        "email": user["email"],
        "quota_limit": user["quota_limit"],
        "daily_usage": user["daily_usage"]
    }

@app.post("/api/login")
async def login(user_in: UserLogin):
    db = get_database()
    user = await db.users.find_one({"username": user_in.username})
    
    if not user or not verify_password(user_in.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    # Verificar si es admin
    admin_record = await db.admins.find_one({"username": user["username"]})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "api_key": user["api_key"],
        "username": user["username"],
        "is_admin": admin_record is not None
    }

# Endpoint que devuelve la página de bienvenida en HTML
@app.get("/")
async def get_welcome():
    """Devuelve la página de bienvenida."""
    return FileResponse("templates/index.html")

@app.get("/auth")
async def get_auth_page():
    return FileResponse("templates/auth.html")

@app.get("/admin")
async def get_admin_dashboard():
    """Serves the administrative dashboard."""
    return FileResponse("templates/dashboard.html")

# --- Admin API Endpoints ---

@app.get("/api/admin/flags", dependencies=[Depends(is_admin)])
async def list_flags():
    db = get_database()
    flags = await db.feature_flags.find().to_list(100)
    for f in flags: f["_id"] = str(f["_id"])
    return flags

@app.post("/api/admin/flags/{name}", dependencies=[Depends(is_admin)])
async def update_flag(name: str, data: dict):
    db = get_database()
    await db.feature_flags.update_one(
        {"name": name},
        {"$set": {"enabled": data.get("enabled", False)}},
        upsert=True
    )
    return {"status": "ok"}

@app.get("/api/flags/{name}")
async def get_flag_status(name: str):
    """Public endpoint to check if a feature flag is enabled."""
    from modules.database import is_feature_enabled
    enabled = await is_feature_enabled(name)
    return {"name": name, "enabled": enabled}

@app.get("/api/admin/users", dependencies=[Depends(is_admin)])
async def list_users():
    db = get_database()
    users = await db.users.find({}, {"hashed_password": 0}).to_list(100)
    for u in users: u["_id"] = str(u["_id"])
    return users

@app.post("/api/admin/users/{username}/quota", dependencies=[Depends(is_admin)])
async def update_user_quota(username: str, data: dict):
    db = get_database()
    new_limit = data.get("quota_limit")
    if new_limit is None:
        raise HTTPException(status_code=400, detail="quota_limit is required")
    
    await db.users.update_one(
        {"username": username},
        {"$set": {"quota_limit": new_limit}}
    )
    return {"status": "ok"}

@app.get("/api/admin/logs", dependencies=[Depends(is_admin)])
async def list_logs():
    db = get_database()
    logs = await db.error_logs.find().sort("timestamp", -1).to_list(50)
    for l in logs: l["_id"] = str(l["_id"])
    return logs

@app.get("/api/admin/logs/{error_id}", dependencies=[Depends(is_admin)])
async def get_log_detail(error_id: str):
    db = get_database()
    log = await db.error_logs.find_one({"error_id": error_id})
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    log["_id"] = str(log["_id"])
    return log

@app.get("/api/admin/ips", dependencies=[Depends(is_admin)])
async def list_ip_usage():
    db = get_database()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    usage = await db.ip_usage.find({"date": today}).sort("count", -1).to_list(100)
    for i in usage: i["_id"] = str(i["_id"])
    return usage

@app.get("/api/admin/registrations", dependencies=[Depends(is_admin)])
async def list_registrations():
    db = get_database()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    regs = await db.registrations.find({"timestamp": {"$gte": today}}).sort("timestamp", -1).to_list(100)
    for r in regs: r["_id"] = str(r["_id"])
    return regs
@app.post("/api/summarize_news", response_model=NewsSummary, dependencies=[Depends(validate_api_key_and_quota)])
@limiter.limit("5/minute")
async def summarize_news_endpoint(news: NewsInput, request: Request):
    """
    Endpoint POST que devuelve el resumen de una noticia determinada.
    
    **Parámetros requeridos:**
    - `title` (string): Título de la noticia
    - `content` (string): Contenido completo de la noticia
    
    **Ejemplo de body JSON:**
    ```json
    {
      "title": "Título de la noticia aquí",
      "content": "Contenido completo de la noticia con suficientes caracteres..."
    }
    ```
    """
    return await summarize_news(news)

@app.post("/api/ingest_json_ticket", response_model=str, dependencies=[Depends(validate_api_key_and_quota)])
@limiter.limit("10/minute")
async def ingest_json_ticket_endpoint(ticket: TicketModel, request: Request):
    """
    Endpoint POST que realiza la ingestión de un documento JSON determinado.
    
    **Parámetros requeridos:**
    - `ticket` (TicketModel): Objeto TicketModel a ingresar.
    
    **Ejemplo de body JSON:**
    ```json
    {
      "ticketId": "12345",
      "title": "Problema con la impresora",
      "priority": "HIGH",
      "owner": "Juan Pérez - IT",
      "description": "La impresora no responde y muestra un error de conexión.",
      "impact": "Alto",
      "actions": "Reinicié la impresora y verifiqué los cables."
    }
    ```
    """
    if await is_feature_enabled("block_ticket_ingestion"):
        raise HTTPException(
            status_code=403, 
            detail="La ingesta de tickets ha sido desactivada temporalmente por el administrador."
        )
    
    return ingest_individual_ticket(ticket)

@app.post("/api/ingest_json_file", dependencies=[Depends(validate_api_key_and_quota)])
async def ingest_json_file_endpoint(file: UploadFile = File(...), request: Request = None):
    """
    Endpoint POST para la ingestión masiva de tickets desde un archivo JSON.
    """
    if await is_feature_enabled("block_ticket_ingestion"):
        raise HTTPException(
            status_code=403, 
            detail="La ingesta de tickets ha sido desactivada temporalmente por el administrador."
        )
        
    temp_file_path = f"temp_{file.filename}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        run_ingestion_from(temp_file_path)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    return {"message": f"Archivo {file.filename} procesado e ingestado exitosamente."}

@app.post("/api/get_similar_tickets", response_model=list[TicketModel], dependencies=[Depends(validate_api_key_and_quota)])
@limiter.limit("20/minute")
async def get_similar_tickets_endpoint(ticket: TicketModel, request: Request):
    """
    Endpoint POST que devuelve los tickets similares a un ticket determinado que se recibe como parámetro.
    
    **Parámetros requeridos:**
    - `ticket` (TicketModel): Objeto TicketModel a ingresar.
    
    **Ejemplo de body JSON:**
    ```json
    {
      "ticketId": "12345",
      "title": "Problema con la impresora",
      "priority": "HIGH",
      "owner": "Juan Pérez - IT",
      "description": "La impresora no responde y muestra un error de conexión.",
      "impact": "Alto",
      "actions": "Reinicié la impresora y verifiqué los cables."
    }
    ```
    """
    return await retrieve_relevant_tickets(ticket)

@app.post("/api/augment_ticket_information", response_model=dict, dependencies=[Depends(validate_api_key_and_quota)])
@limiter.limit("10/minute")
async def augment_ticket_information_endpoint(ticket: TicketModel, request: Request):
    """
    Endpoint POST que aumenta la información de un ticket determinado que se recibe como parámetro.
    
    **Parámetros requeridos:**
    - `ticket` (TicketModel): Objeto TicketModel a ingresar.
    
    **Ejemplo de body JSON:**
    ```json
    {
      "ticketId": "12345",
      "title": "Problema con la impresora",
      "priority": "HIGH",
      "owner": "Juan Pérez - IT",
      "description": "La impresora no responde y muestra un error de conexión.",
      "impact": "Alto",
      "actions": "Reinicié la impresora y verifiqué los cables."
    }
    ```
    """
    return await augment_similar_tickets(ticket)