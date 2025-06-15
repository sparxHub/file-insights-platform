import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..api.app.adapters.dynamodb_adapter import DynamoDBAdapter
from .models import WorkerResult

logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    def __init__(self):
        self.db = DynamoDBAdapter()
    
    @abstractmethod
    async def process(self, upload_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the uploaded file and return insights"""
        pass
    
    def handle_sqs_event(self, event, context):
        """Standard SQS event handler for all workers"""
        try:
            for record in event['Records']:
                message = json.loads(record['body'])
                
                # Process the upload
                result = await self.process(message)
                
                # Save insights to database
                await self.save_insights(message['upload_id'], result)
                
                logger.info(f"Processed upload {message['upload_id']}")
                
        except Exception as e:
            logger.error(f"Worker failed: {str(e)}")
            raise  # Let Lambda retry
    
    async def save_insights(self, upload_id: str, insights: Dict[str, Any]):
        """Save processing results to insights table"""
        await self.db.put_insight({
            'upload_id': upload_id,
            'insight_type': insights['insight_type'],
            'result': insights['result'],
            'created_at': datetime.utcnow().isoformat()
        })
