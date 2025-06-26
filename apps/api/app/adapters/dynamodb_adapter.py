import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aioboto3
from botocore.exceptions import ClientError

from ..core.config import settings
from ..models.upload import Upload, UploadStatus

log = logging.getLogger(__name__)

class DynamoDBAdapter:
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        self.table_name = settings.dynamodb_uploads_table

    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python objects to DynamoDB-compatible types"""
        serialized: Dict[str, Any] = {}
        for key, value in item.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, UploadStatus):
                serialized[key] = value.value
            elif isinstance(value, float):
                serialized[key] = Decimal(str(value))  # Safe decimal conversion
            elif hasattr(value, 'value'):  # Handle other enums
                serialized[key] = value.value
            else:
                serialized[key] = value
        return serialized
    def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB types back to Python objects"""
        deserialized = dict(item)
        
        # Convert status back to enum
        if "status" in deserialized:
            deserialized["status"] = UploadStatus(deserialized["status"])
        
        # Convert datetime strings back to datetime objects
        datetime_fields = ["created_at", "updated_at"]
        for field in datetime_fields:
            if field in deserialized and isinstance(deserialized[field], str):
                deserialized[field] = datetime.fromisoformat(deserialized[field].replace('Z', '+00:00'))
        
        # Ensure upload_progress is Decimal (DynamoDB returns it as Decimal already)
        if "upload_progress" in deserialized and not isinstance(deserialized["upload_progress"], Decimal):
            deserialized["upload_progress"] = Decimal(str(deserialized["upload_progress"]))
        
        return deserialized

    async def put_upload(self, upload: Upload) -> bool:
        """Put upload item to DynamoDB"""
        try:
            item = upload.model_dump()
            serialized_item = self._serialize_item(item)
            
            async with self.session.resource('dynamodb') as resource:
                table = await resource.Table(self.table_name)
                await table.put_item(Item=serialized_item)
            return True
        except ClientError as e:
            log.error(f"Error putting upload {upload.id}: {str(e)}")
            return False

    async def get_upload(self, upload_id: str) -> Optional[Upload]:
        """Get upload item from DynamoDB"""
        try:
            async with self.session.resource('dynamodb') as resource:
                table = await resource.Table(self.table_name)
                response = await table.get_item(Key={"id": upload_id})
                
                if "Item" not in response:
                    return None
                
                item = response["Item"]
                deserialized_item = self._deserialize_item(item)
                return Upload.model_validate(deserialized_item)
                
        except ClientError as e:
            log.error(f"Error retrieving upload {upload_id}: {str(e)}")
            return None
        except Exception as e:
            log.error(f"Unexpected error retrieving upload {upload_id}: {str(e)}")
            return None

    async def update_upload(self, upload_id: str, data: Dict[str, Any]) -> bool:
        """Update upload item in DynamoDB"""
        try:
            upload = await self.get_upload(upload_id)
            if not upload:
                log.warning(f"Upload {upload_id} not found for update")
                return False
            
            # Update the upload object with new data
            for k, v in data.items():
                setattr(upload, k, v)
            upload.updated_at = datetime.utcnow()
            
            # Save the updated upload back to DynamoDB
            return await self.put_upload(upload)
        except Exception as e:
            log.error(f"Error updating upload {upload_id}: {str(e)}")
            return False
