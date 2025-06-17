from .guards import (
    AdminGuard,
    AuthGuard,
    BaseGuard,
    OwnershipGuard,
    RateLimitGuard,
    guards,
)


# Pre-defined guard combinations for common patterns
class GuardCombinations:
    """Common guard combinations"""
    
    # Basic user authentication with rate limiting
    AUTHENTICATED_USER = [AuthGuard(), RateLimitGuard(100)]
    
    # Admin access with generous rate limits
    ADMIN_ACCESS = [AdminGuard(), RateLimitGuard(500)]
    
    # Public endpoint with strict rate limiting
    PUBLIC_STRICT = [RateLimitGuard(20)]
    
    # Resource owner or admin access
    OWNER_OR_ADMIN = [AuthGuard(), OwnershipGuard()]
    
    # High-security operations
    ADMIN_STRICT = [AdminGuard(), RateLimitGuard(50)]

# Convenience decorators for common patterns
def authenticated_user(func):
    """Decorator for authenticated user endpoints"""
    return guards(GuardCombinations.AUTHENTICATED_USER)(func)

def admin_only(func):
    """Decorator for admin-only endpoints"""
    return guards(GuardCombinations.ADMIN_ACCESS)(func)

def owner_or_admin(func):
    """Decorator for resource owner or admin access"""
    return guards(GuardCombinations.OWNER_OR_ADMIN)(func)
