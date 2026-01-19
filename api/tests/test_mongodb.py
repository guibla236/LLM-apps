import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Intentar cargar .env desde el directorio actual o el superior
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("api/.env"):
    load_dotenv("api/.env")
else:
    # Ruta absoluta para mayor seguridad
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir, "api", ".env"))

async def test_connection():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")
    
    print(f"--- Intentando conectar a: {db_name} ---")
    if not uri or "your_mongodb_atlas_uri" in uri:
        print("ERROR: La URI de MongoDB no está configurada correctamente en api/.env")
        return

    try:
        client = AsyncIOMotorClient(uri)
        # El comando 'ping' es la forma estándar de verificar la conexión
        await client.admin.command('ping')
        print("✅ ¡Éxito! Conexión establecida con MongoDB Atlas.")
        
        db = client[db_name]
        collections = await db.list_collection_names()
        print(f"Colecciones disponibles en '{db_name}': {collections}")
        
    except Exception as e:
        print(f"❌ Error al conectar a MongoDB: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
