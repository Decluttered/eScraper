import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.imports import sanitize_import_text
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app

PAYLOAD = {
    "source": "KLEINANZEIGEN_DE",
    "external_id": "2971234567",
    "source_url": "https://www.kleinanzeigen.de/s-anzeige/2971234567",
    "captured_at": "2026-08-27T10:00:00Z",
    "title": "RTX 3060 12GB",
    "description": "gebraucht und getestet",
    "asking_price_cents": 17000,
    "shipping_cents": 690,
    "condition": "Gebraucht",
    "location_summary": "10115 Berlin",
    "sale_format": "CLASSIFIED_AD",
    "import_method": "CONFIRMED_EXTENSION",
}


@pytest.fixture
def client():
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    from sqlalchemy.ext.asyncio import AsyncSession

    async def override_session():
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session

    # Create tables
    from app.db.models import *  # noqa: F401,F403
    import asyncio

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create())

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_sanitize_import_text_redacts_contacts() -> None:
    text = "Kontakt: test@example.com oder 017612345678"
    sanitized = sanitize_import_text(text)
    assert "[REDACTED-CONTACT]" in sanitized
    assert "test@example.com" not in sanitized
    assert "017612345678" not in sanitized


def test_sanitize_import_text_keeps_model_numbers() -> None:
    text = "RTX 3060 12GB Modellnummer 12345"
    assert sanitize_import_text(text) == text


def test_first_import_returns_201_and_second_returns_200(client: TestClient) -> None:
    response_first = client.post("/api/v1/imports/listings", json=PAYLOAD)
    assert response_first.status_code == 201
    assert response_first.json()["created"] is True

    response_second = client.post("/api/v1/imports/listings", json=PAYLOAD)
    assert response_second.status_code == 200
    assert response_second.json()["created"] is False


def test_import_rejects_extra_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/imports/listings",
        json={**PAYLOAD, "seller_phone": "017612345678"},
    )
    assert response.status_code == 422
