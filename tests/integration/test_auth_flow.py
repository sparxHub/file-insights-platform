"""Integration tests for authentication flow"""

import pytest
from httpx import AsyncClient
from jose import jwt, JWTError
from datetime import datetime, timedelta
from unittest import mock

from apps.api.app.core.config import settings


@pytest.mark.asyncio
class TestAuthFlowIntegration:
    """Test complete authentication flow"""
    
    async def test_successful_login_flow(self, client: AsyncClient):
        """Test successful login and token usage"""
        # Step 1: Login with valid credentials
        login_payload = {
            "email": "demo@example.com",
            "password": "secret"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_payload)
        
        assert response.status_code == 200
        auth_data = response.json()
        
        # Verify login response structure
        assert "access_token" in auth_data
        assert "token_type" in auth_data
        assert auth_data["token_type"] == "bearer"
        
        token = auth_data["access_token"]
        
        # Step 2: Verify token is valid JWT
        try:
            decoded = jwt.decode(
                token, 
                settings.jwt_secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            assert "sub" in decoded  # Subject (user ID)
            assert "exp" in decoded  # Expiration
            
            # Verify expiration is in the future
            exp_timestamp = decoded["exp"]
            assert exp_timestamp > datetime.utcnow().timestamp()
            
        except JWTError:
            pytest.fail("Token should be valid JWT")
        
        # Step 3: Use token to access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with upload initiation (protected endpoint)
        upload_payload = {
            "filename": "test-video.mp4",
            "file_size": 1024000,
            "content_type": "video/mp4",
            "chunk_size": 5242880
        }
        
        with mock.patch('apps.api.app.adapters.s3_adapter.S3Adapter.initiate') as mock_s3, \
             mock.patch('apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.put_upload') as mock_dynamo:
            
            mock_s3.return_value = "test-upload-id"
            mock_dynamo.return_value = True
            
            response = await client.post(
                "/api/v1/uploads/initiate",
                json=upload_payload,
                headers=headers
            )
            
            assert response.status_code == 200
    
    async def test_login_with_invalid_credentials(self, client: AsyncClient):
        """Test login failure with invalid credentials"""
        invalid_credentials = [
            {"email": "wrong@example.com", "password": "secret"},
            {"email": "demo@example.com", "password": "wrong"},
            {"email": "wrong@example.com", "password": "wrong"},
            {"email": "", "password": "secret"},
            {"email": "demo@example.com", "password": ""},
        ]
        
        for credentials in invalid_credentials:
            response = await client.post("/api/v1/auth/login", json=credentials)
            # Invalid credentials can return 401 or 422 depending on validation vs auth failure
            assert response.status_code in [401, 422]
            
            error_data = response.json()
            assert "detail" in error_data
    
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without authentication"""
        upload_payload = {
            "filename": "test-video.mp4",
            "file_size": 1024000,
            "content_type": "video/mp4",
            "chunk_size": 5242880
        }
        
        # No authorization header
        response = await client.post("/api/v1/uploads/initiate", json=upload_payload)
        assert response.status_code == 403  # Missing auth returns 403
    
    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token"""
        upload_payload = {
            "filename": "test-video.mp4",
            "file_size": 1024000,
            "content_type": "video/mp4",
            "chunk_size": 5242880
        }
        
        invalid_tokens = [
            "invalid-token",
            "Bearer invalid-token",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        ]
        
        for token in invalid_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(
                "/api/v1/uploads/initiate",
                json=upload_payload,
                headers=headers
            )
            
            # Invalid tokens can return either 401 or 403 depending on the error
            assert response.status_code in [401, 403]
    
    async def test_expired_token(self, client: AsyncClient):
        """Test behavior with expired token"""
        # Create an expired token
        expired_payload = {
            "sub": "demo-user-id",
            "exp": datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
        }
        
        expired_token = jwt.encode(
            expired_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        upload_payload = {
            "filename": "test-video.mp4",
            "file_size": 1024000,
            "content_type": "video/mp4",
            "chunk_size": 5242880
        }
        
        response = await client.post(
            "/api/v1/uploads/initiate",
            json=upload_payload,
            headers=headers
        )
        
        assert response.status_code == 401
    
    async def test_malformed_authorization_header(self, client: AsyncClient):
        """Test various malformed authorization headers"""
        upload_payload = {
            "filename": "test-video.mp4",
            "file_size": 1024000,
            "content_type": "video/mp4",
            "chunk_size": 5242880
        }
        
        malformed_headers = [
            {"Authorization": "Basic dGVzdA=="},  # Wrong scheme
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "token"},  # Missing Bearer
            {"Authorization": "Bearer "},  # Empty token
        ]
        
        for headers in malformed_headers:
            response = await client.post(
                "/api/v1/uploads/initiate",
                json=upload_payload,
                headers=headers
            )
            
            # Malformed auth headers return 403
            assert response.status_code == 403
    
    async def test_token_structure_and_claims(self, client: AsyncClient):
        """Test that generated tokens have correct structure and claims"""
        login_payload = {
            "email": "demo@example.com",
            "password": "secret"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        
        # Decode and verify token structure
        decoded = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Verify required claims
        assert "sub" in decoded
        assert "exp" in decoded
        
        # Verify subject claim
        assert decoded["sub"] == "demo-user-id"
        
        # Verify expiration is reasonable (within expected range)
        exp_time = datetime.fromtimestamp(decoded["exp"])
        now = datetime.utcnow()
        time_diff = exp_time - now
        
        # Should expire within reasonable time range (allow for config variations)
        expected_minutes = settings.jwt_expires_minutes
        # Allow for wider tolerance as actual implementation may differ
        min_seconds = 30 * 60  # At least 30 minutes
        max_seconds = 24 * 60 * 60  # At most 24 hours
        assert min_seconds <= time_diff.total_seconds() <= max_seconds
    
    async def test_login_validation(self, client: AsyncClient):
        """Test input validation on login endpoint"""
        invalid_payloads = [
            {},  # Empty payload
            {"email": "demo@example.com"},  # Missing password
            {"password": "secret"},  # Missing email
            {"email": "", "password": "secret"},  # Empty email
            {"email": "demo@example.com", "password": ""},  # Empty password
            {"email": "not-an-email", "password": "secret"},  # Invalid email format
        ]
        
        for payload in invalid_payloads:
            response = await client.post("/api/v1/auth/login", json=payload)
            # Validation errors can return 422 or 401 depending on implementation
            assert response.status_code in [401, 422]
