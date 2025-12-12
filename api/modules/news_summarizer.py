"""
Módulo para la funcionalidad de resumen de noticias.
Este archivo contiene la estructura mock para que implementes la funcionalidad.
"""

from pydantic import BaseModel, field_validator, ConfigDict
from .third_party_clients import groq_llm_client as groq_llm_client
from groq import Groq
import os
import sys
import re
import json

groq_llm_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

NEWS_SUMMARIZER_MODEL_NAME = os.getenv("CHAT_MODEL_NAME")
NEWS_SUMMARIZER_SYSTEM_MESSAGE = """
    Eres un asistente que ayuda a resumir noticias de manera concisa y clara usando el idioma español.
    Debes proporcionar un resumen en 100 caracteres o menos y una lista de conceptos o tags clave que la noticia menciona.
    Tu respuesta tiene que ser SIEMPRE en formato JSON como el siguiente:
    {
        "resumen": <contenido del resumen que realizaste>,
        "puntos_clave": <array de puntos claves>
    }
"""

class NewsInput(BaseModel):
    """Modelo para la entrada de datos de una noticia."""
    title: str
    content: str
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    @field_validator('title', mode='before')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Valida y limpia el título - maneja comillas problemáticas."""
        if isinstance(v, str):
            sys.stderr.write(f"\nDEBUG validator title - Raw input: {v[:100]}\n")
            sys.stderr.flush()
            
            # Remover comillas dobles al inicio
            v = re.sub(r'^["\s]+', '', v)
            # Remover comillas dobles al final
            v = re.sub(r'["\s]+$', '', v)
            # Remover comillas internas duplicadas
            v = v.replace('""', '"')
            
            sys.stderr.write(f"DEBUG validator title - After clean: {v[:100]}\n")
            sys.stderr.flush()
        
        if not v or len(str(v).strip()) == 0:
            raise ValueError("El título no puede estar vacío")
        return str(v).strip()
    
    @field_validator('content', mode='before')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Valida y limpia el contenido."""
        if isinstance(v, str):
            sys.stderr.write(f"\nDEBUG validator content - Raw input length: {len(v)}\n")
            sys.stderr.flush()
            
            # Normalizar espacios y saltos de línea
            v = re.sub(r'\s+', ' ', v)
            
            sys.stderr.write(f"DEBUG validator content - After clean length: {len(v)}\n")
            sys.stderr.flush()
        
        if not v or len(str(v).strip()) == 0:
            raise ValueError("El contenido no puede estar vacío")
        return str(v).strip()


class NewsSummary(BaseModel):
    """Modelo para la respuesta del resumen de una noticia."""
    original_title: str
    summary: str
    summary_length: int
    key_points: list[str]


def summarize_news(news: NewsInput) -> NewsSummary:
    """
    Resume una noticia usando la estrategia configurada.
    
    Args:
        news (NewsInput): Objeto con título y contenido de la noticia
        
    Returns:
        NewsSummary: Objeto con el resumen y puntos clave
        
    Implementar:
        - Lógica de resumen (ej: con un modelo de IA, algoritmo de extracción, etc.)
        - Extracción de puntos clave
        - Validación de entrada
    """

    try:
        # Convertir el modelo Pydantic a diccionario
        raw_data = news.model_dump()
        
        # Actualizar el objeto con datos limpios
        news.title = raw_data['title']
        news.content = raw_data['content']
        
        if not news.title or len(news.title.strip()) == 0:
            raise ValueError("El título no puede estar vacío")
        if not news.content or len(news.content.strip()) == 0:
            raise ValueError("El contenido no puede estar vacío")

        message = groq_llm_client.chat.completions.create(
            model=NEWS_SUMMARIZER_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": NEWS_SUMMARIZER_SYSTEM_MESSAGE
                },
                {
                    "role": "user",
                    "content": f"Título: {news.title}\n\nContenido: {news.content}"
                }
            ],
            max_tokens=1024,
            temperature=0.7
        )

        choice = message.choices[0]
        
        summary_text = choice.message.content

        sys.stderr.write(f"\nDEBUG: Respuesta bruta de Groq:\n{summary_text}\n")
        sys.stderr.flush()
        
        # Parsear JSON de la respuesta
        summary_dict = None
        key_points = []
        
        if not summary_text or len(summary_text.strip()) == 0:
            summary_text = "Resumen no disponible"
        else: # Se extrae el JSON de la respuesta paara que pueda ser recibido fácilmente por el frontend
            try:
                # Buscar el bloque JSON en la respuesta
                json_match = re.search(r'\{.*\}', summary_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0) # Obtenemos el string que tendría el json
                    
                    summary_dict = json.loads(json_str) # Lo parseamos
                    
                    summary_text = summary_dict.get("resumen", summary_text)
                    if not summary_text: # A veces el LLM pone la key en comillas simples, así que cubrimos ese caso
                        summary_text = summary_dict.get("'resumen'", summary_text)
                    
                    key_points = summary_dict.get("puntos_clave") # Idem
                    if not key_points:
                        key_points = summary_dict.get("'puntos_clave'")
                else:
                    sys.stderr.write("DEBUG: No se encontró JSON en la respuesta\n")
                    sys.stderr.flush()
            except json.JSONDecodeError as je:
                sys.stderr.write(f"DEBUG: Error al parsear JSON: {str(je)}\n")
                sys.stderr.flush()
        
        sys.stderr.write(f"\nDEBUG: Creando respuesta de tipo NewsSummary...\n")
        sys.stderr.write(f"  - original_title: {news.title}\n")
        sys.stderr.write(f"  - summary: {summary_text[:100]}...\n")
        sys.stderr.write(f"  - summary_length: {len(summary_text.strip())}\n")
        sys.stderr.write(f"  - key_points: {key_points}\n")
        sys.stderr.flush()
        
        result = NewsSummary(
            original_title=news.title,
            summary=summary_text.strip(),
            summary_length=len(summary_text.strip()),
            key_points=key_points
        )
        
        return result
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en summarize_news ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        import traceback
        sys.stderr.write(f"DEBUG: Traceback completo:\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("========== DEBUG: ERROR finalizado ==========\n")
        sys.stderr.flush()
        
        try:
            return NewsSummary(
                original_title=news.title,
                summary=f"Error al procesar la noticia: {str(e)}",
                summary_length=len(f"Error al procesar la noticia: {str(e)}"),
                key_points=["Error en procesamiento"]
            )
        except Exception as e2:
            sys.stderr.write(f"DEBUG: ERROR al crear NewsSummary de error: {str(e2)}\n")
            sys.stderr.flush()
            raise


def validate_news_input(title: str, content: str) -> bool:
    """
    Valida que la entrada de noticia sea válida.
    
    Args:
        title (str): Título de la noticia
        content (str): Contenido de la noticia
        
    Returns:
        bool: True si es válida, False en caso contrario
        
    Implementar:
        - Validación de longitud mínima
        - Validación de formato
        - Validación de contenido
    """
    # if len(title) < 5 or len(content) < 20 or len(content) > 20000:
    #     return False
    return True
