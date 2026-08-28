from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture
async def client(session) -> AsyncIterator[AsyncClient]:
    async def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()
