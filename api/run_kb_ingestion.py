#!/usr/bin/env python3
"""
Script de ingesta masiva de Knowledge Base.
Este script ingesta todos los documentos KB al vectorstore para producción.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.rag_kb_ingestor import run_kb_ingestion_from

def main():
    """Función principal de ingesta."""
    print("=== Ingesta Masiva de Knowledge Base ===")
    
    # Ruta a la carpeta de knowledge base
    kb_path = os.path.join(os.path.dirname(__file__), "static", "mock", "knowledge_base")
    
    if not os.path.exists(kb_path):
        print(f"ERROR: La ruta {kb_path} no existe")
        return
    
    # Preguntar si se quiere búsqueda recursiva
    recursive = input("¿Buscar en subcarpetas recursivamente? (s/n): ").lower() in ['s', 'si', 'yes']
    
    print(f"\nIniciando ingesta desde: {kb_path}")
    print(f"Búsqueda recursiva: {recursive}")
    print("Presione Ctrl+C para cancelar\n")
    
    try:
        run_kb_ingestion_from(kb_path, recursive)
        print("\n✅ Ingesta completada exitosamente!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Ingesta cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR durante la ingesta: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()