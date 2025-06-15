# tests/apps/api/uploads/test_upload_routes.py
import pytest
from rich import print

from apps.api.app.models.upload import UploadStatus


@pytest.mark.asyncio
async def test_upload_initiate_requires_auth(client):
    body = {
        "filename": "video.mp4",
        "file_size": 10_485_760,
        "content_type": "video/mp4",
        "chunk_size": 5_242_880,
    }
    res = await client.post("/api/v1/uploads/initiate", json=body)
    assert res.status_code == 403
    print("[bold green]✓ initiate_requires_auth passed")


@pytest.mark.asyncio
async def test_upload_initiate_with_token(client, token, monkeypatch):
    # ---- mock S3 ----
    async def fake_s3_initiate(self, key, content_type):
        return "FAKE-S3-UPLOAD-ID"

    monkeypatch.setattr(
        "apps.api.app.adapters.s3_adapter.S3Adapter.initiate",
        fake_s3_initiate,
    )

    # ---- mock Dynamo ----
    async def fake_put_upload(self, upload): ...
    async def fake_get_upload(self, upload_id): return None

    monkeypatch.setattr(
        "apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.put_upload",
        fake_put_upload,
    )
    monkeypatch.setattr(
        "apps.api.app.adapters.dynamodb_adapter.DynamoDBAdapter.get_upload",
        fake_get_upload,
    )

    # ---- exercise ----
    body = {
        "filename": "video.mp4",
        "file_size": 10_485_760,
        "content_type": "video/mp4",
        "chunk_size": 5_242_880,
    }
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/v1/uploads/initiate", json=body, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == UploadStatus.uploading.value
    assert data["upload_id"]
    assert data["next_chunk"] == 1
    print("[bold green]✓ initiate_with_token passed")
