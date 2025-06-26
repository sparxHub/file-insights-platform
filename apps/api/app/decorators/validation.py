import json
import logging
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

class BaseValidation(ABC):
    """Base class for all validation rules"""
    
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    async def validate(self, request: Request, **kwargs) -> Dict[str, Any]:
        """
        Validate request data
        Returns validated data or raises ValidationError/HTTPException
        """
        pass

class BodyValidation(BaseValidation):
    """Request body validation"""
    
    def __init__(self, model: Type[BaseModel], name: Optional[str] = None):
        super().__init__(name or f"BodyValidation[{model.__name__}]")
        self.model = model
    
    async def validate(self, request: Request, **kwargs) -> Dict[str, Any]:
        """
        TODO: Validate request body against Pydantic model
        - Extract body content
        - Parse JSON
        - Validate against model
        - Return validated data
        """
        try:
            body = await request.body()
            if not body:
                raise HTTPException(status_code=400, detail="Request body is required")
            
            json_data = json.loads(body)
            validated_data = self.model.model_validate(json_data)
            return {"body": validated_data}
        
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in request body")
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")

class QueryValidation(BaseValidation):
    """Query parameters validation"""
    
    def __init__(self, model: Type[BaseModel], name: Optional[str] = None):
        super().__init__(name or f"QueryValidation[{model.__name__}]")
        self.model = model
    
    async def validate(self, request: Request, **kwargs) -> Dict[str, Any]:
        """
        TODO: Validate query parameters
        - Extract query parameters
        - Convert to dict
        - Validate against model
        - Return validated data
        """
        try:
            query_params = dict(request.query_params)
            validated_data = self.model.model_validate(query_params)
            return {"query": validated_data}
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Query validation error: {str(e)}")

class PathValidation(BaseValidation):
    """Path parameters validation"""
    
    def __init__(self, model: Type[BaseModel], name: Optional[str] = None):
        super().__init__(name or f"PathValidation[{model.__name__}]")
        self.model = model
    
    async def validate(self, request: Request, **kwargs) -> Dict[str, Any]:
        """
        TODO: Validate path parameters
        - Extract path parameters from kwargs
        - Validate against model
        - Return validated data
        """
        try:
            path_params = kwargs.get('path_params', {})
            validated_data = self.model.model_validate(path_params)
            return {"path": validated_data}
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Path validation error: {str(e)}")

class CustomValidation(BaseValidation):
    """Custom validation logic"""
    
    def __init__(self, validator_func: Callable, name: Optional[str] = None):
        super().__init__(name or "CustomValidation")
        self.validator_func = validator_func
    
    async def validate(self, request: Request, **kwargs) -> Dict[str, Any]:
        """
        TODO: Execute custom validation function
        - Call custom validator function
        - Handle validation results
        - Return validated data or raise error
        """
        try:
            result = await self.validator_func(request, **kwargs)
            return {"custom": result} if result else {}
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Custom validation failed: {str(e)}")

def validation(validation_list: List[BaseValidation]):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request object
            request = None
            
            if args and hasattr(args[0], 'method') and hasattr(args[0], 'url'):
                request = args[0]
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise ValueError("Request object not found in function arguments")
            
            # Store validated data
            validated_data = {}
            
            # Execute all validations
            for validator in validation_list:
                try:
                    result = await validator.validate(request, path_params=kwargs)
                    validated_data.update(result)
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")
            
            # Set validated data in request state
            request.state.validated = validated_data
            
            # Execute the original function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator

# Pre-defined validation instances for common models
from ..models.upload import UploadChunkRequest, UploadInitiate

uploadInitiateValidation = BodyValidation(UploadInitiate)
uploadChunkValidation = BodyValidation(UploadChunkRequest)

# Query validation models
from pydantic import BaseModel


class PaginationQuery(BaseModel):
    page: int = 1
    limit: int = 10
    sort_by: str = "created_at"
    sort_order: str = "desc"

paginationValidation = QueryValidation(PaginationQuery)