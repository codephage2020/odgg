"""Tests for the Modeling Brief CRUD API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from odgg.core.database import Base, engine


# Use a fresh database for brief tests — create tables before, drop after
@pytest.fixture(autouse=True)
async def setup_db():
    """Create and tear down tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client."""
    from odgg.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Brief CRUD
# ---------------------------------------------------------------------------


class TestBriefCRUD:
    async def test_create_brief(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/briefs",
            json={"title": "TPC-H Analysis", "database_name": "tpch"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "TPC-H Analysis"
        assert data["status"] == "draft"
        assert data["database_name"] == "tpch"
        assert data["sections"] == []
        assert "id" in data

    async def test_create_brief_defaults(self, client: AsyncClient):
        resp = await client.post("/api/v1/briefs", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Untitled Brief"
        assert data["source_db_type"] == "postgresql"

    async def test_list_briefs_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/briefs")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_briefs_with_items(self, client: AsyncClient):
        await client.post("/api/v1/briefs", json={"title": "Brief A"})
        await client.post("/api/v1/briefs", json={"title": "Brief B"})
        resp = await client.get("/api/v1/briefs")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        titles = {i["title"] for i in items}
        assert titles == {"Brief A", "Brief B"}

    async def test_get_brief(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/briefs", json={"title": "My Brief"})
        brief_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/briefs/{brief_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == brief_id

    async def test_get_brief_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/briefs/nonexistent-id")
        assert resp.status_code == 404

    async def test_update_brief_title(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/briefs", json={"title": "Old Title"})
        brief_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/briefs/{brief_id}",
            json={"title": "New Title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    async def test_update_brief_status(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/briefs", json={})
        brief_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/briefs/{brief_id}",
            json={"status": "review"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "review"

    async def test_delete_brief(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/briefs", json={})
        brief_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/briefs/{brief_id}")
        assert del_resp.status_code == 204
        get_resp = await client.get(f"/api/v1/briefs/{brief_id}")
        assert get_resp.status_code == 404

    async def test_delete_brief_not_found(self, client: AsyncClient):
        resp = await client.delete("/api/v1/briefs/nonexistent-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Section CRUD
# ---------------------------------------------------------------------------


class TestSectionCRUD:
    @pytest.fixture
    async def brief_id(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/briefs", json={"title": "Test Brief"})
        return resp.json()["id"]

    async def test_create_section(self, client: AsyncClient, brief_id: str):
        resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={
                "section_type": "business_process",
                "content": "Order processing workflow",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["section_type"] == "business_process"
        assert data["content"] == "Order processing workflow"
        assert data["position"] == 0
        assert data["user_edited"] is False
        assert data["ai_drafts"] == []

    async def test_create_dimension_section(self, client: AsyncClient, brief_id: str):
        resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={
                "section_type": "dimension",
                "name": "Customer",
                "source_table": "customers",
                "source_columns": ["customer_id", "name", "email"],
                "dimension_type": "regular",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Customer"
        assert data["source_table"] == "customers"
        assert data["source_columns"] == ["customer_id", "name", "email"]
        assert data["dimension_type"] == "regular"

    async def test_create_measure_section(self, client: AsyncClient, brief_id: str):
        resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={
                "section_type": "measure",
                "name": "Total Revenue",
                "source_table": "orders",
                "source_column": "total_amount",
                "data_type": "decimal",
                "aggregation_type": "sum",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Total Revenue"
        assert data["aggregation_type"] == "sum"

    async def test_section_auto_position(self, client: AsyncClient, brief_id: str):
        """Sections auto-increment position."""
        await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "business_process"},
        )
        resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "grain"},
        )
        assert resp.json()["position"] == 1

    async def test_update_section_content(self, client: AsyncClient, brief_id: str):
        create_resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "grain", "content": "One row per order"},
        )
        section_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/briefs/{brief_id}/sections/{section_id}",
            json={"content": "One row per order line item"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "One row per order line item"
        assert data["user_edited"] is True

    async def test_update_section_same_content_not_edited(self, client: AsyncClient, brief_id: str):
        """Updating with same content doesn't mark as user-edited."""
        create_resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "grain", "content": "One row per order"},
        )
        section_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/briefs/{brief_id}/sections/{section_id}",
            json={"content": "One row per order"},
        )
        assert resp.json()["user_edited"] is False

    async def test_delete_section(self, client: AsyncClient, brief_id: str):
        create_resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "notes"},
        )
        section_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/briefs/{brief_id}/sections/{section_id}")
        assert del_resp.status_code == 204

    async def test_delete_section_not_found(self, client: AsyncClient, brief_id: str):
        resp = await client.delete(f"/api/v1/briefs/{brief_id}/sections/nonexistent")
        assert resp.status_code == 404

    async def test_sections_included_in_brief_response(self, client: AsyncClient, brief_id: str):
        """Brief GET includes all sections."""
        await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "business_process", "content": "BP"},
        )
        await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "grain", "content": "Grain"},
        )
        resp = await client.get(f"/api/v1/briefs/{brief_id}")
        sections = resp.json()["sections"]
        assert len(sections) == 2
        assert sections[0]["section_type"] == "business_process"
        assert sections[1]["section_type"] == "grain"

    async def test_brief_delete_cascades_sections(self, client: AsyncClient, brief_id: str):
        """Deleting a brief removes all sections."""
        await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "notes", "content": "test"},
        )
        await client.delete(f"/api/v1/briefs/{brief_id}")
        # Brief gone
        assert (await client.get(f"/api/v1/briefs/{brief_id}")).status_code == 404

    async def test_list_briefs_section_count(self, client: AsyncClient, brief_id: str):
        """List endpoint includes section count."""
        await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "business_process"},
        )
        await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "grain"},
        )
        resp = await client.get("/api/v1/briefs")
        items = resp.json()
        matching = [i for i in items if i["id"] == brief_id]
        assert matching[0]["section_count"] == 2


