import logging
import math
import uuid
from datetime import datetime
from typing import List

from ..adapters.dynamodb_adapter import DynamoDBAdapter
from ..adapters.s3_adapter import S3Adapter
from ..models.upload import (
    Upload,
    UploadChunk,
    UploadChunkRequest,
    UploadInitiate,
    UploadResponse,
    UploadStatus,
)

log = logging.getLogger(__name__)

class UploadService:
    def __init__(self):
        self.s3 = S3Adapter()
        self.db = DynamoDBAdapter()
        self.max_file_size = 5 * 1024 * 1024 * 1024  # 5 GB

    # ---------- public -----------------------------------------------------
    async def initiate(self, req: UploadInitiate, user_id: str) -> UploadResponse:
        if req.file_size > self.max_file_size:
            return UploadResponse(
                upload_id="",
                status=UploadStatus.failed,
                progress=0.0,
                message="File too large",
            )

        upload_id = str(uuid.uuid4())
        s3_key = f"uploads/{user_id}/{upload_id}/{req.filename}"

        s3_upload_id = await self.s3.initiate(s3_key, req.content_type)
        if not s3_upload_id:
            return UploadResponse(
                upload_id="", status=UploadStatus.failed, progress=0, message="S3 error"
            )

        chunks = self._make_chunks(req.file_size, req.chunk_size)
        upload = Upload(
            id=upload_id,
            user_id=user_id,
            filename=req.filename,
            file_size=req.file_size,
            content_type=req.content_type,
            upload_id=s3_upload_id,
            status=UploadStatus.uploading,
            chunks=chunks,
            s3_key=s3_key,
            s3_bucket=self.s3.bucket,
        )
        await self.db.put_upload(upload)

        return UploadResponse(
            upload_id=upload_id,
            status=upload.status,
            progress=0.0,
            message="Upload initiated",
            next_chunk=1,
        )

    async def presign(self, req: UploadChunkRequest, user_id: str) -> UploadResponse:
        upload = await self.db.get_upload(req.upload_id)
        if not upload or upload.user_id != user_id:
            return UploadResponse(
                upload_id=req.upload_id,
                status=UploadStatus.failed,
                progress=0,
                message="Upload not found",
            )

        chunk = upload.chunks[req.chunk_number - 1]
        if chunk.is_uploaded:
            return UploadResponse(
                upload_id=req.upload_id,
                status=upload.status,
                progress=upload.upload_progress,
                message="Chunk already uploaded",
                next_chunk=self._next_chunk(upload.chunks),
            )

        url = await self.s3.presign(upload.s3_key, upload.upload_id, req.chunk_number)
        return UploadResponse(
            upload_id=req.upload_id,
            status=upload.status,
            progress=upload.upload_progress,
            message="URL generated",
            upload_url=url,
            next_chunk=req.chunk_number,
        )

    async def mark_complete(
        self, upload_id: str, chunk_number: int, etag: str, user_id: str
    ) -> UploadResponse:
        upload = await self.db.get_upload(upload_id)
        if not upload or upload.user_id != user_id:
            return UploadResponse(
                upload_id=upload_id,
                status=UploadStatus.failed,
                progress=0,
                message="Upload not found",
            )

        upload.chunks[chunk_number - 1].is_uploaded = True
        upload.chunks[chunk_number - 1].etag = etag
        uploaded = sum(1 for c in upload.chunks if c.is_uploaded)
        upload.upload_progress = round(uploaded / len(upload.chunks) * 100, 2)

        await self.db.update_upload(upload_id, upload.dict())

        if uploaded == len(upload.chunks):
            parts = [
                {"PartNumber": c.chunk_number, "ETag": c.etag}
                for c in upload.chunks
                if c.etag
            ]
            if await self.s3.complete(upload.s3_key, upload.upload_id, parts):
                upload.status = UploadStatus.completed
                upload.completed_at = datetime.utcnow()
                await self.db.update_upload(upload_id, upload.dict())
                return UploadResponse(
                    upload_id=upload_id,
                    status=upload.status,
                    progress=100.0,
                    message="Upload completed",
                )
            upload.status = UploadStatus.failed
            await self.db.update_upload(upload_id, upload.dict())
            return UploadResponse(
                upload_id=upload_id,
                status=upload.status,
                progress=upload.upload_progress,
                message="S3 finalize failed",
            )

        return UploadResponse(
            upload_id=upload_id,
            status=upload.status,
            progress=upload.upload_progress,
            message=f"Chunk {chunk_number} saved",
            next_chunk=self._next_chunk(upload.chunks),
        )

    # ---------- helpers ----------------------------------------------------
    def _make_chunks(self, size: int, chunk: int) -> List[UploadChunk]:
        total = math.ceil(size / chunk)
        return [
            UploadChunk(
                chunk_number=i + 1,
                start_byte=i * chunk,
                end_byte=min(size - 1, (i + 1) * chunk - 1),
            )
            for i in range(total)
        ]

    def _next_chunk(self, chunks: List[UploadChunk]):
        for c in chunks:
            if not c.is_uploaded:
                return c.chunk_number
        return None
