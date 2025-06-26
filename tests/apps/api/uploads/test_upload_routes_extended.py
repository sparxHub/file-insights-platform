# tests/apps/api/uploads/test_upload_routes_extended.py
#
# Adds coverage for:
#   •  BodyValidation decorator
#   •  authenticated_user decorator (AuthGuard + RateLimitGuard)
#   •  chunk-url route
#   •  chunk-complete route
#
import asyncio
from typing import Any, Dict

import pytest

from apps.api.app.decorators.guards import RateLimitGuard
from apps.api.app.models.upload import Upload, UploadChunkRequest, UploadInitiate, UploadStatus


# ---------------------------------------------------------------------------
# Helper – reset the RateLimitGuard “cache” between tests so we never run into
#           cross-test pollution.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_rate_limit_guard_cache():
    # Reset the rate limit guard instances that are used in guard combinations
    from apps.api.app.decorators.guard_combinations import GuardCombinations
    
    # Clear cache for all known guard instances
    for guards in [GuardCombinations.AUTHENTICATED_USER, GuardCombinations.ADMIN_ACCESS, 
                   GuardCombinations.PUBLIC_STRICT, GuardCombinations.OWNER_OR_ADMIN,
                   GuardCombinations.ADMIN_STRICT]:
        for guard in guards:
            if isinstance(guard, RateLimitGuard):
                guard._requests_cache.clear()
    
    yield
    
    # Clear again after test
    for guards in [GuardCombinations.AUTHENTICATED_USER, GuardCombinations.ADMIN_ACCESS, 
                   GuardCombinations.PUBLIC_STRICT, GuardCombinations.OWNER_OR_ADMIN,
                   GuardCombinations.ADMIN_STRICT]:
        for guard in guards:
            if isinstance(guard, RateLimitGuard):
                guard._requests_cache.clear()


# ---------------------------------------------------------------------------
# Shared sample payloads
# ---------------------------------------------------------------------------
VALID_INITIATE: Dict[str, Any] = {
    "filename": "video.mp4",
    "file_size": 10_485_760,
    "content_type": "video/mp4",
    "chunk_size": 5_242_880,
}
VALID_CHUNK_URL: Dict[str, Any] = {
    "upload_id": "FAKE-S3-UPLOAD-ID",
    "chunk_number": 1,
}
VALID_ETAG = "mock-etag-1"


# ---------------------------------------------------------------------------
# Common monkey-patches for S3 & Dynamo so every test below only worries about
# what *it* is asserting.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _monkeypatch_adapters(monkeypatch):
    # S3 initiate
    async def fake_s3_initiate(self, key, content_type):
        return "FAKE-S3-UPLOAD-ID"

    async def fake_s3_presign(self, key, upload_id, part_number):
        return f"https://example.com/presigned/upload/{part_number}"

    async def fake_s3_complete(self, key, parts):
        return "https://example.com/final/location"

    monkeypatch.setattr(
        "apps.api.app.adapters.s3_adapter.S3Adapter.initiate", fake_s3_initiate
    )
    monkeypatch.setattr(
        "apps.api.app.adapters.s3_adapter.S3Adapter.presign", fake_s3_presign
    )
    monkeypatch.setattr(
        "apps.api.app.adapters.s3_adapter.S3Adapter.complete", fake_s3_complete
    )

    # Dynamo – very small in-mem “DB”
    _mem_uploads: Dict[str, Any] = {}

    async def fake_put_upload(self, upload):
        _mem_uploads[upload.id] = upload

    async def fake_get_upload(self, upload_id):
        return _mem_uploads.get(upload_id)

    async def fake_update_upload(self, upload_id, data):
        upload = _mem_uploads[upload_id]
        # Create a new upload by merging current data with updates
        current_data = upload.model_dump()
        current_data.update(data)
        _mem_uploads[upload_id] = Upload.model_validate(current_data)
        return _mem_uploads[upload_id]

    monkeypatch.setattr(
        "apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.put_upload",
        fake_put_upload,
    )
    monkeypatch.setattr(
        "apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.get_upload",
        fake_get_upload,
    )
    monkeypatch.setattr(
        "apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.update_upload",
        fake_update_upload,
    )

    yield


# ---------------------------------------------------------------------------
# 1. BodyValidation – bad payload returns 422
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_upload_initiate_validation_failure(client, token):
    bad_body = VALID_INITIATE.copy()
    bad_body.pop("filename")  # Break the schema – filename is required

    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/v1/uploads/initiate", json=bad_body, headers=headers)

    assert res.status_code == 422
    # BodyValidation should place a detail field in the response
    assert "detail" in res.json()


# ---------------------------------------------------------------------------
# 2. RateLimitGuard – hit the same route >limit times should yield 429
#    (limit is 100 on authenticated_user)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rate_limit_guard_on_authenticated_user(client, token):
    headers = {"Authorization": f"Bearer {token}"}

    async def _make_request():
        return await client.post(
            "/api/v1/uploads/initiate", json=VALID_INITIATE, headers=headers
        )

    # 100 requests must pass, the 101st must fail.
    for _ in range(100):
        res = await _make_request()
        assert res.status_code == 200

    res = await _make_request()
    assert res.status_code == 429
    assert res.json()["detail"] == "Rate limit exceeded"


# ---------------------------------------------------------------------------
# 3. /chunk-url – success path returns next_chunk increment + presigned_url
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chunk_url_success(client, token):
    headers = {"Authorization": f"Bearer {token}"}

    # First, initialise an upload to insert it in our fake DB:
    res_init = await client.post(
        "/api/v1/uploads/initiate", json=VALID_INITIATE, headers=headers
    )
    assert res_init.status_code == 200
    upload_id = res_init.json()["upload_id"]

    body = {**VALID_CHUNK_URL, "upload_id": upload_id}
    res = await client.post("/api/v1/uploads/chunk-url", json=body, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["upload_id"] == upload_id
    assert data["upload_url"].startswith("https://example.com/presigned")
    assert data["next_chunk"] == body["chunk_number"]  # next chunk to upload is still this chunk
    assert data["status"] == UploadStatus.uploading.value


# ---------------------------------------------------------------------------
# 4. /{upload_id}/chunks/{chunk_number}/complete – needs ETag header, auth
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chunk_complete_success(client, token):
    # 1. Set up proper authorization headers
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Make the request with headers
    res_init = await client.post(
        "/api/v1/uploads/initiate", 
        json=VALID_INITIATE, 
        headers=headers
    )
    
    # 3. Assert response
    assert res_init.status_code == 200
    upload_id = res_init.json()["upload_id"]

    # 2. mark chunk-complete
    url = f"/api/v1/uploads/{upload_id}/chunks/1/complete"
    res = await client.post(url, headers={**headers, "ETag": VALID_ETAG})

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == UploadStatus.uploading.value
    assert data["progress"] == 50.0  # First chunk of 2 completed
    assert data["message"] == "Chunk 1 saved"
    assert data["next_chunk"] == 2


# # ---------------------------------------------------------------------------
# # 5. Missing ETag header should give 422 (FastAPI’s validation on Header)
# # ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chunk_complete_missing_etag(client, token):
    headers = {"Authorization": f"Bearer {token}"}

    res_init = await client.post(
        "/api/v1/uploads/initiate", json=VALID_INITIATE, headers=headers
    )
    upload_id = res_init.json()["upload_id"]

    url = f"/api/v1/uploads/{upload_id}/chunks/1/complete"
    res = await client.post(url, headers=headers)  # Intentionally no ETag

    assert res.status_code == 422