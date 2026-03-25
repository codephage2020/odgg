"""Tests for API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_session(client):
    resp = await client.post("/api/v1/sessions", json={"source_db_type": "postgresql"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["state"]["steps"][0]["status"] == "active"


@pytest.mark.asyncio
async def test_get_session(client):
    # Create first
    create_resp = await client.post("/api/v1/sessions", json={})
    session_id = create_resp.json()["session_id"]

    # Get
    resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    resp = await client.get("/api/v1/sessions/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_step_optimistic_lock(client):
    # Create session
    create_resp = await client.post("/api/v1/sessions", json={})
    data = create_resp.json()
    session_id = data["session_id"]
    version = data["state"]["version"]

    # Confirm step 1
    resp = await client.post(
        f"/api/v1/sessions/{session_id}/steps",
        json={"step_number": 1, "action": "confirm", "version": version},
    )
    assert resp.status_code == 200
    new_version = resp.json()["version"]
    assert new_version == version + 1

    # Try with stale version - should fail
    resp = await client.post(
        f"/api/v1/sessions/{session_id}/steps",
        json={"step_number": 2, "action": "confirm", "version": version},
    )
    assert resp.status_code == 409
