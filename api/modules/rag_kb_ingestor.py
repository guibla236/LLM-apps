"""
Module for ingesting Knowledge Base documents.
This module ingests markdown documents from the knowledge_base folder to the vectorstore
for later retrieval in the RAG system.
"""

import sys
import re
from pathlib import Path
from pydantic import BaseModel, Field
from .unified_logger import log_execution, log_error
from typing import List, Dict
from .third_party_clients import kb_vector_store_instance as kb_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Splitter configuration for KBs documents.
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    add_start_index=True,
    separators=["\n\n", "\n", ". ", ", ", " ", ""]
)

# Predefined categories based on main IT support topics (bilingual: English primary, Spanish fallback).
KB_CATEGORIES = {
    "KB1": "Cybersecurity & Compliance",
    "KB2": "Collaboration & Cloud Tools",
    "KB3": "DevOps & Infrastructure",
    "KB4": "Mobility & MDM",
    "KB5": "Hardware & Smart Office",
    "KB6": "Privacy & Data Management"
}

class KBDocument(BaseModel):
    """Model for a Knowledge Base Document."""
    fileId: str = Field(..., description="Unique document ID (e.g. KB2001)")
    fileName: str = Field(..., description="Original file name")
    content: str = Field(..., description="Processed document content")
    category: str = Field(..., description="Extracted technical category")
    tags: List[str] = Field(default_factory=list, description="Key tags")
    target_audience: str = Field(default="", description="Target audience")
    purpose: str = Field(default="", description="Document purpose")

def extract_kb_category(file_id: str, content: str = "") -> str:
    """
    Extracts category based on file_id and content.
    
    Args:
        file_id (str): Document ID (e.g. KB2001)
        content (str): Document content for fallback
        
    Returns:
        str: Corresponding category
    """
    # First by ID prefix (main method)
    prefix = file_id[:3]  # KB1, KB2, etc.
    if prefix in KB_CATEGORIES:
        return KB_CATEGORIES[prefix]
    
    # Fallback by keywords in content (bilingual: English + Spanish)
    content_lower = content.lower()
    keyword_mapping = {
        r"cybersecurity|security|phishing|mfa|2fa|authentication|compliance|gdpr|ciberseguridad|seguridad|autenticación|cumplimiento|ley": "Cybersecurity & Compliance",
        r"onedrive|sharepoint|teams|slack|collaboration|cloud|azure|office365|google workspace|colaboración|cloud": "Collaboration & Cloud Tools",
        r"docker|kubernetes|ci/cd|pipeline|deployment|infrastructure|devops|staging|despliegue|infraestructura|redes": "DevOps & Infrastructure",
        r"mobility|mdm|jamf|intune|byod|device|mobile|tablet|enrollment|movilidad|dispositivo|móvil|enrolamiento": "Mobility & MDM",
        r"hardware|dock|monitor|sensor|iot|charger|peripheral|ergonomics|oficina inteligente|periférico|ergonomía|cargador": "Hardware & Smart Office",
        r"privacy|data|dlp|audit|export|retention|legal hold|payroll|erp|privacidad|datos|auditoría|exportación|retención|nóminas": "Privacy & Data Management"
    }
    
    for pattern, category in keyword_mapping.items():
        if re.search(pattern, content_lower):
            return category
    
    return "General"

def extract_metadata_from_content(content: str) -> Dict[str, str]:
    """
    Extract additional metadata from markdown content.
    
    Args:
        content (str): Document content
        
    Returns:
        Dict[str, str]: Extracted metadata
    """
    metadata = {}
    
    # Extract target audience (bilingual: English + Spanish)
    audience_patterns = [
        r"target audience[:\s]+(.+?)(?:\n|$)",
        r"intended for[:\s]+(.+?)(?:\n|$)",
        r"audience[:\s]+(.+?)(?:\n|$)",
        r"dirigido a[:\s]+(.+?)(?:\n|$)",
        r"para[:\s]+(.+?)(?:\n|$)",
        r"público[:\s]+(.+?)(?:\n|$)"
    ]
    
    for pattern in audience_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            metadata["target_audience"] = match.group(1).strip()
            break
    
    # Extract purpose (bilingual: English + Spanish)
    purpose_patterns = [
        r"purpose[:\s]+(.+?)(?:\n|$)",
        r"objective[:\s]+(.+?)(?:\n|$)",
        r"goal[:\s]+(.+?)(?:\n|$)",
        r"propósito[:\s]+(.+?)(?:\n|$)",
        r"objetivo[:\s]+(.+?)(?:\n|$)",
        r"finalidad[:\s]+(.+?)(?:\n|$)"
    ]
    
    for pattern in purpose_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            metadata["purpose"] = match.group(1).strip()
            break
    
    # Extracts tags (keywords in uppercase or titles)
    tag_patterns = [
        r"#([A-Z][A-Z\s]+[A-Z])",  # hashtags in uppercase
        r"##\s*([A-Z][A-Z\s]+[A-Z])",  # H2 Headers in uppercase
    ]
    
    tags = set()
    for pattern in tag_patterns:
        matches = re.findall(pattern, content)
        tags.update(matches)
    
    metadata["tags"] = list(tags)
    
    return metadata

