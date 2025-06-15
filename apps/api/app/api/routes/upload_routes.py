from fastapi import APIRouter, Depends, Header

from ...controllers.upload_controller import UploadController
from ...middleware.auth import get_current_user
from ...models.upload import UploadChunkRequest, UploadInitiate, UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])
ctl = UploadController()

@router.post("/initiate", response_model=UploadResponse)
async def initiate(body: UploadInitiate, user=Depends(get_current_user)):
    return await ctl.initiate(body, user)

@router.post("/chunk-url", response_model=UploadResponse)
async def chunk_url(body: UploadChunkRequest, user=Depends(get_current_user)):
    return await ctl.presign(body, user)

@router.post("/{upload_id}/chunks/{chunk_number}/complete", response_model=UploadResponse)
async def chunk_complete(
    upload_id: str,
    chunk_number: int,
    etag: str = Header(..., alias="ETag"),
    user=Depends(get_current_user),
):
    return await ctl.complete(upload_id, chunk_number, etag, user)
