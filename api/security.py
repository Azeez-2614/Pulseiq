from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
import os

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
VALID_API_KEY = os.getenv("API_KEY", "pulseiq-dev-key-change-in-production")

limiter = Limiter(key_func=get_remote_address)

ALLOWED_SYMBOLS = {"AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"}

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    if not api_key or api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Include X-API-Key header."
        )
    return api_key

def validate_symbol(symbol: str) -> str:
    clean = symbol.upper().strip()[:10]
    if clean not in ALLOWED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol '{clean}' not in watchlist. Valid: {sorted(ALLOWED_SYMBOLS)}"
        )
    return clean
