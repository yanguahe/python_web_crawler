"""
HTTP Basic Authentication for the application.

This module provides HTTP Basic Auth to protect the web application
from unauthorized access when deployed on a public server.
"""
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import settings

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Verify HTTP Basic Auth credentials.
    
    Args:
        credentials: HTTP Basic credentials from the request
        
    Returns:
        Username if credentials are valid
        
    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid
    """
    if not settings.auth_enabled:
        return "anonymous"
    
    # Use secrets.compare_digest to prevent timing attacks
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.auth_username.encode("utf-8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.auth_password.encode("utf-8")
    )
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

