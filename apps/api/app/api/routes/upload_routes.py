from fastapi import APIRouter, Depends, Header, Request

from ...controllers.upload_controller import UploadController
from ...decorators.guard_combinations import authenticated_user, owner_or_admin
from ...decorators.guards import OwnershipGuard, guards
from ...decorators.validation import BodyValidation, validation
from ...middleware.auth import get_current_user
from ...models.upload import UploadChunkRequest, UploadInitiate, UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])
ctl = UploadController()

@router.post("/initiate", response_model=UploadResponse)
@authenticated_user
@validation([BodyValidation(UploadInitiate)])  # Apply validation after the router
async def initiate(request: Request, user=Depends(get_current_user)):
    body = request.state.validated["body"]
    return await ctl.initiate(body, user)
# @router.post("/initiate", response_model=UploadResponse)
# async def initiate(request: Request):
#     breakpoint() 
#     # Temporary for debugging
#     return {"message": "Debug point reached"}


@router.post("/chunk-url", response_model=UploadResponse)
@authenticated_user
@validation([BodyValidation(UploadChunkRequest)])
async def chunk_url(request: Request, user=Depends(get_current_user)):
    body = request.state.validated["body"]
    return await ctl.presign(body, user)

@authenticated_user
@router.post("/{upload_id}/chunks/{chunk_number}/complete", response_model=UploadResponse)
async def chunk_complete(
    upload_id: str,
    chunk_number: int,
    etag: str = Header(..., alias="ETag"),
    user=Depends(get_current_user),
):
    return await ctl.complete(upload_id, chunk_number, etag, user)
