"""Integration tests for complete upload flow"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.app.main import app
from apps.api.app.models.upload import UploadStatus


@pytest.mark.asyncio
class TestUploadFlowIntegration:
    """Test complete upload flow from initiation to completion"""
    
    async def test_complete_upload_flow_success(self, client: AsyncClient, token: str):
        """Test successful end-to-end upload flow"""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock AWS services
        mock_upload_id = "test-upload-id-123"
        mock_presigned_url = "https://s3.amazonaws.com/presigned-url"
        
        with patch('apps.api.app.adapters.s3_adapter.S3Adapter.initiate') as mock_s3_initiate, \
             patch('apps.api.app.adapters.s3_adapter.S3Adapter.presign') as mock_s3_presign, \
             patch('apps.api.app.adapters.s3_adapter.S3Adapter.complete') as mock_s3_complete, \
             patch('apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.put_upload') as mock_dynamo_put, \
             patch('apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.get_upload') as mock_dynamo_get, \
             patch('apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.update_upload') as mock_dynamo_update:
            
            # Setup mocks
            mock_s3_initiate.return_value = mock_upload_id
            mock_s3_presign.return_value = mock_presigned_url
            mock_s3_complete.return_value = True
            mock_dynamo_put.return_value = True
            mock_dynamo_update.return_value = True
            
            # Step 1: Initiate upload
            initiate_payload = {
                "filename": "test-video.mp4",
                "file_size": 1024000,
                "content_type": "video/mp4",
                "chunk_size": 5242880  # 5MB chunks
            }
            
            response = await client.post(
                "/api/v1/uploads/initiate",
                json=initiate_payload,
                headers=headers
            )
            
            assert response.status_code == 200
            upload_data = response.json()
            upload_id = upload_data["upload_id"]
            
            # Verify initiate response structure
            assert "upload_id" in upload_data
            assert "total_chunks" in upload_data
            assert upload_data["status"] == UploadStatus.pending.value
            
            # Mock the upload object for subsequent calls
            from apps.api.app.models.upload import Upload
            from datetime import datetime
            
            mock_upload = Upload(
                id=upload_id,
                user_id="demo-user-id",
                filename="test-video.mp4",
                file_size=1024000,
                content_type="video/mp4",
                chunk_size=5242880,
                total_chunks=1,
                s3_upload_id=mock_upload_id,
                s3_key=f"uploads/{upload_id}/test-video.mp4",
                status=UploadStatus.uploading,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            mock_dynamo_get.return_value = mock_upload
            
            # Step 2: Get presigned URL for chunk upload
            chunk_payload = {
                "upload_id": upload_id,
                "chunk_number": 1
            }
            
            response = await client.post(
                "/api/v1/uploads/chunk-url",
                json=chunk_payload,
                headers=headers
            )
            
            assert response.status_code == 200
            chunk_data = response.json()
            
            # Verify chunk URL response
            assert "presigned_url" in chunk_data
            assert "upload_id" in chunk_data
            assert chunk_data["next_chunk"] == 2
            assert chunk_data["status"] == UploadStatus.uploading.value
            
            # Step 3: Complete chunk upload
            etag = "test-etag-123"
            
            response = await client.post(
                f"/api/v1/uploads/{upload_id}/chunks/1/complete",
                headers={**headers, "ETag": etag}
            )
            
            assert response.status_code == 200
            completion_data = response.json()
            
            # Verify completion response
            assert completion_data["upload_id"] == upload_id
            assert completion_data["chunk_number"] == 1
            assert completion_data["status"] == UploadStatus.completed.value
            
            # Verify all mocks were called correctly
            mock_s3_initiate.assert_called_once()
            mock_s3_presign.assert_called_once()
            mock_s3_complete.assert_called_once()
            mock_dynamo_put.assert_called()
            mock_dynamo_get.assert_called()
            mock_dynamo_update.assert_called()
    
    async def test_upload_flow_with_multiple_chunks(self, client: AsyncClient, token: str):
        """Test upload flow with multiple chunks"""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Large file requiring multiple chunks
        large_file_size = 15 * 1024 * 1024  # 15MB
        chunk_size = 5 * 1024 * 1024  # 5MB chunks
        expected_chunks = 3
        
        with patch('apps.api.app.adapters.s3_adapter.S3Adapter.initiate') as mock_s3_initiate, \
             patch('apps.api.app.adapters.s3_adapter.S3Adapter.presign') as mock_s3_presign, \
             patch('apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.put_upload') as mock_dynamo_put, \
             patch('apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.get_upload') as mock_dynamo_get:
            
            mock_s3_initiate.return_value = "test-upload-id"
            mock_s3_presign.return_value = "https://s3.amazonaws.com/presigned-url"
            mock_dynamo_put.return_value = True
            
            # Initiate upload
            initiate_payload = {
                "filename": "large-video.mp4",
                "file_size": large_file_size,
                "content_type": "video/mp4",
                "chunk_size": chunk_size
            }
            
            response = await client.post(
                "/api/v1/uploads/initiate",
                json=initiate_payload,
                headers=headers
            )
            
            assert response.status_code == 200
            upload_data = response.json()
            
            # Verify chunk calculation
            assert upload_data["total_chunks"] == expected_chunks
            
            # Test getting presigned URLs for all chunks
            upload_id = upload_data["upload_id"]
            
            # Mock upload object
            from apps.api.app.models.upload import Upload
            from datetime import datetime
            
            mock_upload = Upload(
                id=upload_id,
                user_id="demo-user-id",
                filename="large-video.mp4",
                file_size=large_file_size,
                content_type="video/mp4",
                chunk_size=chunk_size,
                total_chunks=expected_chunks,
                s3_upload_id="test-upload-id",
                s3_key=f"uploads/{upload_id}/large-video.mp4",
                status=UploadStatus.uploading,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            mock_dynamo_get.return_value = mock_upload
            
            # Request presigned URLs for each chunk
            for chunk_num in range(1, expected_chunks + 1):
                chunk_payload = {
                    "upload_id": upload_id,
                    "chunk_number": chunk_num
                }
                
                response = await client.post(
                    "/api/v1/uploads/chunk-url",
                    json=chunk_payload,
                    headers=headers
                )
                
                assert response.status_code == 200
                chunk_data = response.json()
                assert "presigned_url" in chunk_data
                
                expected_next_chunk = chunk_num + 1 if chunk_num < expected_chunks else None
                if expected_next_chunk:
                    assert chunk_data["next_chunk"] == expected_next_chunk
    
    async def test_upload_flow_error_handling(self, client: AsyncClient, token: str):
        """Test error handling in upload flow"""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test S3 failure during initiation
        with patch('apps.api.app.adapters.s3_adapter.S3Adapter.initiate') as mock_s3_initiate:
            mock_s3_initiate.return_value = None  # Simulate S3 failure
            
            initiate_payload = {
                "filename": "test-video.mp4",
                "file_size": 1024000,
                "content_type": "video/mp4",
                "chunk_size": 5242880
            }
            
            response = await client.post(
                "/api/v1/uploads/initiate",
                json=initiate_payload,
                headers=headers
            )
            
            # Should handle S3 failure gracefully
            assert response.status_code == 500
    
    async def test_unauthorized_upload_access(self, client: AsyncClient):
        """Test that upload endpoints require authentication"""
        # Test without authorization header
        initiate_payload = {
            "filename": "test-video.mp4",
            "file_size": 1024000,
            "content_type": "video/mp4",
            "chunk_size": 5242880
        }
        
        response = await client.post(
            "/api/v1/uploads/initiate",
            json=initiate_payload
        )
        
        assert response.status_code == 401
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        
        response = await client.post(
            "/api/v1/uploads/initiate",
            json=initiate_payload,
            headers=headers
        )
        
        assert response.status_code == 401
    
    async def test_invalid_upload_data(self, client: AsyncClient, token: str):
        """Test validation of upload data"""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test missing required fields
        invalid_payloads = [
            {},  # Empty payload
            {"filename": "test.mp4"},  # Missing file_size
            {"file_size": 1024},  # Missing filename
            {"filename": "", "file_size": 1024},  # Empty filename
            {"filename": "test.mp4", "file_size": 0},  # Zero file size
            {"filename": "test.mp4", "file_size": -1},  # Negative file size
        ]
        
        for payload in invalid_payloads:
            response = await client.post(
                "/api/v1/uploads/initiate",
                json=payload,
                headers=headers
            )
            
            assert response.status_code == 400
