import requests
import time
import json

BASE_URL = "http://localhost:8000"
API_KEY = "tu_api_key_de_prueba"

# Intentar obtener una llave válida automáticamente si se usa el placeholder
if API_KEY == "tu_api_key_de_prueba":
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        async def fetch_key():
            client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
            db = client[os.getenv("MONGODB_DB_NAME", "ticket_system")]
            user = await db.users.find_one()
            client.close()
            return user["api_key"] if user else None
        
        found_key = asyncio.run(fetch_key())
        if found_key:
            API_KEY = found_key
            print(f"ℹ️ Usando API Key encontrada en DB: {API_KEY[:8]}...")
    except Exception:
        pass

def test_unauthorized():
    print("\n1. Probando acceso sin API Key...")
    response = requests.post(f"{BASE_URL}/api/get_similar_tickets", json={
        "ticketId": "TEST",
        "creationDate": "2024-01-01",
        "priority": "Low",
        "owner": "Tester",
        "description": "Prueba de seguridad",
        "impact": "Low",
        "actions": "None"
    })
    if response.status_code == 401:
        print("✅ Correcto: 401 Unauthorized recibido.")
    else:
        print(f"❌ Error: Se esperaba 401 pero se obtuvo {response.status_code}")

def test_rate_limiting():
    print("\n2. Probando Rate Limiting (IP)...")
    # Nota: esto requiere que la API Key sea válida para pasar el primer filtro
    headers = {"X-API-KEY": API_KEY}
    payload = {
        "ticketId": "TEST",
        "creationDate": "2024-01-01",
        "priority": "Low",
        "owner": "Tester",
        "description": "Prueba de rate limiting",
        "impact": "Low",
        "actions": "None"
    }
    
    for i in range(7): # El límite es 5/minuto en summarize_news para este test
        response = requests.post(f"{BASE_URL}/api/summarize_news", json={
            "title": "Noticia de prueba",
            "content": "Contenido suficientemente largo para la prueba de rate limit."
        }, headers=headers)
        
        if response.status_code == 429:
            print(f"✅ Correcto: 429 Too Many Requests recibido en el intento {i+1}.")
            return
        elif response.status_code == 200:
            print(f"Intento {i+1}: 200 OK")
        else:
            print(f"Intento {i+1}: Error inesperado {response.status_code}: {response.text}")
            break
    print("❌ Error: No se alcanzó el límite de tasa esperado.")

def test_payload_size():
    print("\n3. Probando límite de tamaño de payload...")
    headers = {"X-API-KEY": API_KEY}
    huge_description = "A" * 6000 # El límite es 5000
    payload = {
        "ticketId": "TEST",
        "creationDate": "2024-01-01",
        "priority": "Low",
        "owner": "Tester",
        "description": huge_description,
        "impact": "Low",
        "actions": "None"
    }
    response = requests.post(f"{BASE_URL}/api/ingest_json_ticket", json=payload, headers=headers)
    if response.status_code == 422: # Pydantic validation error code
        print("✅ Correcto: 422 Unprocessable Entity recibido (Payload demasiado grande).")
    else:
        print(f"❌ Error: Se esperaba 422 pero se obtuvo {response.status_code}")

if __name__ == "__main__":
    print("Iniciando pruebas de seguridad...")
    print("Asegúrate de que la API esté corriendo en localhost:8000")
    test_unauthorized()
    test_rate_limiting() # Descomentar cuando tengas una API Key válida en DB
    test_payload_size()
