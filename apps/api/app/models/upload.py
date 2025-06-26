from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class UploadStatus(str, Enum):
    pending = "pending"
    uploading = "uploading"
    completed = "completed"
    failed = "failed"

class UploadChunk(BaseModel):
    chunk_number: int = Field(..., ge=1)
    start_byte: int
    end_byte: int
    is_uploaded: bool = False
    etag: str | None = None

class Upload(BaseModel):
    id: str | None = None
    user_id: str
    filename: str
    file_size: int = Field(..., gt=0)
    content_type: str
    upload_id: str | None = None
    s3_key: str | None = None
    s3_bucket: str | None = None
    status: UploadStatus = UploadStatus.pending
    chunks: List[UploadChunk] = Field(default_factory=list)
    upload_progress: Decimal = Field(default_factory=lambda: Decimal("0.0"))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    model_config = ConfigDict(json_encoders={Decimal: float})

# DTOs
class UploadInitiate(BaseModel):
    filename: str
    file_size: int = Field(..., gt=0, le=5*1024*1024*1024)
    content_type: str
    chunk_size: int = Field(5*1024*1024, ge=1024*1024, le=100*1024*1024)

class UploadChunkRequest(BaseModel):
    upload_id: str
    chunk_number: int = Field(..., ge=1)

class UploadResponse(BaseModel):
    upload_id: str
    status: UploadStatus
    progress: float
    message: str
    upload_url: str | None = None
    next_chunk: int | None = None
