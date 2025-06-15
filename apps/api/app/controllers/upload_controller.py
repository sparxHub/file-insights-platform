from typing import Any, Dict

from ..models.upload import UploadChunkRequest, UploadInitiate, UploadResponse
from ..services.upload_service import UploadService

svc = UploadService()

class UploadController:
    async def initiate(self, body: UploadInitiate, user: Dict[str, Any]) -> UploadResponse:
        return await svc.initiate(body, user["user_id"])

    async def presign(self, body: UploadChunkRequest, user: Dict[str, Any]) -> UploadResponse:
        return await svc.presign(body, user["user_id"])

    async def complete(self, upload_id: str, chunk: int, etag: str, user: Dict[str, Any]) -> UploadResponse:
        return await svc.mark_complete(upload_id, chunk, etag, user["user_id"])