def load_kb_documents_from_directory(directory_path: str, recursive: bool = False) -> List[KBDocument]:
    """
    Loads Knowledge Base documents from a directory.
    
    Args:
        directory_path (str): Path to the directory containing .md documents
        recursive (bool): If True, searches in subdirectories as well
        
    Returns:
        List[KBDocument]: List of loaded KBDocument objects
    """
    try:
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"The path directory {directory_path} does not exist")
        
        # Find all .md files.
        if recursive:
            md_files = list(directory.rglob("*.md"))
        else:
            md_files = list(directory.glob("*.md"))
        
        documents = []
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Extract fileId from file name
                file_id = md_file.stem
                
                # Extract category
                category = extract_kb_category(file_id, content)
                
                # Extract additional metadata
                metadata = extract_metadata_from_content(content)
                
                # Create KBDocument object
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
                print(f"DEBUG: Document {file_id} loaded successfully. Category: {category}")
                
            except Exception as e:
                sys.stderr.write(f"\n========== DEBUG: ERROR processing file {md_file} ==========\n")
                sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
                sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
                sys.stderr.flush()
                continue
        
        return documents
        
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in load_kb_documents_from_directory ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        return []

def ingest_kb_documents_to_vectorstore(documents: List[KBDocument]) -> None:
    """
    Ingests Knowledge Base documents to the vectorstore for later retrieval.
    
    Args:
        documents (List[KBDocument]): List of KBDocument objects to ingest.
    """
    try:
        for i, doc in enumerate(documents):
            print(f"\nDEBUG: Processing document {i+1}/{len(documents)}: {doc.fileId}\n")
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
            
            kb_vector_store.add_texts(
                texts=splits,
                metadatas=metadatas,
                ids=ids
            )
            print(f"DEBUG: Document {doc.fileId} ingested successfully ({len(splits)} chunks).\n")
            try:
                log_execution(ticket_id=f"KB-INGEST-{doc.fileId}", user=doc.fileName, input_data={"fileId": doc.fileId}, solution="success", execution_time=0)
            except Exception:
                pass
            
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in ingest_kb_documents_to_vectorstore ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        try:
            log_error(user="system", path="ingest_kb_documents_to_vectorstore", method="ingest", error_message=str(e), traceback_data="see stderr")
        except Exception:
            pass

def run_kb_ingestion_from(directory_path: str, recursive: bool = False) -> None:
    """
    Runs the process of ingesting Knowledge Base documents from a directory to the vectorstore.
    
    Args:
        directory_path (str): Path to the directory containing .md documents
        recursive (bool): If True, searches subdirectories as well
    """
    print(f"\n========== DEBUG: Starting bulk Knowledge Base ingestion ==========\n")
    print(f"DEBUG: Directory received: {directory_path}")
    print(f"DEBUG: Recursive search: {recursive}")
    
    try:
        documents = load_kb_documents_from_directory(directory_path, recursive)
        print(f"\nDEBUG: Loaded {len(documents)} KB documents.\n")
        
        if documents:
            # Agrupar por categoría para mostrar estadísticas
            categories = {}
            for doc in documents:
                if doc.category not in categories:
                    categories[doc.category] = 0
                categories[doc.category] += 1
            
            print("DEBUG: Category distribution:")
            for category, count in categories.items():
                print(f"  - {category}: {count} documents")
            
            ingest_kb_documents_to_vectorstore(documents)
        else:
            print("DEBUG: No KB documents found to process.")
            
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in run_kb_ingestion_from ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()

def ingest_individual_kb_document(document: KBDocument) -> str:
    """
    Ingests an individual KB document to the vectorstore.
    
    Args:
        document (KBDocument): KBDocument object to ingest.
        
    Returns:
        str: Success or error message.
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
        
        kb_vector_store.add_texts(
            texts=splits,
            metadatas=metadatas,
            ids=ids
        )
        return f"Knowledge Base document {document.fileId} ingested successfully ({len(splits)} chunks)."
    except Exception as e:
        sys.stderr.write(f"\n========== DEBUG: ERROR in ingest_individual_kb_document ==========\n")
        sys.stderr.write(f"DEBUG: Error type: {type(e).__name__}\n")
        sys.stderr.write(f"DEBUG: Error message: {str(e)}\n")
        sys.stderr.flush()
        return f"ERROR ingesting Knowledge Base document {document.fileId}: {str(e)}"