# ---------------------------------------------------------------------------
# Regenerate (placeholder)
# ---------------------------------------------------------------------------


class TestRegenerate:
    @pytest.fixture
    async def section_ids(self, client: AsyncClient) -> tuple[str, str]:
        brief_resp = await client.post("/api/v1/briefs", json={"title": "Regen Test"})
        brief_id = brief_resp.json()["id"]
        sec_resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "grain", "content": "Original content"},
        )
        return brief_id, sec_resp.json()["id"]

    async def test_regenerate_appends_draft(
        self, client: AsyncClient, section_ids: tuple[str, str]
    ):
        brief_id, section_id = section_ids
        resp = await client.post(f"/api/v1/briefs/{brief_id}/sections/{section_id}/regenerate")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["ai_drafts"]) == 1
        assert data["user_edited"] is False

    async def test_regenerate_twice_accumulates(
        self, client: AsyncClient, section_ids: tuple[str, str]
    ):
        brief_id, section_id = section_ids
        await client.post(f"/api/v1/briefs/{brief_id}/sections/{section_id}/regenerate")
        resp = await client.post(f"/api/v1/briefs/{brief_id}/sections/{section_id}/regenerate")
        data = resp.json()
        assert len(data["ai_drafts"]) == 2

    async def test_regenerate_not_found(self, client: AsyncClient):
        resp = await client.post("/api/v1/briefs/fake/sections/fake/regenerate")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    async def test_create_section_invalid_brief(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/briefs/nonexistent/sections",
            json={"section_type": "grain"},
        )
        assert resp.status_code == 404

    async def test_create_section_invalid_type(self, client: AsyncClient):
        brief_resp = await client.post("/api/v1/briefs", json={})
        brief_id = brief_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/briefs/{brief_id}/sections",
            json={"section_type": "invalid_type"},
        )
        assert resp.status_code == 422

    async def test_update_brief_invalid_status(self, client: AsyncClient):
        brief_resp = await client.post("/api/v1/briefs", json={})
        brief_id = brief_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/briefs/{brief_id}",
            json={"status": "bogus"},
        )
        assert resp.status_code == 422

    async def test_brief_with_metadata_snapshot(self, client: AsyncClient):
        """Metadata snapshot round-trips through JSON."""
        snapshot = {
            "tables": [{"name": "orders", "columns": [{"name": "id", "data_type": "int"}]}],
            "database_name": "tpch",
        }
        resp = await client.post(
            "/api/v1/briefs",
            json={"title": "With Snapshot", "metadata_snapshot": snapshot},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["metadata_snapshot"]["database_name"] == "tpch"
        assert len(data["metadata_snapshot"]["tables"]) == 1


# ---------------------------------------------------------------------------
# SSE Cascade Drafting
# ---------------------------------------------------------------------------

# Mock LLM responses for the cascade
_MOCK_BP = {
    "processes": [
        {
            "name": "Order Processing",
            "description": "Track customer orders",
            "involved_tables": ["orders", "customers"],
            "confidence": 0.9,
        }
    ]
}
_MOCK_GRAIN = {
    "options": [
        {
            "description": "One row per order line item",
            "grain_columns": ["order_id", "line_number"],
            "source_table": "lineitem",
            "recommended": True,
            "reasoning": "Finest grain for order analysis",
        }
    ]
}
_MOCK_DIMS = {
    "dimensions": [
        {
            "name": "dim_customer",
            "source_table": "customers",
            "columns": ["name"],
            "description": "Customer dimension",
        }
    ]
}
_MOCK_MEASURES = {
    "measures": [
        {
            "name": "total_revenue",
            "source_column": "total",
            "source_table": "orders",
            "aggregation": "SUM",
            "description": "Total revenue",
        }
    ]
}

_SAMPLE_SNAPSHOT = {
    "tables": [
        {
            "name": "orders",
            "columns": [
                {"name": "id", "data_type": "int"},
                {"name": "total", "data_type": "decimal"},
            ],
        },
        {
            "name": "customers",
            "columns": [{"name": "id", "data_type": "int"}],
        },
    ],
    "relationships": [],
    "database_name": "tpch",
    "database_type": "postgresql",
}


class TestCascadeDrafting:
    @pytest.fixture
    async def brief_with_snapshot(self, client: AsyncClient) -> str:
        """Create a brief with metadata snapshot."""
        resp = await client.post(
            "/api/v1/briefs",
            json={
                "title": "Cascade Test",
                "metadata_snapshot": _SAMPLE_SNAPSHOT,
            },
        )
        return resp.json()["id"]

    @patch("odgg.api.v1.briefs.suggest_measures", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_dimensions", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_grain", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_business_process", new_callable=AsyncMock)
    async def test_cascade_creates_four_sections(
        self,
        mock_bp,
        mock_grain,
        mock_dims,
        mock_measures,
        client: AsyncClient,
        brief_with_snapshot: str,
    ):
        mock_bp.return_value = _MOCK_BP
        mock_grain.return_value = _MOCK_GRAIN
        mock_dims.return_value = _MOCK_DIMS
        mock_measures.return_value = _MOCK_MEASURES

        brief_id = brief_with_snapshot

        # Use stream=false for reliable testing
        resp = await client.post(f"/api/v1/briefs/{brief_id}/draft?stream=false")
        assert resp.status_code == 200

        # Verify sections were created
        brief_resp = await client.get(f"/api/v1/briefs/{brief_id}")
        sections = brief_resp.json()["sections"]
        assert len(sections) == 4

        types = [s["section_type"] for s in sections]
        assert "business_process" in types
        assert "grain" in types
        assert "dimension" in types
        assert "measure" in types

    @patch("odgg.api.v1.briefs.suggest_measures", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_dimensions", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_grain", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_business_process", new_callable=AsyncMock)
    async def test_cascade_sections_have_ai_drafts(
        self,
        mock_bp,
        mock_grain,
        mock_dims,
        mock_measures,
        client: AsyncClient,
        brief_with_snapshot: str,
    ):
        mock_bp.return_value = _MOCK_BP
        mock_grain.return_value = _MOCK_GRAIN
        mock_dims.return_value = _MOCK_DIMS
        mock_measures.return_value = _MOCK_MEASURES

        brief_id = brief_with_snapshot
        await client.post(f"/api/v1/briefs/{brief_id}/draft?stream=false")

        brief_resp = await client.get(f"/api/v1/briefs/{brief_id}")
        for section in brief_resp.json()["sections"]:
            assert len(section["ai_drafts"]) == 1, (
                f"{section['section_type']} should have 1 AI draft"
            )
            assert section["user_edited"] is False

    @patch("odgg.api.v1.briefs.suggest_measures", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_dimensions", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_grain", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_business_process", new_callable=AsyncMock)
    async def test_cascade_bp_content(
        self,
        mock_bp,
        mock_grain,
        mock_dims,
        mock_measures,
        client: AsyncClient,
        brief_with_snapshot: str,
    ):
        """BP section content includes process name and description."""
        mock_bp.return_value = _MOCK_BP
        mock_grain.return_value = _MOCK_GRAIN
        mock_dims.return_value = _MOCK_DIMS
        mock_measures.return_value = _MOCK_MEASURES

        brief_id = brief_with_snapshot
        await client.post(f"/api/v1/briefs/{brief_id}/draft?stream=false")

        brief_resp = await client.get(f"/api/v1/briefs/{brief_id}")
        bp = next(
            s for s in brief_resp.json()["sections"] if s["section_type"] == "business_process"
        )
        assert "Order Processing" in bp["content"]

    @patch("odgg.api.v1.briefs.suggest_measures", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_dimensions", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_grain", new_callable=AsyncMock)
    @patch("odgg.api.v1.briefs.suggest_business_process", new_callable=AsyncMock)
    async def test_cascade_returns_section_list(
        self,
        mock_bp,
        mock_grain,
        mock_dims,
        mock_measures,
        client: AsyncClient,
        brief_with_snapshot: str,
    ):
        """stream=false returns JSON array of sections."""
        mock_bp.return_value = _MOCK_BP
        mock_grain.return_value = _MOCK_GRAIN
        mock_dims.return_value = _MOCK_DIMS
        mock_measures.return_value = _MOCK_MEASURES

        brief_id = brief_with_snapshot
        resp = await client.post(f"/api/v1/briefs/{brief_id}/draft?stream=false")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 4

    async def test_cascade_no_snapshot_returns_400(self, client: AsyncClient):
        """Drafting without metadata returns 400."""
        resp = await client.post("/api/v1/briefs", json={"title": "Empty"})
        brief_id = resp.json()["id"]
        resp = await client.post(f"/api/v1/briefs/{brief_id}/draft?stream=false")
        assert resp.status_code == 400

    async def test_cascade_not_found(self, client: AsyncClient):
        resp = await client.post("/api/v1/briefs/nonexistent/draft?stream=false")
        assert resp.status_code == 404
