from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from modules.news_summarizer import NewsInput, NewsSummary, summarize_news
from modules.rag_tickets_ingestor import TicketModel, ingest_individual_ticket, run_ingestion_from
from modules.rag_tickets_retriever import retrieve_relevant_tickets, augment_similar_tickets
from modules.database import connect_to_mongo, close_mongo_connection, get_database
from modules.security import get_current_user, limiter, get_password_hash, verify_password, create_access_token, generate_api_key, validate_api_key_and_quota
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field, EmailStr
from datetime import timedelta
import sys
import shutil
import os

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    sys.stderr.write("\n========== DEBUG: Llamada a /api/summarize_news ==========\n")
    sys.stderr.write(f"DEBUG: Datos recibidos: {news}\n")
    sys.stderr.flush()
    
    try:
        # Llamar a la función del módulo para resumir la noticia
        result = summarize_news(news)
        
        sys.stderr.write(f"DEBUG: Resultado de summarize_news: {result}\n")
        sys.stderr.write(f"DEBUG: Validando respuesta para response_model...\n")
        sys.stderr.flush()
        
        # Validar que el resultado cumple con NewsSummary
        if not isinstance(result, NewsSummary):
            sys.stderr.write(f"DEBUG: ERROR - El resultado no es NewsSummary, es {type(result)}\n")
            sys.stderr.flush()
        else:
            sys.stderr.write("DEBUG: OK - El resultado es NewsSummary\n")
            sys.stderr.flush()
            
        sys.stderr.write("========== DEBUG: Endpoint finalizado exitosamente ==========\n")
        sys.stderr.flush()
        return result
        
    except Exception as e:
        sys.stderr.write(f"\nDEBUG: ERROR en endpoint: {str(e)}\n")
        sys.stderr.flush()
        import traceback
        sys.stderr.write(f"DEBUG: Traceback:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("========== DEBUG: ERROR en endpoint ==========\n")
        sys.stderr.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el resumen: {str(e)}"
        )

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
    sys.stderr.write("\n========== DEBUG: Llamada a /api/ingest_json_ticket ==========\n")
    sys.stderr.write(f"DEBUG: Datos recibidos: {ticket}\n")
    sys.stderr.flush()
    
    try:
        # Llamar a la función para realizar la ingestión de tickets
        result = ingest_individual_ticket(ticket)
        return result
        
    except Exception as e:
        sys.stderr.write(f"\nDEBUG: ERROR en endpoint: {str(e)}\n")
        sys.stderr.flush()
        import traceback
        sys.stderr.write(f"DEBUG: Traceback:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("========== DEBUG: ERROR en ingest_json_ticket ==========\n")
        sys.stderr.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el resumen: {str(e)}"
        )

@app.post("/api/ingest_json_file")
async def ingest_json_file_endpoint(file: UploadFile = File(...)):
    """
    Endpoint POST para la ingestión masiva de tickets desde un archivo JSON.
    """
    sys.stderr.write(f"\n========== DEBUG: Llamada a /api/ingest_json_file ==========\n")
    sys.stderr.write(f"DEBUG: Archivo recibido: {file.filename}\n")
    sys.stderr.flush()

    temp_file_path = f"temp_{file.filename}"
    
    try:
        # Guardar el archivo temporalmente
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ejecutar la ingestión
        run_ingestion_from(temp_file_path)
        
        # Eliminar el archivo temporal
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        sys.stderr.write("DEBUG: Ingestión masiva completada exitosamente.\n")
        sys.stderr.flush()
        
        return {"message": f"Archivo {file.filename} procesado e ingestado exitosamente."}
        
    except Exception as e:
        sys.stderr.write(f"\nDEBUG: ERROR en endpoint de carga masiva: {str(e)}\n")
        sys.stderr.flush()
        # Intentar limpiar archivo en caso de error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )

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
    sys.stderr.write(f"\n========== DEBUG: Llamada a /api/get_similar_tickets ==========\n")
    sys.stderr.write(f"DEBUG: Datos recibidos: {ticket}\n")
    sys.stderr.flush()
    
    try:
        # Llamar a la función del módulo para obtener los tickets similares
        result = retrieve_relevant_tickets(ticket)
        
        sys.stderr.write(f"DEBUG: Resultado de retrieve_relevant_tickets: {result}\n")
        sys.stderr.write(f"DEBUG: Validando respuesta para response_model...\n")
        sys.stderr.flush()
        
        # Validar que el resultado cumple con list
        if not isinstance(result, list):
            sys.stderr.write(f"DEBUG: ERROR - El resultado no es list, es {type(result)}\n")
            sys.stderr.flush()
        else:
            sys.stderr.write("DEBUG: OK - El resultado es list\n")
            sys.stderr.flush()
            
        sys.stderr.write("========== DEBUG: Endpoint finalizado exitosamente ==========\n")
        sys.stderr.flush()
        return result
        
    except Exception as e:
        sys.stderr.write(f"\nDEBUG: ERROR en endpoint: {str(e)}\n")
        sys.stderr.flush()
        import traceback
        sys.stderr.write(f"DEBUG: Traceback:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("========== DEBUG: ERROR en endpoint ==========\n")
        sys.stderr.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el resumen: {str(e)}"
        )

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
    sys.stderr.write(f"\n========== DEBUG: Llamada a /api/augment_ticket_information ==========\n")
    sys.stderr.write(f"DEBUG: Datos recibidos: {ticket}\n")
    sys.stderr.flush()
    
    try:
        # Llamar a la función del módulo para obtener los tickets similares
        result = augment_similar_tickets(ticket)
        
        sys.stderr.write(f"DEBUG: Resultado de augment_similar_tickets: {result}\n")
        sys.stderr.write(f"DEBUG: Validando respuesta para response_model...\n")
        sys.stderr.flush()
        
        # Validar que el resultado cumple con dict
        if not isinstance(result, dict):
            sys.stderr.write(f"DEBUG: ERROR - El resultado no es dict, es {type(result)}\n")
            sys.stderr.flush()
        else:
            sys.stderr.write("DEBUG: OK - El resultado es dict\n")
            sys.stderr.flush()
            
        sys.stderr.write("========== DEBUG: Endpoint finalizado exitosamente ==========\n")
        sys.stderr.flush()
        return result
        
    except Exception as e:
        sys.stderr.write(f"\nDEBUG: ERROR en endpoint: {str(e)}\n")
        sys.stderr.flush()
        import traceback
        sys.stderr.write(f"DEBUG: Traceback:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("========== DEBUG: ERROR en endpoint ==========\n")
        sys.stderr.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el resumen: {str(e)}"
        )