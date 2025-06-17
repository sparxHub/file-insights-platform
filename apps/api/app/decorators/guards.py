import logging
from abc import ABC, abstractmethod
from functools import wraps
from inspect import signature
from typing import Any, Callable, Dict, List, Optional, Type, Union

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger(__name__)

# -----------------------------------------------------------
#  Base guard classes
# -----------------------------------------------------------
class BaseGuard(ABC):
    """Base class for all guards"""
    
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    async def can_activate(self, request: Request, **kwargs) -> bool:
        """
        Check if the guard allows activation
        Returns True if access is granted, False otherwise
        Can raise HTTPException for immediate rejection with custom error
        """
        pass
    
    async def handle_failure(self, request: Request, **kwargs) -> HTTPException:
        """
        Handle guard failure - override for custom error responses
        """
        return HTTPException(
            status_code=403,
            detail=f"Access denied by {self.name}"
        )

# -----------------------------------------------------------
#  Auth guard
# -----------------------------------------------------------
class AuthGuard(BaseGuard):
    """Basic authentication guard"""
    
    def __init__(self, required_role: Optional[str] = None):
        super().__init__("AuthGuard")
        self.required_role = required_role
        self.security = HTTPBearer(auto_error=False)
    
    async def can_activate(self, request: Request, **kwargs) -> bool:
        """
        TODO: Implement authentication check
        - Extract token from request
        - Validate JWT token
        - Check user role if required_role is set
        - Inject user context into request.state
        """
        # Get authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return False
        
        token = auth_header.split(" ")[1]
        
        # TODO: Validate token and extract user info
        # For now, mock implementation
        user_context = {"user_id": "123", "role": "admin"}
        request.state.user = user_context
        
        if self.required_role and user_context.get("role") != self.required_role:
            return False
        
        return True

class AdminGuard(AuthGuard):
    """Admin-only access guard"""
    
    def __init__(self):
        super().__init__(required_role="admin")
        self.name = "AdminGuard"

class RateLimitGuard(BaseGuard):
    """Rate limiting guard"""
    
    def __init__(self, requests_per_minute: int = 60):
        super().__init__("RateLimitGuard")
        self.requests_per_minute = requests_per_minute
        # TODO: Use Redis or in-memory cache for production
        # key   -> number of requests seen in the current minute
        # str   -> int
        self._requests_cache: Dict[str, int] = {}
    
    async def can_activate(self, request: Request, **kwargs) -> bool:
        """
        TODO: Implement rate limiting logic
        - Get client identifier (IP, user_id, API key)
        - Check request count in time window
        - Update request count
        - Return False if limit exceeded
        """
        # request.client is Address | None.  Guard against the None case.
        client = request.client
        if client is None:
            # Could decide to reject; here we treat it as a generic bucket.
            client_ip = "unknown"
        else:
            client_ip = client.host
        
        # Simplified implementation - use Redis/DynamoDB for production
        current_count = self._requests_cache.get(client_ip, 0)
        
        if current_count >= self.requests_per_minute:
            return False
        
        self._requests_cache[client_ip] = current_count + 1
        return True
    
    async def handle_failure(self, request: Request, **kwargs) -> HTTPException:
        return HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"}
        )

class OwnershipGuard(BaseGuard):
    """Resource ownership guard"""
    
    def __init__(self, resource_param: str = "upload_id"):
        super().__init__("OwnershipGuard")
        self.resource_param = resource_param
    
    async def can_activate(self, request: Request, **kwargs) -> bool:
        """
        TODO: Check resource ownership
        - Extract resource ID from path parameters
        - Get current user from request.state
        - Check if user owns the resource
        - Allow admin users to bypass ownership check
        """
        user = getattr(request.state, 'user', None)
        if not user:
            return False
        
        # Get resource ID from path parameters
        path_params = kwargs.get('path_params', {})
        resource_id = path_params.get(self.resource_param)
        
        if not resource_id:
            return False
        
        # TODO: Check ownership in database
        # For now, mock implementation
        if user.get("role") == "admin":
            return True
        
        # TODO: Query database to check ownership
        return True

def guards(guard_list: List[BaseGuard]):
    """
    Decorator to apply multiple guards to a route
    Usage: @guards([AuthGuard(), RateLimitGuard(100)])
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request object in args/kwargs
            request = None
            
            # Check if first argument is Request
            if args and hasattr(args[0], 'method') and hasattr(args[0], 'url'):
                request = args[0]
            
            # Check kwargs for request
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise ValueError("Request object not found in function arguments")
            
            # Execute all guards
            for guard in guard_list:
                try:
                    can_proceed = await guard.can_activate(request, path_params=kwargs)
                    if not can_proceed:
                        error = await guard.handle_failure(request, path_params=kwargs)
                        raise error
                except HTTPException:
                    raise
                except Exception as e:
                    log.error(f"Guard {guard.name} failed with error: {str(e)}")
                    raise HTTPException(status_code=500, detail="Internal server error")
            
            # All guards passed, execute the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Convenience guard instances
authGuard = AuthGuard()
adminGuard = AdminGuard()
rateGuard = RateLimitGuard()
authAdminOnlyGuard = AdminGuard()
# Rate limit variants
rateLimitStrict = RateLimitGuard(30)  # 30 requests per minute
rateLimitGenerous = RateLimitGuard(200)  # 200 requests per minute