from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from modules.news_summarizer import NewsInput, NewsSummary, summarize_news
from modules.rag_tickets_ingestor import TicketModel, ingest_individual_ticket, run_ingestion_from
from modules.rag_tickets_retriever import retrieve_relevant_tickets, augment_similar_tickets
from modules.database import connect_to_mongo, close_mongo_connection, get_database, is_feature_enabled
from modules.security import get_current_user, limiter, get_password_hash, verify_password, create_access_token, generate_api_key, validate_api_key_and_quota
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
async def register(user_in: UserRegister):
    db = get_database()
    # Check if user already exists
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
    
    await db.users.insert_one(new_user)
    return {"message": "User registered successfully", "api_key": new_user["api_key"]}

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
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "api_key": user["api_key"],
        "username": user["username"]
    }

# Endpoint que devuelve la página de bienvenida en HTML
@app.get("/")
async def get_welcome():
    """Devuelve la página de bienvenida."""
    return FileResponse("templates/index.html")

@app.get("/auth")
async def get_auth_page():
    return FileResponse("templates/auth.html")

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