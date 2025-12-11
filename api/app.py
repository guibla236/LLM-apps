from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from modules.news_summarizer import NewsInput, NewsSummary, summarize_news
from dotenv import load_dotenv
import sys

# load_dotenv()

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