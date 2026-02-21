"""
Módulo para la ingesta de documentos Knowledge Base.
Este módulo ingesta documentos markdown de la carpeta knowledge_base al vectorstore
para su posterior recuperación en el sistema RAG.
"""

import sys
import json
import re
import os
from pathlib import Path
from pydantic import BaseModel, Field
from .unified_logger import log_execution, log_error
from typing import List, Optional, Dict
from .third_party_clients import vector_store_instance as vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configuración del splitter de texto
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    add_start_index=True,
    separators=["\n\n", "\n", ". ", ", ", " ", ""]
)

# Categorías predefinidas basadas en los temas principales
KB_CATEGORIES = {
    "KB1": "Ciberseguridad y Cumplimiento",
    "KB2": "Colaboración y Herramientas Cloud", 
    "KB3": "DevOps e Infraestructura",
    "KB4": "Movilidad y MDM",
    "KB5": "Hardware y Oficina Inteligente",
    "KB6": "Privacidad y Gestión de Datos"
}

class KBDocument(BaseModel):
    """Modelo de un documento Knowledge Base."""
    fileId: str = Field(..., description="ID único del documento (ej. KB2001)")
    fileName: str = Field(..., description="Nombre del archivo original")
    content: str = Field(..., description="Contenido procesado del documento")
    category: str = Field(..., description="Categoría técnica extraída")
    tags: List[str] = Field(default_factory=list, description="Etiquetas clave")
    target_audience: str = Field(default="", description="Público objetivo")
    purpose: str = Field(default="", description="Propósito del documento")

def extract_kb_category(file_id: str, content: str = "") -> str:
    """
    Extrae categoría basada en file_id y contenido.
    
    Args:
        file_id (str): ID del documento (ej. KB2001)
        content (str): Contenido del documento para fallback
        
    Returns:
        str: Categoría correspondiente
    """
    # Primero por prefijo del ID (método principal)
    prefix = file_id[:3]  # KB1, KB2, etc.
    if prefix in KB_CATEGORIES:
        return KB_CATEGORIES[prefix]
    
    # Fallback por keywords en contenido
    content_lower = content.lower()
    keyword_mapping = {
        r"ciberseguridad|seguridad|phishing|mfa|2fa|autenticación|cumplimiento|gdpr|ley": "Ciberseguridad y Cumplimiento",
        r"onedrive|sharepoint|teams|slack|colaboración|cloud|azure|office365|google workspace": "Colaboración y Herramientas Cloud",
        r"docker|kubernetes|ci/cd|pipeline|despliegue|infraestructura|redes|devops|staging": "DevOps e Infraestructura",
        r"movilidad|mdm|jamf|intune|byod|dispositivo|móvil|tablet|enrolamiento": "Movilidad y MDM",
        r"hardware|dock|monitor|sensor|oficina inteligente|iot|cargador|periférico|ergonomía": "Hardware y Oficina Inteligente",
        r"privacidad|datos|dlp|auditoría|exportación|retención|legal hold|nóminas|erp": "Privacidad y Gestión de Datos"
    }
    
    for pattern, category in keyword_mapping.items():
        if re.search(pattern, content_lower):
            return category
    
    return "General"

def extract_metadata_from_content(content: str) -> Dict[str, str]:
    """
    Extraer metadatos adicionales del contenido markdown.
    
    Args:
        content (str): Contenido del documento
        
    Returns:
        Dict[str, str]: Metadatos extraídos
    """
    metadata = {}
    
    # Extraer público objetivo
    audience_patterns = [
        r"dirigido a[:\s]+(.+?)(?:\n|$)",
        r"para[:\s]+(.+?)(?:\n|$)",
        r"público[:\s]+(.+?)(?:\n|$)"
    ]
    
    for pattern in audience_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            metadata["target_audience"] = match.group(1).strip()
            break
    
    # Extraer propósito
    purpose_patterns = [
        r"propósito[:\s]+(.+?)(?:\n|$)",
        r"objetivo[:\s]+(.+?)(?:\n|$)",
        r"finalidad[:\s]+(.+?)(?:\n|$)"
    ]
    
    for pattern in purpose_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            metadata["purpose"] = match.group(1).strip()
            break
    
    # Extraer tags (palabras clave en mayúsculas o títulos)
    tag_patterns = [
        r"#([A-Z][A-Z\s]+[A-Z])",  # hashtags en mayúsculas
        r"##\s*([A-Z][A-Z\s]+[A-Z])",  # títulos H2 en mayúsculas
    ]
    
    tags = set()
    for pattern in tag_patterns:
        matches = re.findall(pattern, content)
        tags.update(matches)
    
    metadata["tags"] = list(tags)
    
    return metadata

def load_kb_documents_from_directory(directory_path: str, recursive: bool = False) -> List[KBDocument]:
    """
    Carga los documentos Knowledge Base desde un directorio.
    
    Args:
        directory_path (str): Ruta al directorio que contiene los documentos .md
        recursive (bool): Si es True, busca en subcarpetas también
        
    Returns:
        List[KBDocument]: Lista de objetos KBDocument cargados
    """
    try:
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"El directorio {directory_path} no existe")
        
        # Encontrar todos los archivos .md
        if recursive:
            md_files = list(directory.rglob("*.md"))
        else:
            md_files = list(directory.glob("*.md"))
        
        documents = []
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Extraer fileId del nombre del archivo
                file_id = md_file.stem
                
                # Extraer categoría
                category = extract_kb_category(file_id, content)
                
                # Extraer metadatos adicionales
                metadata = extract_metadata_from_content(content)
                
                # Crear objeto KBDocument
                doc = KBDocument(
                    fileId=file_id,
                    fileName=md_file.name,
                    content=content,
                    category=category,
                    target_audience=metadata.get("target_audience", ""),
                    purpose=metadata.get("purpose", ""),
                    tags=metadata.get("tags", [])
                )
                
                documents.append(doc)
                print(f"DEBUG: Documento {file_id} cargado exitosamente. Categoría: {category}")
                
            except Exception as e:
                sys.stderr.write(f"\n========== DEBUG: ERROR procesando archivo {md_file} ==========\n")
                sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
                sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
                sys.stderr.flush()
                continue
        
        return documents
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en load_kb_documents_from_directory ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return []

