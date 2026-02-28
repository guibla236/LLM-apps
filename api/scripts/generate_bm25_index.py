import json
import sys
from pathlib import Path

# Agregar el directorio principal al path para poder importar los módulos
sys.path.append(str(Path(__file__).parent.parent))

from modules.rag_tickets_ingestor import load_support_tickets
from modules.rag_kb_ingestor import load_kb_documents_from_directory

def generate_index():
    base_path = Path(__file__).parent.parent
    tickets_dir = base_path / "static/mock/tickets"
    kb_dir = base_path / "static/mock/knowledge_base"
    output_file = base_path / "static/bm25_index.json"

    print(f"Cargando tickets desde {tickets_dir}...")
    all_tickets = []
    for json_file in tickets_dir.glob("*.json"):
        tickets = load_support_tickets(str(json_file))
        all_tickets.extend(tickets)
    
    print(f"Total tickets cargados: {len(all_tickets)}")

    print(f"Cargando documentos KB desde {kb_dir}...")
    kb_docs = load_kb_documents_from_directory(str(kb_dir))
    print(f"Total documentos KB cargados: {len(kb_docs)}")

    # Preparar para guardado (convertir Pydantic a dict)
    data = {
        "tickets": [t.model_dump() for t in all_tickets],
        "kb": [
            {
                "fileId": d.fileId,
                "fileName": d.fileName,
                "content": d.content,
                "category": d.category,
                "target_audience": d.target_audience,
                "purpose": d.purpose,
                "tags": d.tags
            } for d in kb_docs
        ]
    }

    print(f"Guardando índice en {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("¡Índice generado con éxito!")

if __name__ == "__main__":
    generate_index()
