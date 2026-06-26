from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import os

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
VALID_API_KEY = os.getenv("API_KEY", "pulseiq-dev-key-change-in-production")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if not api_key or api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Pass X-API-Key header."
        )
    return api_key
