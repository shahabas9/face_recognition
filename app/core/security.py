"""
Security utilities for API authentication
"""
from fastapi import Header, HTTPException, status
from typing import Optional
from config.settings import API_KEY, REQUIRE_AUTH


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from header
    Header: X-API-Key: testkey123
    """
    if not REQUIRE_AUTH:
        return "anonymous"
    
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return x_api_key
