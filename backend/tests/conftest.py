"""Shared test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from odgg.app import app
from odgg.core.database import Base, engine


def pytest_addoption(parser):
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Run live LLM evals",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-llm"):
        return
    skip_llm = pytest.mark.skip(reason="needs --run-llm option to run")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip_llm)


@pytest.fixture(autouse=True, scope="session")
async def _create_tables():
    """Ensure all ORM tables exist before tests run (lifespan doesn't fire in ASGITransport)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
