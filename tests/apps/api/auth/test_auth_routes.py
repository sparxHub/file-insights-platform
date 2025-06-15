# tests/apps/api/auth/test_auth_routes.py
import pytest
from rich import print


@pytest.mark.asyncio
async def test_login_success(client):
    body = {"email": "demo@example.com", "password": "secret"}
    res = await client.post("/api/v1/auth/login", json=body)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    print("[bold green]✓ login_success passed")


@pytest.mark.asyncio
async def test_login_fail(client):
    body = {"email": "demo@example.com", "password": "wrong"}
    res = await client.post("/api/v1/auth/login", json=body)
    assert res.status_code == 401
    print("[bold green]✓ login_fail passed")