def ingest_kb_documents_to_vectorstore(documents: List[KBDocument]) -> None:
    """
    Ingresa los documentos Knowledge Base al vectorstore para su posterior recuperación.
    
    Args:
        documents (List[KBDocument]): Lista de objetos KBDocument a ingresar.
    """
    try:
        for i, doc in enumerate(documents):
            print(f"\nDEBUG: Procesando documento {i+1}/{len(documents)}: {doc.fileId}\n")
            # Log: start ingestion for this KB document
            try:
                log_execution(ticket_id=f"KB-INGEST-{doc.fileId}", user=doc.fileName, input_data={"fileId": doc.fileId}, solution="started", execution_time=0)
            except Exception:
                pass
            
            # Dividir contenido en chunks si es muy largo
            splits = [doc.content]
            if len(doc.content) > 1000:
                splits = text_splitter.split_text(doc.content)
            
            # Generar IDs deterministas basados en el fileId
            ids = [f"{doc.fileId}_{i}" for i in range(len(splits))]
            
            # Preparar metadatos para cada chunk
            metadatas = []
            for j, split in enumerate(splits):
                metadata = {
                    "fileId": doc.fileId,
                    "fileName": doc.fileName,
                    "category": doc.category,
                    "chunk_index": j,
                    "total_chunks": len(splits),
                    "target_audience": doc.target_audience,
                    "purpose": doc.purpose,
                    "tags": doc.tags
                }
                metadatas.append(metadata)
            
            vector_store.add_texts(
                texts=splits,
                metadatas=metadatas,
                ids=ids
            )
            print(f"DEBUG: Documento {doc.fileId} ingresado exitosamente ({len(splits)} chunks).\n")
            try:
                log_execution(ticket_id=f"KB-INGEST-{doc.fileId}", user=doc.fileName, input_data={"fileId": doc.fileId}, solution="success", execution_time=0)
            except Exception:
                pass
            
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en ingest_kb_documents_to_vectorstore ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        try:
            log_error(user="system", path="ingest_kb_documents_to_vectorstore", method="ingest", error_message=str(e), traceback_data="see stderr")
        except Exception:
            pass

def run_kb_ingestion_from(directory_path: str, recursive: bool = False) -> None:
    """
    Ejecuta el proceso de ingestión de documentos KB desde un directorio al vectorstore.
    
    Args:
        directory_path (str): Ruta al directorio que contiene los documentos .md
        recursive (bool): Si es True, busca en subcarpetas también
    """
    print(f"\n========== DEBUG: Iniciando ingestión masiva de Knowledge Base ==========\n")
    print(f"DEBUG: Directorio recibido: {directory_path}")
    print(f"DEBUG: Búsqueda recursiva: {recursive}")
    
    try:
        documents = load_kb_documents_from_directory(directory_path, recursive)
        print(f"\nDEBUG: Cargados {len(documents)} documentos KB.\n")
        
        if documents:
            # Agrupar por categoría para mostrar estadísticas
            categories = {}
            for doc in documents:
                if doc.category not in categories:
                    categories[doc.category] = 0
                categories[doc.category] += 1
            
            print("DEBUG: Distribución por categorías:")
            for category, count in categories.items():
                print(f"  - {category}: {count} documentos")
            
            ingest_kb_documents_to_vectorstore(documents)
        else:
            print("DEBUG: No se encontraron documentos KB para procesar.")
            
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en run_kb_ingestion_from ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()

def ingest_individual_kb_document(document: KBDocument) -> str:
    """
    Ingresa un documento KB individual al vectorstore.
    
    Args:
        document (KBDocument): Objeto KBDocument a ingresar.
        
    Returns:
        str: Mensaje de éxito o error.
    """
    try:
        # Dividir contenido en chunks si es muy largo
        splits = [document.content]
        if len(document.content) > 1000:
            splits = text_splitter.split_text(document.content)
        
        # Generar IDs deterministas basados en el fileId
        ids = [f"{document.fileId}_{i}" for i in range(len(splits))]
        
        # Preparar metadatos para cada chunk
        metadatas = []
        for j, split in enumerate(splits):
            metadata = {
                "fileId": document.fileId,
                "fileName": document.fileName,
                "category": document.category,
                "chunk_index": j,
                "total_chunks": len(splits),
                "target_audience": document.target_audience,
                "purpose": document.purpose,
                "tags": document.tags
            }
            metadatas.append(metadata)
        
        vector_store.add_texts(
            texts=splits,
            metadatas=metadatas,
            ids=ids
        )
        return f"Documento KB {document.fileId} ingresado exitosamente ({len(splits)} chunks)."
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR en ingest_individual_kb_document ==========\n")
        sys.stderr.write(f"DEBUG: Tipo de error: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Mensaje de error: {str(e)}\n")
        sys.stderr.flush()
        return f"ERROR al ingresar el documento KB {document.fileId}: {str(e)}"