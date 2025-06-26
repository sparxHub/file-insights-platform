"""Security utilities for JWT token management and secret handling"""

import os
import secrets
from functools import lru_cache
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class SecretManager:
    """Handles secure secret management for JWT and other sensitive data"""
    
    @staticmethod
    def generate_jwt_secret() -> str:
        """Generate a cryptographically secure JWT secret"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def get_jwt_secret() -> str:
        """
        Get JWT secret from environment or generate secure default
        
        Priority:
        1. JWT_SECRET_KEY environment variable
        2. Generated secure secret (with warning)
        """
        # Check environment variable first
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        
        if jwt_secret and jwt_secret != "CHANGE_ME":
            return jwt_secret
        
        # Generate secure secret if not provided or default used
        generated_secret = SecretManager.generate_jwt_secret()
        
        if jwt_secret == "CHANGE_ME":
            logger.warning(
                "JWT_SECRET_KEY is set to default 'CHANGE_ME'. "
                "Using generated secret for this session. "
                "Set JWT_SECRET_KEY environment variable for production."
            )
        else:
            logger.warning(
                "JWT_SECRET_KEY not found in environment. "
                "Using generated secret for this session. "
                "Set JWT_SECRET_KEY environment variable for production."
            )
        
        return generated_secret
    
    @staticmethod
    def validate_secret_strength(secret: str) -> bool:
        """Validate JWT secret meets security requirements"""
        if len(secret) < 32:
            logger.error("JWT secret too short. Must be at least 32 characters.")
            return False
        
        if secret in ["CHANGE_ME", "secret", "password", "123456"]:
            logger.error("JWT secret is a common weak value. Use a cryptographically secure secret.")
            return False
        
        return True


@lru_cache(maxsize=1)
def get_secure_jwt_secret() -> str:
    """Get cached secure JWT secret"""
    secret = SecretManager.get_jwt_secret()
    
    if not SecretManager.validate_secret_strength(secret):
        logger.error("JWT secret validation failed. Application may be insecure.")
    
    return secret
