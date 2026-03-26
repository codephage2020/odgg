"""Tests for modeling and code generation API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from odgg.api.v1.sessions import _sessions
from odgg.app import app
from odgg.models.session import SessionState, StepStatus


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def session_with_model():
    """Create a session with a complete dimensional model."""
    session = SessionState(session_id="model-test")
    session.business_process = "Order Processing"
    session.grain_description = "One row per order"
    session.dimensional_model = {
        "version": "1.0",
        "business_process": "Order Processing",
        "fact_table": {
            "name": "fact_orders",
            "grain_description": "One row per order",
            "grain_columns": ["order_id"],
            "measures": [
                {
                    "name": "total",
                    "source_column": "total",
                    "source_table": "orders",
                    "aggregation": "SUM",
                    "data_type": "NUMERIC",
                }
            ],
            "dimension_keys": ["dim_customer_key"],
            "source_tables": ["orders"],
        },
        "dimensions": [
            {
                "name": "dim_customer",
                "source_table": "customer",
                "columns": ["name"],
                "natural_key": "id",
            }
        ],
    }
    # Set step 8 as active
    for step in session.steps:
        if step.step_number < 8:
            step.status = StepStatus.COMPLETED
        elif step.step_number == 8:
            step.status = StepStatus.ACTIVE
    _sessions["model-test"] = session
    yield session
    _sessions.pop("model-test", None)


class TestGenerateCodeEndpoint:
    async def test_generate_code_success(self, client, session_with_model):
        resp = await client.post("/api/v1/modeling/generate", json={
            "session_id": "model-test",
            "mode": "full",
            "include_dbt": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ddl" in data
        assert "etl" in data
        assert "data_dictionary" in data
        assert "dbt" in data
        assert "CREATE TABLE" in data["ddl"]
        assert "INSERT INTO" in data["etl"]

    async def test_generate_no_dbt(self, client, session_with_model):
        resp = await client.post("/api/v1/modeling/generate", json={
            "session_id": "model-test",
            "mode": "full",
            "include_dbt": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "dbt" not in data

    async def test_generate_incremental(self, client, session_with_model):
        resp = await client.post("/api/v1/modeling/generate", json={
            "session_id": "model-test",
            "mode": "incremental",
        })
        assert resp.status_code == 200
        assert "ON CONFLICT" in resp.json()["etl"]

    async def test_generate_session_not_found(self, client):
        resp = await client.post("/api/v1/modeling/generate", json={
            "session_id": "nonexistent",
        })
        assert resp.status_code == 404

    async def test_generate_no_model(self, client):
        session = SessionState(session_id="no-model")
        _sessions["no-model"] = session
        try:
            resp = await client.post("/api/v1/modeling/generate", json={
                "session_id": "no-model",
            })
            assert resp.status_code == 400
            assert "No dimensional model" in resp.json()["detail"]
        finally:
            _sessions.pop("no-model", None)


class TestSuggestEndpoint:
    async def test_suggest_session_not_found(self, client):
        resp = await client.post("/api/v1/modeling/suggest", json={
            "session_id": "nonexistent",
            "step_number": 3,
        })
        assert resp.status_code == 404

    async def test_suggest_invalid_step(self, client):
        session = SessionState(session_id="step-test")
        _sessions["step-test"] = session
        try:
            resp = await client.post("/api/v1/modeling/suggest", json={
                "session_id": "step-test",
                "step_number": 99,
            })
            assert resp.status_code == 400
        finally:
            _sessions.pop("step-test", None)

    async def test_suggest_step_without_ai(self, client):
        """Steps 1, 2, 8 don't have AI suggestions."""
        session = SessionState(session_id="noai-test")
        session.steps[0].status = StepStatus.ACTIVE  # Step 1
        _sessions["noai-test"] = session
        try:
            resp = await client.post("/api/v1/modeling/suggest", json={
                "session_id": "noai-test",
                "step_number": 1,
            })
            assert resp.status_code == 400 or resp.status_code == 500
        finally:
            _sessions.pop("noai-test", None)


class TestStreamEndpoint:
    async def test_stream_session_not_found(self, client):
        resp = await client.post("/api/v1/modeling/suggest/stream", json={
            "session_id": "nonexistent",
            "step_number": 3,
        })
        assert resp.status_code == 404
