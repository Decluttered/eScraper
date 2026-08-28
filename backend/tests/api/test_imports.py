from sqlalchemy import select

from app.db.models.listing import RawListingModel

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


async def test_import_listing_is_idempotent(client) -> None:
    first = await client.post("/api/v1/imports/listings", json=PAYLOAD)
    second = await client.post("/api/v1/imports/listings", json=PAYLOAD)

    assert first.status_code == 201
    assert first.json()["created"] is True
    assert second.status_code == 200
    assert second.json()["created"] is False


async def test_import_listing_rejects_extra_fields(client) -> None:
    response = await client.post(
        "/api/v1/imports/listings", json={**PAYLOAD, "images": ["https://example.com/a.jpg"]}
    )

    assert response.status_code == 422

    for extra_field in ("metadata", "seller_phone", "seller_email"):
        response = await client.post(
            "/api/v1/imports/listings", json={**PAYLOAD, extra_field: "value"}
        )
        assert response.status_code == 422


async def test_import_listing_redacts_contact_details(client, session) -> None:
    payload = {
        **PAYLOAD,
        "external_id": "2971234568",
        "description": "Kontakt: max.mustermann@example.com oder 0151 2345678",
    }

    response = await client.post("/api/v1/imports/listings", json=payload)
    assert response.status_code == 201

    raw = await session.scalar(
        select(RawListingModel).where(RawListingModel.external_id == "2971234568")
    )

    assert raw is not None
    assert raw.raw_description.count("[REDACTED-CONTACT]") == 2
    assert "max.mustermann@example.com" not in raw.raw_description
    assert "0151 2345678" not in raw.raw_description
