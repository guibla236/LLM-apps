from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from modules.news_summarizer import NewsInput, NewsSummary, summarize_news
from modules.rag_tickets_ingestor import TicketModel, ingest_individual_ticket, run_ingestion_from
from modules.rag_tickets_retriever import retrieve_relevant_tickets, augment_similar_tickets
import sys
import shutil
import os

app = FastAPI()

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

# Endpoint que devuelve la página de bienvenida en HTML
@app.get("/")
async def get_welcome():
    """Devuelve la página de bienvenida."""
    return FileResponse("templates/index.html")

@app.post("/api/summarize_news", response_model=NewsSummary)
async def summarize_news_endpoint(news: NewsInput):
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

@app.post("/api/ingest_json_ticket", response_model=str)
async def ingest_json_ticket_endpoint(ticket: TicketModel):
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

@app.post("/api/get_similar_tickets", response_model=list[TicketModel])
async def get_similar_tickets_endpoint(ticket: TicketModel):
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

@app.post("/api/augment_ticket_information", response_model=dict)
async def augment_ticket_information_endpoint(ticket: TicketModel):
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