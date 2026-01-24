from fastapi import HTTPException
import httpx
from fastapi import Request
from core.config import get_env_var

API_MAIN_URL = get_env_var("API_BASE_URL")

async def get_authorized_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_MAIN_URL}/api/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code != 200:
                detail = "Unknown error during token validation"
                try:
                    detail = response.json().get("detail", detail)
                except:
                    detail = response.text
                raise HTTPException(status_code=response.status_code, detail=detail)
            return response.json()
        except httpx.RequestError as e:
            print(f"Error connecting to auth service at {API_MAIN_URL}: {str(e)}")
            raise HTTPException(status_code=401, detail="Could not connect to auth service")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Unexpected error in get_authorized_user: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Auth error: {str(e)}")