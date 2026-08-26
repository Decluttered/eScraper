# PC Hardware Flipping Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first dashboard that ingests authorized marketplace observations, normalizes PC hardware, estimates conservative resale values, and produces explainable acquisition recommendations.

**Architecture:** A React/TypeScript frontend consumes a versioned FastAPI API. PostgreSQL stores immutable observations and evaluation snapshots, while a Redis-backed Python worker polls eBay through its official Browse API and re-evaluates changed data. A user-triggered browser companion imports one currently open Kleinanzeigen listing without background crawling.

**Tech Stack:** Python 3.13, FastAPI 0.141, Pydantic 2.15, SQLAlchemy 2.0, Alembic 1.19, PostgreSQL 17, Redis 8, Dramatiq 2.2, pytest 9; React 19, TypeScript 7, Vite 8, TanStack Query 5, React Router 7, Recharts 3, Vitest 4, Playwright 1.62; Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-27-pc-hardware-flipping-dashboard-design.md`

## Global Constraints

- The MVP is local-first, single-user, binds application services to localhost, and stores only `EUR` money in integer cents.
- Percentages and rates use integer basis points; persisted timestamps are UTC; persisted IDs are UUIDs.
- eBay discovery uses the official Browse API. Realized sales enter only through authorized Product Research-derived manual or CSV imports.
- Kleinanzeigen support is explicit-click, active-tab-only companion import. No background navigation, polling, pagination, login automation, CAPTCHA handling, anti-bot bypass, seller contact collection, or image copying is permitted.
- Active asks never become realized sale prices. Low or stale sold-comparable confidence caps recommendations at `WATCH`.
- Every evaluation snapshot stores the observation IDs and effective profile/rule versions used to produce it.
- Every buying recommendation fails closed on ambiguous products, missing evidence, stale data, blocked risk rules, or calculation errors.
- Tax values are estimates. No code may claim to determine legal status, warranty obligations, or binding tax treatment.
- Secrets live only in ignored local environment configuration and may never appear in API responses, logs, fixtures, screenshots, or commits.
- Backend behavior is implemented test-first. Frontend tasks use rendered component tests and browser verification. Live eBay acceptance remains open unless credentials and a successful network call are evidenced.
- Use targeted `git add` paths in every commit; never use `git add .`.
- Before Task 1, `stat /mnt/d/Work/eScraper` must succeed. If it reports `No such device`, run `wsl --shutdown` from Windows PowerShell, reopen Codex, and repeat the check before creating an isolated execution worktree.

---

## File and responsibility map

### Root

- `.gitignore` — excludes credentials, local databases, caches, builds, screenshots, and extension packages.
- `.env.example` — documents safe configuration names without values that grant access.
- `compose.yaml` — local PostgreSQL, Redis, backend, worker, and frontend services.
- `README.md` — setup, commands, compliance boundary, and acceptance status.

### Backend

- `backend/pyproject.toml` — Python package metadata, runtime dependencies, and test configuration.
- `backend/Dockerfile` — backend and worker-compatible Python image.
- `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/*.py` — schema migrations.
- `backend/app/main.py` — FastAPI application factory only.
- `backend/app/api/router.py` — versioned router composition.
- `backend/app/api/*.py` — thin HTTP handlers grouped by feature.
- `backend/app/core/config.py` — typed settings.
- `backend/app/core/logging.py` — structured redacting logging.
- `backend/app/core/security.py` — local extension pairing and origin checks.
- `backend/app/db/base.py`, `backend/app/db/session.py` — SQLAlchemy metadata and session lifecycle.
- `backend/app/db/models/*.py` — persistence models split by aggregate.
- `backend/app/domain/enums.py`, `backend/app/domain/money.py` — stable primitive domain types.
- `backend/app/domain/market.py`, `finance.py`, `scoring.py`, `part_out.py` — pure calculation types and functions.
- `backend/app/schemas/*.py` — HTTP and import contracts.
- `backend/app/services/ingestion.py` — immutable raw ingestion and deduplication.
- `backend/app/services/normalization.py` — deterministic product, variant, and risk-text recognition.
- `backend/app/services/market_estimation.py` — comparable weighting, outlier filtering, percentiles, and confidence.
- `backend/app/services/evaluation.py` — orchestration across market, finance, risk, and scoring.
- `backend/app/services/max_purchase.py` — inverse purchase-price solver.
- `backend/app/sources/base.py` — source-adapter protocol.
- `backend/app/sources/ebay.py` — official eBay OAuth and Browse API adapter.
- `backend/app/sources/imports.py` — authorized CSV and manual comparable import.
- `backend/tests/**` — unit, API, persistence, adapter, and integration tests.

### Worker

- `worker/worker.py` — Dramatiq broker initialization.
- `worker/tasks.py` — idempotent poll, normalize, evaluate, stale-mark, and retry tasks.
- `worker/tests/test_tasks.py` — task behavior against controlled repositories and recorded responses.

### Frontend

- `frontend/package.json` — scripts and pinned compatible dependency ranges.
- `frontend/src/app/router.tsx` — route table.
- `frontend/src/app/AppShell.tsx` — navigation and page frame.
- `frontend/src/api/client.ts`, `frontend/src/api/types.ts` — validated HTTP access and shared response types.
- `frontend/src/components/**` — focused reusable UI primitives.
- `frontend/src/features/{overview,deals,watchlists,market,inventory,settings}/**` — page-specific components and queries.
- `frontend/src/styles.css` — accessible visual tokens and responsive layout.
- `frontend/tests/**` — component and route tests.
- `frontend/e2e/**` — Playwright critical-flow tests.

### Companion extension

- `extension/manifest.json` — active-tab-only permissions.
- `extension/src/extract.ts` — current-page field extraction with no navigation or requests.
- `extension/src/popup.tsx` — preview, correction, explicit confirmation, and local submission.
- `extension/src/pairing.ts` — short-lived local pairing token storage.
- `extension/tests/**` — saved local HTML fixture and popup tests.

---

### Task 1: Establish the local backend health slice

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `compose.yaml`
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: none.
- Produces: `app.main.create_app() -> FastAPI`, `app.core.config.get_settings() -> Settings`, `GET /api/v1/health -> {"status":"ok"}`.

- [ ] **Step 1: Add package configuration and the failing health test**

Create `backend/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "escraper-backend"
version = "0.1.0"
requires-python = ">=3.13,<3.15"
dependencies = [
  "alembic>=1.19,<2",
  "asyncpg>=0.31,<1",
  "dramatiq[redis]>=2.2,<3",
  "fastapi>=0.141,<0.142",
  "httpx>=0.28,<1",
  "pydantic-settings>=2.15,<3",
  "python-multipart>=0.0.20,<1",
  "redis>=8.1,<9",
  "sqlalchemy>=2.0.52,<2.1",
  "uvicorn[standard]>=0.35,<1"
]

[project.optional-dependencies]
dev = [
  "pytest>=9.1,<10",
  "pytest-asyncio>=1.4,<2",
  "ruff>=0.12,<1"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py313"
```

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    response = TestClient(create_app()).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test and verify the expected failure**

Run:

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest tests/test_health.py -v
```

Expected: FAIL during collection because `app.main` does not exist.

- [ ] **Step 3: Implement settings, router, and application factory**

Create `backend/app/core/config.py`:

```python
from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "eScraper"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://escraper:escraper@localhost:5432/escraper"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origin: AnyHttpUrl = "http://localhost:5173"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `backend/app/api/health.py`:

```python
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
```

Create `backend/app/api/router.py`:

```python
from fastapi import APIRouter

from app.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(settings.frontend_origin).rstrip("/")],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Extension-Token"],
    )
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
```

- [ ] **Step 4: Add safe local configuration and containers**

Create `.env.example` with these names and non-secret local defaults:

```dotenv
DATABASE_URL=postgresql+asyncpg://escraper:escraper@postgres:5432/escraper
REDIS_URL=redis://redis:6379/0
FRONTEND_ORIGIN=http://localhost:5173
LOG_LEVEL=INFO
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
EBAY_MARKETPLACE_ID=EBAY_DE
```

Create `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
*.pyc
node_modules/
dist/
build/
playwright-report/
test-results/
*.zip
*.crx
*.pem
*.key
```

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/app /app/app
RUN pip install --no-cache-dir .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `compose.yaml` with PostgreSQL, Redis, and backend services bound locally:

```yaml
services:
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: escraper
      POSTGRES_USER: escraper
      POSTGRES_PASSWORD: escraper
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U escraper"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:8-alpine
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - redis_data:/data

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
```

- [ ] **Step 5: Verify health and static checks**

Run:

```bash
cd backend
.venv/bin/pytest tests/test_health.py -v
.venv/bin/ruff check app tests
```

Expected: one passing test and no Ruff findings.

- [ ] **Step 6: Commit the health slice**

```bash
git add .gitignore .env.example compose.yaml backend/pyproject.toml backend/Dockerfile backend/app backend/tests/test_health.py
git commit -m "feat: establish local backend health slice"
```

---

### Task 2: Add exact money, rate, and enum primitives

**Files:**
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/enums.py`
- Create: `backend/app/domain/money.py`
- Create: `backend/tests/domain/test_money.py`
- Create: `backend/tests/domain/test_enums.py`

**Interfaces:**
- Consumes: Python 3.13.
- Produces: `Money`, `apply_basis_points()`, and stable enums `Currency`, `Marketplace`, `ProductCategory`, `Condition`, `Recommendation`, `ConfidenceLevel`, `ComparableStatus`, `TaxProfileType`.

- [ ] **Step 1: Write failing primitive tests**

Create `backend/tests/domain/test_money.py`:

```python
import pytest

from app.domain.money import Money, apply_basis_points


def test_money_addition_requires_same_currency() -> None:
    assert Money(1250) + Money(275) == Money(1525)


def test_basis_points_round_half_up() -> None:
    assert apply_basis_points(25690, 500) == 1285


def test_money_rejects_non_integer_cents() -> None:
    with pytest.raises(TypeError, match="integer cents"):
        Money(12.5)  # type: ignore[arg-type]
```

Create `backend/tests/domain/test_enums.py`:

```python
from app.domain.enums import Currency, Marketplace, Recommendation


def test_stable_external_enum_values() -> None:
    assert Currency.EUR.value == "EUR"
    assert Marketplace.EBAY_DE.value == "EBAY_DE"
    assert Recommendation.NEGOTIATE.value == "NEGOTIATE"
```

- [ ] **Step 2: Run the tests and verify they fail because the modules are absent**

Run: `cd backend && .venv/bin/pytest tests/domain/test_money.py tests/domain/test_enums.py -v`

Expected: FAIL during collection with missing `app.domain` modules.

- [ ] **Step 3: Implement the stable enums**

Create `backend/app/domain/enums.py`:

```python
from enum import StrEnum


class Currency(StrEnum):
    EUR = "EUR"


class Marketplace(StrEnum):
    EBAY_DE = "EBAY_DE"
    KLEINANZEIGEN_DE = "KLEINANZEIGEN_DE"
    MANUAL = "MANUAL"


class ProductCategory(StrEnum):
    GPU = "GPU"
    CPU = "CPU"
    MAINBOARD = "MAINBOARD"
    RAM = "RAM"
    SSD = "SSD"
    PSU = "PSU"
    CASE = "CASE"
    COOLER = "COOLER"
    COMPLETE_PC = "COMPLETE_PC"
    OTHER = "OTHER"


class Condition(StrEnum):
    USED = "USED"
    REFURBISHED = "REFURBISHED"
    UNTESTED = "UNTESTED"
    DEFECTIVE = "DEFECTIVE"
    UNKNOWN = "UNKNOWN"


class Recommendation(StrEnum):
    BUY = "BUY"
    NEGOTIATE = "NEGOTIATE"
    WATCH = "WATCH"
    REJECT = "REJECT"


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ComparableStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SOLD = "SOLD"


class TaxProfileType(StrEnum):
    PRIVATE = "PRIVATE"
    SMALL_BUSINESS = "SMALL_BUSINESS"
    STANDARD_VAT = "STANDARD_VAT"
    MARGIN_SCHEME = "MARGIN_SCHEME"
```

- [ ] **Step 4: Implement money and basis-point arithmetic**

Create `backend/app/domain/money.py`:

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.domain.enums import Currency


def _round_decimal(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def apply_basis_points(cents: int, basis_points: int) -> int:
    if not isinstance(cents, int) or not isinstance(basis_points, int):
        raise TypeError("amount and rate must use integers")
    return _round_decimal(Decimal(cents) * Decimal(basis_points) / Decimal(10_000))


@dataclass(frozen=True, slots=True)
class Money:
    cents: int
    currency: Currency = Currency.EUR

    def __post_init__(self) -> None:
        if not isinstance(self.cents, int):
            raise TypeError("money must use integer cents")

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.cents - other.cents, self.currency)

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency is not other.currency:
            raise ValueError("currency mismatch")
```

- [ ] **Step 5: Verify the primitive tests pass**

Run: `cd backend && .venv/bin/pytest tests/domain/test_money.py tests/domain/test_enums.py -v`

Expected: four passing tests.

- [ ] **Step 6: Commit the primitives**

```bash
git add backend/app/domain backend/tests/domain/test_money.py backend/tests/domain/test_enums.py
git commit -m "feat: add exact money and marketplace primitives"
```

---

### Task 3: Persist products and immutable listing observations

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/app/db/models/product.py`
- Create: `backend/app/db/models/listing.py`
- Create: `backend/tests/db/conftest.py`
- Create: `backend/tests/db/test_listing_models.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_products_and_listings.py`

**Interfaces:**
- Consumes: `ProductCategory`, `Marketplace`, `Condition`, SQLAlchemy async session.
- Produces: `Base`, `ProductModel`, `ProductAliasModel`, `RawListingModel`, `ListingObservationModel`, `get_session()`, and migration revision `0001`.

- [ ] **Step 1: Write the failing persistence test and async database fixture**

Create `backend/tests/db/conftest.py`:

```python
import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://escraper:escraper@localhost:5432/escraper_test",
)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as database_session:
        yield database_session
        await database_session.rollback()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

Create `backend/tests/db/test_listing_models.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.product import ProductModel
from app.domain.enums import Condition, Marketplace, ProductCategory


async def test_observation_links_raw_evidence_to_canonical_product(session) -> None:
    product = ProductModel(
        category=ProductCategory.GPU,
        manufacturer="NVIDIA",
        canonical_model="RTX 3060",
        variant="12GB",
        attributes={"vram_gb": 12},
    )
    raw = RawListingModel(
        source=Marketplace.EBAY_DE,
        external_id="v1|123|0",
        source_url="https://www.ebay.de/itm/123",
        captured_at=datetime(2026, 8, 27, tzinfo=UTC),
        raw_title="RTX 3060 12GB",
        raw_description="tested",
        asking_price_cents=18000,
        shipping_cents=690,
        raw_condition="Gebraucht",
        location_summary="Berlin",
        payload_checksum="sha256:one",
        import_method="EBAY_API",
        raw_metadata={},
    )
    session.add_all([product, raw])
    await session.flush()
    observation = ListingObservationModel(
        raw_listing_id=raw.id,
        product_id=product.id,
        asking_price_cents=18000,
        shipping_cents=690,
        condition=Condition.USED,
        sale_format="FIXED_PRICE",
        model_match_confidence_bps=10000,
        flags=[],
    )
    session.add(observation)
    await session.commit()

    stored = await session.scalar(select(ListingObservationModel))
    assert stored is not None
    assert stored.product_id == product.id
    assert stored.raw_listing_id == raw.id
```

- [ ] **Step 2: Start a disposable test database and verify the test fails**

Run:

```bash
docker run --name escraper-test-postgres --rm -d -e POSTGRES_USER=escraper -e POSTGRES_PASSWORD=escraper -e POSTGRES_DB=escraper_test -p 127.0.0.1:5432:5432 postgres:17-alpine
cd backend
.venv/bin/pytest tests/db/test_listing_models.py -v
```

Expected: FAIL during collection because `app.db.base` and model modules do not exist.

- [ ] **Step 3: Implement database base and session lifecycle**

Create `backend/app/db/base.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

Create `backend/app/db/session.py`:

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
```

- [ ] **Step 4: Implement product and listing models**

Create `backend/app/db/models/product.py`:

```python
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import ProductCategory


class ProductModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("manufacturer", "canonical_model", "variant", name="uq_product_variant"),
    )

    category: Mapped[ProductCategory]
    manufacturer: Mapped[str] = mapped_column(String(120))
    canonical_model: Mapped[str] = mapped_column(String(160))
    variant: Mapped[str] = mapped_column(String(120), default="")
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    ean: Mapped[str | None] = mapped_column(String(32))
    mpn: Mapped[str | None] = mapped_column(String(120))
    ebay_product_id: Mapped[str | None] = mapped_column(String(120))
    windows_11_status: Mapped[str | None] = mapped_column(String(40))


class ProductAliasModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_aliases"
    __table_args__ = (UniqueConstraint("normalized_alias", name="uq_product_alias"),)

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    normalized_alias: Mapped[str] = mapped_column(String(240))
    required_tokens: Mapped[list[str]] = mapped_column(JSONB, default=list)
    excluded_tokens: Mapped[list[str]] = mapped_column(JSONB, default=list)
```

Create `backend/app/db/models/listing.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import Condition, Marketplace


class RawListingModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "raw_listings"
    __table_args__ = (
        UniqueConstraint("source", "external_id", "payload_checksum", name="uq_raw_payload"),
        Index("ix_raw_listing_source_capture", "source", "captured_at"),
    )

    source: Mapped[Marketplace]
    external_id: Mapped[str] = mapped_column(String(240))
    source_url: Mapped[str] = mapped_column(String(2048))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_title: Mapped[str] = mapped_column(String(500))
    raw_description: Mapped[str] = mapped_column(String(8000), default="")
    asking_price_cents: Mapped[int] = mapped_column(BigInteger)
    shipping_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    raw_condition: Mapped[str] = mapped_column(String(120), default="")
    location_summary: Mapped[str] = mapped_column(String(240), default="")
    payload_checksum: Mapped[str] = mapped_column(String(80))
    import_method: Mapped[str] = mapped_column(String(40))
    raw_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ListingObservationModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "listing_observations"

    raw_listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_listings.id", ondelete="RESTRICT"), unique=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT")
    )
    asking_price_cents: Mapped[int] = mapped_column(BigInteger)
    shipping_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    condition: Mapped[Condition]
    sale_format: Mapped[str] = mapped_column(String(40))
    seller_type: Mapped[str | None] = mapped_column(String(40))
    model_match_confidence_bps: Mapped[int] = mapped_column(default=0)
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    review_status: Mapped[str] = mapped_column(String(40), default="PENDING")
```

Update `backend/app/db/models/__init__.py` to import all four classes so Alembic sees them.

- [ ] **Step 5: Add and apply the first migration**

Configure `backend/migrations/env.py` with `Base.metadata` and the async URL from `get_settings()`. Generate the revision:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "add products and listings"
mv migrations/versions/*_add_products_and_listings.py migrations/versions/0001_products_and_listings.py
.venv/bin/alembic upgrade head
```

Inspect the generated revision and require explicit `products`, `product_aliases`, `raw_listings`, and `listing_observations` create/drop operations before continuing.

- [ ] **Step 6: Run the persistence test and migration round-trip**

Run:

```bash
cd backend
TEST_DATABASE_URL=postgresql+asyncpg://escraper:escraper@localhost:5432/escraper_test .venv/bin/pytest tests/db/test_listing_models.py -v
DATABASE_URL=postgresql+asyncpg://escraper:escraper@localhost:5432/escraper_test .venv/bin/alembic downgrade base
DATABASE_URL=postgresql+asyncpg://escraper:escraper@localhost:5432/escraper_test .venv/bin/alembic upgrade head
docker stop escraper-test-postgres
```

Expected: test passes; downgrade, upgrade, and disposable-container cleanup exit 0.

- [ ] **Step 7: Commit product and listing persistence**

```bash
git add backend/app/db backend/tests/db backend/alembic.ini backend/migrations
git commit -m "feat: persist products and listing observations"
```

---

### Task 4: Persist market, cost, risk, and evaluation snapshots

**Files:**
- Create: `backend/app/db/models/market.py`
- Create: `backend/app/db/models/evaluation.py`
- Modify: `backend/app/db/models/__init__.py`
- Create: `backend/tests/db/test_evaluation_models.py`
- Create: `backend/migrations/versions/0002_market_and_evaluations.py`

**Interfaces:**
- Consumes: `ProductModel`, `ListingObservationModel`, stable enums.
- Produces: `MarketComparableModel`, `CostProfileModel`, `RiskRuleModel`, `EvaluationSnapshotModel`, revision `0002`.

- [ ] **Step 1: Write the failing evaluation-snapshot persistence test**

Create `backend/tests/db/test_evaluation_models.py` with one product, observation, cost profile, and snapshot. Assert that the snapshot retains `cost_profile_version`, `risk_rule_versions`, `comparable_ids`, `expected_profit_cents`, `downside_profit_cents`, `maximum_purchase_price_cents`, `score`, and `recommendation` after commit and reload.

Use these exact expected values in the assertion:

```python
assert stored.cost_profile_version == 1
assert stored.risk_rule_versions == {"gpu_shipping": 1}
assert stored.comparable_ids == []
assert stored.expected_profit_cents == 4100
assert stored.downside_profit_cents == 1400
assert stored.maximum_purchase_price_cents == 17200
assert stored.score == 81
assert stored.recommendation is Recommendation.NEGOTIATE
```

- [ ] **Step 2: Run the test and verify missing model failure**

Run: `cd backend && .venv/bin/pytest tests/db/test_evaluation_models.py -v`

Expected: FAIL during collection because `app.db.models.evaluation` is absent.

- [ ] **Step 3: Implement market and effective-dated configuration models**

Create `backend/app/db/models/market.py` with:

```python
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import ComparableStatus, Condition, Marketplace, TaxProfileType


class MarketComparableModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "market_comparables"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    source: Mapped[Marketplace]
    status: Mapped[ComparableStatus]
    condition: Mapped[Condition]
    item_price_cents: Mapped[int] = mapped_column(BigInteger)
    shipping_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    variant_match_confidence_bps: Mapped[int] = mapped_column(Integer)
    source_quality: Mapped[str] = mapped_column(String(40))
    observation_count: Mapped[int] = mapped_column(Integer, default=1)
    sold_through_bps: Mapped[int | None] = mapped_column(Integer)
    source_note: Mapped[str] = mapped_column(String(500), default="")


class CostProfileModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "cost_profiles"

    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tax_profile: Mapped[TaxProfileType]
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB)


class RiskRuleModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "risk_rules"

    key: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matcher: Mapped[dict[str, object]] = mapped_column(JSONB)
    severity: Mapped[str] = mapped_column(String(40))
    required_evidence: Mapped[list[str]] = mapped_column(JSONB, default=list)
    reserve_adjustment_bps: Mapped[int] = mapped_column(Integer, default=0)
    recommendation_cap: Mapped[str | None] = mapped_column(String(40))
    explanation: Mapped[str] = mapped_column(String(500))
```

- [ ] **Step 4: Implement immutable evaluation snapshot storage**

Create `backend/app/db/models/evaluation.py`:

```python
import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import ConfidenceLevel, Recommendation


class EvaluationSnapshotModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_snapshots"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listing_observations.id", ondelete="RESTRICT")
    )
    cost_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cost_profiles.id", ondelete="RESTRICT")
    )
    cost_profile_version: Mapped[int] = mapped_column(Integer)
    risk_rule_versions: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    comparable_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    downside_resale_cents: Mapped[int] = mapped_column(BigInteger)
    expected_resale_cents: Mapped[int] = mapped_column(BigInteger)
    optimistic_resale_cents: Mapped[int] = mapped_column(BigInteger)
    expected_profit_cents: Mapped[int] = mapped_column(BigInteger)
    downside_profit_cents: Mapped[int] = mapped_column(BigInteger)
    expected_roi_bps: Mapped[int] = mapped_column(Integer)
    maximum_purchase_price_cents: Mapped[int] = mapped_column(BigInteger)
    liquidity_bps: Mapped[int] = mapped_column(Integer)
    market_confidence: Mapped[ConfidenceLevel]
    risk_reserve_cents: Mapped[int] = mapped_column(BigInteger)
    risk_severity: Mapped[str]
    score: Mapped[int] = mapped_column(Integer)
    recommendation: Mapped[Recommendation]
    reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
```

- [ ] **Step 5: Generate, inspect, and round-trip migration `0002`**

Run:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "add market and evaluations"
mv migrations/versions/*_add_market_and_evaluations.py migrations/versions/0002_market_and_evaluations.py
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade 0001
.venv/bin/alembic upgrade head
```

Expected: all commands exit 0; the revision creates four tables and drops them in reverse dependency order.

- [ ] **Step 6: Verify and commit market persistence**

Run: `cd backend && .venv/bin/pytest tests/db/test_evaluation_models.py -v`

Expected: passing persistence test.

```bash
git add backend/app/db/models backend/tests/db/test_evaluation_models.py backend/migrations/versions/0002_market_and_evaluations.py
git commit -m "feat: persist market evidence and evaluations"
```

---

### Task 5: Persist watchlists, alerts, inventory, tests, and jobs

**Files:**
- Create: `backend/app/db/models/operations.py`
- Modify: `backend/app/db/models/__init__.py`
- Create: `backend/tests/db/test_operations_models.py`
- Create: `backend/migrations/versions/0003_operations.py`

**Interfaces:**
- Consumes: marketplace, product, observation, and evaluation IDs.
- Produces: `WatchlistModel`, `AlertModel`, `InventoryItemModel`, `TestRunModel`, `JobRunModel`, `ExtensionPairingModel`, revision `0003`.

- [ ] **Step 1: Write the failing operations persistence test**

Create a test that persists a watchlist with include terms `['rtx 3060', '12gb']`, exclude terms `['ti', 'defekt', 'ovp']`, a 15-minute polling interval, and an enabled state. Persist an inventory item and test run, then assert the serial number, acquisition price, procedure name, duration, and measured values survive reload.

- [ ] **Step 2: Verify the missing-model failure**

Run: `cd backend && .venv/bin/pytest tests/db/test_operations_models.py -v`

Expected: FAIL during collection because `app.db.models.operations` is absent.

- [ ] **Step 3: Implement focused operations models**

Create `backend/app/db/models/operations.py` with these exact table responsibilities:

```python
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import Marketplace, ProductCategory


class WatchlistModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "watchlists"
    name: Mapped[str] = mapped_column(String(120))
    marketplace: Mapped[Marketplace]
    category: Mapped[ProductCategory]
    include_terms: Mapped[list[str]] = mapped_column(JSONB)
    exclude_terms: Mapped[list[str]] = mapped_column(JSONB, default=list)
    filters: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, default=900)
    enabled: Mapped[bool] = mapped_column(default=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "alerts"
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_snapshots.id", ondelete="CASCADE")
    )
    alert_type: Mapped[str] = mapped_column(String(40))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventoryItemModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    source_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listing_observations.id", ondelete="SET NULL")
    )
    serial_number: Mapped[str | None] = mapped_column(String(240))
    acquisition_price_cents: Mapped[int] = mapped_column(BigInteger)
    acquisition_costs: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    condition_notes: Mapped[str] = mapped_column(String(4000), default="")
    disposition: Mapped[str] = mapped_column(String(40), default="IN_STOCK")


class TestRunModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "test_runs"
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE")
    )
    procedure_name: Mapped[str] = mapped_column(String(160))
    tool_name: Mapped[str] = mapped_column(String(160))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    result: Mapped[str] = mapped_column(String(40))
    measured_values: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    notes: Mapped[str] = mapped_column(String(4000), default="")
    evidence_paths: Mapped[list[str]] = mapped_column(JSONB, default=list)


class JobRunModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "job_runs"
    idempotency_key: Mapped[str] = mapped_column(String(240), unique=True)
    job_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(120))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExtensionPairingModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "extension_pairings"
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    extension_origin: Mapped[str] = mapped_column(String(240))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- [ ] **Step 4: Generate and round-trip migration `0003`**

Run the same inspected Alembic workflow as earlier with message `add operations`, rename the revision to `0003_operations.py`, then run `upgrade head`, `downgrade 0002`, and `upgrade head`.

Expected: all six tables are created and the dependency-aware downgrade succeeds.

- [ ] **Step 5: Verify and commit operations persistence**

Run: `cd backend && .venv/bin/pytest tests/db/test_operations_models.py -v`

Expected: passing persistence test.

```bash
git add backend/app/db/models backend/tests/db/test_operations_models.py backend/migrations/versions/0003_operations.py
git commit -m "feat: persist watchlists inventory and jobs"
```

---

### Task 6: Add source-neutral immutable ingestion

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/sources.py`
- Create: `backend/app/sources/__init__.py`
- Create: `backend/app/sources/base.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/ingestion.py`
- Create: `backend/tests/services/test_ingestion.py`

**Interfaces:**
- Consumes: `RawListingModel`, `ListingObservationModel`, async session.
- Produces: `SourceEnvelope`, `SourceHealth`, `SourceAdapter`, `IngestionResult`, `IngestionService.ingest(session, envelope)`.

- [ ] **Step 1: Write failing ingestion tests**

Create `backend/tests/services/test_ingestion.py` with two behaviors:

```python
from datetime import UTC, datetime

from app.domain.enums import Marketplace
from app.schemas.sources import SourceEnvelope
from app.services.ingestion import IngestionService


def ebay_envelope(title: str = "RTX 3060 12GB") -> SourceEnvelope:
    return SourceEnvelope(
        source=Marketplace.EBAY_DE,
        external_id="v1|123|0",
        source_url="https://www.ebay.de/itm/123",
        captured_at=datetime(2026, 8, 27, tzinfo=UTC),
        title=title,
        description="tested",
        asking_price_cents=18000,
        shipping_cents=690,
        condition="Gebraucht",
        location_summary="Berlin",
        sale_format="FIXED_PRICE",
        metadata={"item_id": "v1|123|0"},
        import_method="EBAY_API",
    )


async def test_identical_payload_is_idempotent(session) -> None:
    first = await IngestionService().ingest(session, ebay_envelope())
    second = await IngestionService().ingest(session, ebay_envelope())

    assert first.created is True
    assert second.created is False
    assert second.raw_listing_id == first.raw_listing_id


async def test_changed_payload_creates_new_evidence(session) -> None:
    first = await IngestionService().ingest(session, ebay_envelope())
    changed = ebay_envelope(title="RTX 3060 12GB price drop")
    second = await IngestionService().ingest(session, changed)

    assert second.created is True
    assert second.raw_listing_id != first.raw_listing_id
```

- [ ] **Step 2: Run tests and verify missing schema/service failure**

Run: `cd backend && .venv/bin/pytest tests/services/test_ingestion.py -v`

Expected: FAIL during collection because source schemas and service do not exist.

- [ ] **Step 3: Define the source contract**

Create `backend/app/schemas/sources.py`:

```python
import uuid
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums import Marketplace


class SourceEnvelope(BaseModel):
    source: Marketplace
    external_id: str = Field(min_length=1, max_length=240)
    source_url: HttpUrl
    captured_at: datetime
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=8000)
    asking_price_cents: int = Field(ge=0)
    shipping_cents: int = Field(default=0, ge=0)
    condition: str = Field(default="", max_length=120)
    location_summary: str = Field(default="", max_length=240)
    sale_format: str = Field(default="UNKNOWN", max_length=40)
    metadata: dict[str, object] = Field(default_factory=dict)
    import_method: str = Field(max_length=40)


class SourceHealth(BaseModel):
    source: Marketplace
    healthy: bool
    checked_at: datetime
    quota_remaining: int | None = None
    error_code: str | None = None


class SourceAdapter(Protocol):
    async def discover(self) -> list[SourceEnvelope]:
        raise NotImplementedError

    async def health(self) -> SourceHealth:
        raise NotImplementedError


class IngestionResult(BaseModel):
    raw_listing_id: uuid.UUID
    observation_id: uuid.UUID
    created: bool
```

- [ ] **Step 4: Implement checksum-based ingestion**

Create `backend/app/services/ingestion.py` with canonical JSON hashing and one transaction:

```python
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.domain.enums import Condition
from app.schemas.sources import IngestionResult, SourceEnvelope


def payload_checksum(envelope: SourceEnvelope) -> str:
    payload = envelope.model_dump(mode="json", exclude={"captured_at"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class IngestionService:
    async def ingest(
        self, session: AsyncSession, envelope: SourceEnvelope
    ) -> IngestionResult:
        checksum = payload_checksum(envelope)
        existing = await session.scalar(
            select(RawListingModel).where(
                RawListingModel.source == envelope.source,
                RawListingModel.external_id == envelope.external_id,
                RawListingModel.payload_checksum == checksum,
            )
        )
        if existing is not None:
            observation = await session.scalar(
                select(ListingObservationModel).where(
                    ListingObservationModel.raw_listing_id == existing.id
                )
            )
            if observation is None:
                raise RuntimeError("raw listing exists without observation")
            return IngestionResult(
                raw_listing_id=existing.id,
                observation_id=observation.id,
                created=False,
            )

        raw = RawListingModel(
            source=envelope.source,
            external_id=envelope.external_id,
            source_url=str(envelope.source_url),
            captured_at=envelope.captured_at,
            raw_title=envelope.title,
            raw_description=envelope.description,
            asking_price_cents=envelope.asking_price_cents,
            shipping_cents=envelope.shipping_cents,
            raw_condition=envelope.condition,
            location_summary=envelope.location_summary,
            payload_checksum=checksum,
            import_method=envelope.import_method,
            raw_metadata=envelope.metadata,
        )
        session.add(raw)
        await session.flush()
        observation = ListingObservationModel(
            raw_listing_id=raw.id,
            product_id=None,
            asking_price_cents=envelope.asking_price_cents,
            shipping_cents=envelope.shipping_cents,
            condition=Condition.UNKNOWN,
            sale_format=envelope.sale_format,
            model_match_confidence_bps=0,
            flags=[],
            review_status="PENDING",
        )
        session.add(observation)
        await session.commit()
        return IngestionResult(
            raw_listing_id=raw.id,
            observation_id=observation.id,
            created=True,
        )
```

- [ ] **Step 5: Verify ingestion tests and commit**

Run: `cd backend && .venv/bin/pytest tests/services/test_ingestion.py -v`

Expected: two passing tests.

```bash
git add backend/app/schemas backend/app/sources backend/app/services/ingestion.py backend/tests/services/test_ingestion.py
git commit -m "feat: add immutable source ingestion"
```

---
### Task 7: Normalize products, variants, conditions, and review flags

**Files:**
- Create: `backend/app/domain/normalization.py`
- Create: `backend/app/services/normalization.py`
- Create: `backend/app/services/catalog_seed.py`
- Create: `backend/tests/services/test_normalization.py`

**Interfaces:**
- Consumes: `ProductAliasModel` rows represented as `NormalizationCandidate` values and raw listing text.
- Produces: `NormalizationCandidate`, `NormalizationResult`, `normalize_listing(title, description, candidates) -> NormalizationResult`, `initial_catalog() -> list[CatalogProduct]`.

- [ ] **Step 1: Write failing variant and risk-text tests**

Create `backend/tests/services/test_normalization.py`:

```python
from uuid import UUID

from app.domain.enums import Condition, ProductCategory
from app.domain.normalization import NormalizationCandidate
from app.services.normalization import normalize_listing

RTX_3060_12 = NormalizationCandidate(
    product_id=UUID("00000000-0000-0000-0000-000000000012"),
    category=ProductCategory.GPU,
    alias="rtx 3060",
    required_tokens=frozenset({"12gb"}),
    excluded_tokens=frozenset({"ti", "8gb"}),
)
RTX_3060_TI = NormalizationCandidate(
    product_id=UUID("00000000-0000-0000-0000-000000000013"),
    category=ProductCategory.GPU,
    alias="rtx 3060 ti",
    required_tokens=frozenset({"ti"}),
    excluded_tokens=frozenset(),
)


def test_exact_gpu_variant_is_resolved() -> None:
    result = normalize_listing(
        "MSI GeForce RTX 3060 12 GB Gaming X",
        "voll funktionsfähig und getestet",
        [RTX_3060_12, RTX_3060_TI],
    )

    assert result.product_id == RTX_3060_12.product_id
    assert result.condition is Condition.USED
    assert result.confidence_bps == 10000
    assert result.review_required is False


def test_defective_and_empty_box_language_blocks_resolution() -> None:
    result = normalize_listing(
        "RTX 3060 12GB OVP",
        "Nur Verpackung, Karte defekt und nicht enthalten",
        [RTX_3060_12],
    )

    assert result.condition is Condition.DEFECTIVE
    assert set(result.flags) == {"DEFECTIVE", "EMPTY_BOX_RISK"}
    assert result.review_required is True


def test_missing_variant_stays_in_review() -> None:
    result = normalize_listing("RTX 3060 Grafikkarte", "gebraucht", [RTX_3060_12])

    assert result.product_id is None
    assert "UNCLEAR_VARIANT" in result.flags
    assert result.review_required is True
```

- [ ] **Step 2: Run the tests and verify missing implementation failure**

Run: `cd backend && .venv/bin/pytest tests/services/test_normalization.py -v`

Expected: FAIL during collection because `app.domain.normalization` is absent.

- [ ] **Step 3: Define normalization input and output types**

Create `backend/app/domain/normalization.py`:

```python
from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import Condition, ProductCategory


@dataclass(frozen=True, slots=True)
class NormalizationCandidate:
    product_id: UUID
    category: ProductCategory
    alias: str
    required_tokens: frozenset[str]
    excluded_tokens: frozenset[str]


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    product_id: UUID | None
    condition: Condition
    confidence_bps: int
    flags: tuple[str, ...]
    review_required: bool
```

- [ ] **Step 4: Implement deterministic normalization**

Create `backend/app/services/normalization.py`:

```python
import re
import unicodedata
from collections.abc import Iterable

from app.domain.enums import Condition
from app.domain.normalization import NormalizationCandidate, NormalizationResult

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:gb|tb|mhz)?")
DEFECT_TERMS = {"defekt", "kaputt", "bastler", "artefakte", "funktionsunfähig"}
UNTESTED_TERMS = {"ungetestet", "ungeprüft", "keine funktionsprüfung"}
EMPTY_BOX_TERMS = {"nur ovp", "nur verpackung", "leerkarton", "nicht enthalten"}
BUNDLE_TERMS = {"bundle", "konvolut", "komplett pc", "gaming pc"}


def normalized_text(value: str) -> str:
    lowered = unicodedata.normalize("NFKC", value).lower()
    lowered = re.sub(r"(\d+)\s*(gb|tb|mhz)\b", r"\1\2", lowered)
    return " ".join(TOKEN_PATTERN.findall(lowered))


def _contains_phrase(raw_lower: str, phrases: set[str]) -> bool:
    return any(phrase in raw_lower for phrase in phrases)


def normalize_listing(
    title: str,
    description: str,
    candidates: Iterable[NormalizationCandidate],
) -> NormalizationResult:
    raw_lower = f"{title} {description}".lower()
    text = normalized_text(raw_lower)
    tokens = frozenset(text.split())
    flags: list[str] = []

    if _contains_phrase(raw_lower, DEFECT_TERMS):
        condition = Condition.DEFECTIVE
        flags.append("DEFECTIVE")
    elif _contains_phrase(raw_lower, UNTESTED_TERMS):
        condition = Condition.UNTESTED
        flags.append("UNTESTED")
    else:
        condition = Condition.USED

    if _contains_phrase(raw_lower, EMPTY_BOX_TERMS):
        flags.append("EMPTY_BOX_RISK")
    if _contains_phrase(raw_lower, BUNDLE_TERMS):
        flags.append("BUNDLE")

    matches = [
        candidate
        for candidate in candidates
        if normalized_text(candidate.alias) in text
        and candidate.required_tokens.issubset(tokens)
        and not candidate.excluded_tokens.intersection(tokens)
    ]
    blocking_text = "DEFECTIVE" in flags or "EMPTY_BOX_RISK" in flags
    if len(matches) == 1:
        return NormalizationResult(
            product_id=matches[0].product_id,
            condition=condition,
            confidence_bps=10000,
            flags=tuple(sorted(flags)),
            review_required=blocking_text,
        )

    flags.append("UNCLEAR_VARIANT")
    return NormalizationResult(
        product_id=None,
        condition=condition,
        confidence_bps=0,
        flags=tuple(sorted(set(flags))),
        review_required=True,
    )
```

- [ ] **Step 5: Seed only research-backed canonical variants**

Create `backend/app/services/catalog_seed.py` with a `CatalogProduct` dataclass and idempotent seed definitions for RTX 3060 12GB, RX 6700 XT 12GB, RTX 4060 Ti 16GB, RTX 3070 8GB, Ryzen 5 5600, Ryzen 7 5700X, Ryzen 7 5800X, Core i5-12400F, B550 ATX, B550 Mini-ITX, DDR4 32GB 3200/3600, DDR5 32GB 6000, and 1TB NVMe PCIe 4.0. Every seed must include required and excluded tokens; no seed includes a price or score.

Use this exact type:

```python
from dataclasses import dataclass

from app.domain.enums import ProductCategory


@dataclass(frozen=True, slots=True)
class CatalogProduct:
    category: ProductCategory
    manufacturer: str
    canonical_model: str
    variant: str
    attributes: dict[str, object]
    aliases: tuple[tuple[str, frozenset[str], frozenset[str]], ...]
```

Implement `initial_catalog()` as data only; these entries intentionally contain no prices or scores:

```python
def initial_catalog() -> list[CatalogProduct]:
    return [
        CatalogProduct(ProductCategory.GPU, "NVIDIA", "RTX 3060", "12GB", {"vram_gb": 12}, (("rtx 3060", frozenset({"12gb"}), frozenset({"ti", "8gb"})),)),
        CatalogProduct(ProductCategory.GPU, "AMD", "RX 6700 XT", "12GB", {"vram_gb": 12}, (("rx 6700 xt", frozenset({"12gb"}), frozenset()),)),
        CatalogProduct(ProductCategory.GPU, "NVIDIA", "RTX 4060 Ti", "16GB", {"vram_gb": 16}, (("rtx 4060 ti", frozenset({"ti", "16gb"}), frozenset({"8gb"})),)),
        CatalogProduct(ProductCategory.GPU, "NVIDIA", "RTX 3070", "8GB", {"vram_gb": 8}, (("rtx 3070", frozenset({"8gb"}), frozenset({"ti"})),)),
        CatalogProduct(ProductCategory.CPU, "AMD", "Ryzen 5 5600", "", {"socket": "AM4"}, (("ryzen 5 5600", frozenset({"5600"}), frozenset({"5600g", "5600x"})),)),
        CatalogProduct(ProductCategory.CPU, "AMD", "Ryzen 7 5700X", "", {"socket": "AM4"}, (("ryzen 7 5700x", frozenset({"5700x"}), frozenset()),)),
        CatalogProduct(ProductCategory.CPU, "AMD", "Ryzen 7 5800X", "", {"socket": "AM4"}, (("ryzen 7 5800x", frozenset({"5800x"}), frozenset({"5800x3d"})),)),
        CatalogProduct(ProductCategory.CPU, "Intel", "Core i5-12400F", "", {"socket": "LGA1700"}, (("i5 12400f", frozenset({"12400f"}), frozenset()), ("i5-12400f", frozenset({"12400f"}), frozenset()))),
        CatalogProduct(ProductCategory.MAINBOARD, "Generic", "B550", "ATX", {"socket": "AM4", "form_factor": "ATX"}, (("b550", frozenset({"atx"}), frozenset({"matx", "itx", "mini"})),)),
        CatalogProduct(ProductCategory.MAINBOARD, "Generic", "B550", "Mini-ITX", {"socket": "AM4", "form_factor": "MINI_ITX"}, (("b550", frozenset({"itx"}), frozenset({"matx", "atx"})), ("b550i", frozenset(), frozenset()))),
        CatalogProduct(ProductCategory.RAM, "Generic", "DDR4 Kit", "32GB", {"generation": "DDR4", "capacity_gb": 32, "modules": 2}, (("ddr4", frozenset({"32gb"}), frozenset({"16gb", "64gb"})),)),
        CatalogProduct(ProductCategory.RAM, "Generic", "DDR5 Kit", "32GB 6000", {"generation": "DDR5", "capacity_gb": 32, "speed_mhz": 6000}, (("ddr5", frozenset({"32gb", "6000mhz"}), frozenset({"16gb", "64gb"})),)),
        CatalogProduct(ProductCategory.SSD, "Generic", "NVMe SSD", "1TB PCIe 4.0", {"capacity_tb": 1, "interface": "PCIE_4"}, (("nvme", frozenset({"1tb", "pcie", "4"}), frozenset({"sata"})),)),
    ]
```

- [ ] **Step 6: Verify normalization and commit**

Run: `cd backend && .venv/bin/pytest tests/services/test_normalization.py -v`

Expected: three passing tests.

```bash
git add backend/app/domain/normalization.py backend/app/services/normalization.py backend/app/services/catalog_seed.py backend/tests/services/test_normalization.py
git commit -m "feat: normalize PC hardware variants safely"
```

---

### Task 8: Import comparables and estimate conservative market values

**Files:**
- Create: `backend/app/domain/market.py`
- Create: `backend/app/schemas/comparables.py`
- Create: `backend/app/sources/imports.py`
- Create: `backend/app/services/market_estimation.py`
- Create: `backend/tests/domain/test_market_estimation.py`
- Create: `backend/tests/sources/test_comparable_import.py`

**Interfaces:**
- Consumes: authorized sold or active comparable rows and canonical product IDs.
- Produces: `ComparableEvidence`, `MarketEstimate`, `MarketEstimationConfig`, `estimate_market()`, `parse_comparable_csv()`.

- [ ] **Step 1: Write failing market-estimation tests**

Create `backend/tests/domain/test_market_estimation.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.domain.enums import ComparableStatus, ConfidenceLevel, Condition
from app.domain.market import ComparableEvidence, MarketEstimationConfig
from app.services.market_estimation import estimate_market

NOW = datetime(2026, 8, 27, tzinfo=UTC)
PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000012")


def sold(index: int, price_cents: int, age_days: int = 5) -> ComparableEvidence:
    return ComparableEvidence(
        id=f"sold-{index}",
        product_id=PRODUCT_ID,
        status=ComparableStatus.SOLD,
        condition=Condition.USED,
        item_price_cents=price_cents,
        shipping_cents=690,
        occurred_at=NOW - timedelta(days=age_days),
        variant_match_confidence_bps=10000,
        observation_count=1,
        sold_through_bps=7000,
    )


def test_active_asks_do_not_change_realized_percentiles() -> None:
    evidence = [sold(index, 24000 + index * 100) for index in range(8)]
    evidence.append(
        ComparableEvidence(
            id="active-high",
            product_id=PRODUCT_ID,
            status=ComparableStatus.ACTIVE,
            condition=Condition.USED,
            item_price_cents=99900,
            shipping_cents=0,
            occurred_at=NOW,
            variant_match_confidence_bps=10000,
            observation_count=1,
            sold_through_bps=None,
        )
    )

    result = estimate_market(evidence, NOW, MarketEstimationConfig())

    assert result.expected_item_price_cents < 25000
    assert result.confidence is ConfidenceLevel.MEDIUM
    assert "active-high" not in result.comparable_ids


def test_fewer_than_eight_exact_sales_is_low_confidence() -> None:
    result = estimate_market(
        [sold(index, 24000 + index * 100) for index in range(7)],
        NOW,
        MarketEstimationConfig(),
    )

    assert result.confidence is ConfidenceLevel.LOW
```

- [ ] **Step 2: Run tests and verify the missing market module failure**

Run: `cd backend && .venv/bin/pytest tests/domain/test_market_estimation.py -v`

Expected: FAIL during collection because market domain types are absent.

- [ ] **Step 3: Define comparable and estimate types**

Create `backend/app/domain/market.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums import ComparableStatus, ConfidenceLevel, Condition


@dataclass(frozen=True, slots=True)
class ComparableEvidence:
    id: str
    product_id: UUID
    status: ComparableStatus
    condition: Condition
    item_price_cents: int
    shipping_cents: int
    occurred_at: datetime
    variant_match_confidence_bps: int
    observation_count: int
    sold_through_bps: int | None


@dataclass(frozen=True, slots=True)
class MarketEstimationConfig:
    recency_half_life_days: int = 45
    stale_after_days: int = 30
    medium_min_sales: int = 8
    medium_max_age_days: int = 180
    high_min_sales: int = 20
    high_max_age_days: int = 90


@dataclass(frozen=True, slots=True)
class MarketEstimate:
    downside_item_price_cents: int
    expected_item_price_cents: int
    optimistic_item_price_cents: int
    confidence: ConfidenceLevel
    liquidity_bps: int
    comparable_ids: tuple[str, ...]
    latest_sale_at: datetime | None
    stale: bool
```

- [ ] **Step 4: Implement robust weighted percentiles and confidence**

Create `backend/app/services/market_estimation.py` with pure helpers:

```python
import math
import statistics
from datetime import datetime

from app.domain.enums import ComparableStatus, ConfidenceLevel
from app.domain.market import ComparableEvidence, MarketEstimate, MarketEstimationConfig


def _weighted_quantile(values: list[tuple[int, float]], quantile: float) -> int:
    ordered = sorted(values, key=lambda pair: pair[0])
    target = sum(weight for _, weight in ordered) * quantile
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= target:
            return value
    return ordered[-1][0]


def _remove_outliers(evidence: list[ComparableEvidence]) -> list[ComparableEvidence]:
    if len(evidence) < 7:
        return evidence
    prices = [row.item_price_cents for row in evidence]
    median = statistics.median(prices)
    deviations = [abs(price - median) for price in prices]
    mad = statistics.median(deviations)
    if mad == 0:
        return evidence
    return [row for row in evidence if abs(row.item_price_cents - median) <= 3 * mad]


def estimate_market(
    evidence: list[ComparableEvidence],
    now: datetime,
    config: MarketEstimationConfig,
) -> MarketEstimate:
    sold = _remove_outliers([row for row in evidence if row.status is ComparableStatus.SOLD])
    if not sold:
        return MarketEstimate(0, 0, 0, ConfidenceLevel.LOW, 0, (), None, True)

    weighted: list[tuple[int, float]] = []
    for row in sold:
        age_days = max(0.0, (now - row.occurred_at).total_seconds() / 86400)
        recency = math.pow(0.5, age_days / config.recency_half_life_days)
        variant = row.variant_match_confidence_bps / 10000
        weighted.append((row.item_price_cents, recency * variant * row.observation_count))

    exact_90 = sum(
        row.observation_count
        for row in sold
        if row.variant_match_confidence_bps == 10000
        and (now - row.occurred_at).days <= config.high_max_age_days
    )
    exact_180 = sum(
        row.observation_count
        for row in sold
        if row.variant_match_confidence_bps == 10000
        and (now - row.occurred_at).days <= config.medium_max_age_days
    )
    confidence = (
        ConfidenceLevel.HIGH
        if exact_90 >= config.high_min_sales
        else ConfidenceLevel.MEDIUM
        if exact_180 >= config.medium_min_sales
        else ConfidenceLevel.LOW
    )
    liquidity_values = [row.sold_through_bps for row in sold if row.sold_through_bps is not None]
    liquidity = round(sum(liquidity_values) / len(liquidity_values)) if liquidity_values else 0
    latest = max(row.occurred_at for row in sold)
    return MarketEstimate(
        downside_item_price_cents=_weighted_quantile(weighted, 0.25),
        expected_item_price_cents=_weighted_quantile(weighted, 0.50),
        optimistic_item_price_cents=_weighted_quantile(weighted, 0.75),
        confidence=confidence,
        liquidity_bps=max(0, min(10000, liquidity)),
        comparable_ids=tuple(row.id for row in sold),
        latest_sale_at=latest,
        stale=(now - latest).days > config.stale_after_days,
    )
```

- [ ] **Step 5: Add strict CSV preview parsing**

Create `backend/app/schemas/comparables.py`:

```python
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from app.domain.enums import ComparableStatus, Condition, Marketplace


class ComparableImportRow(BaseModel):
    product_id: UUID
    source: Marketplace
    status: ComparableStatus
    condition: Condition
    currency: Literal["EUR"]
    occurred_at: AwareDatetime
    item_price_cents: int = Field(ge=0)
    shipping_cents: int = Field(default=0, ge=0)
    variant_match_confidence_bps: int = Field(ge=0, le=10000)
    observation_count: int = Field(default=1, ge=1)
    sold_through_bps: int | None = Field(default=None, ge=0, le=10000)
    source_note: str = Field(default="", max_length=500)


class ImportRowError(BaseModel):
    row_number: int
    field: str
    message: str
```

Create `backend/app/sources/imports.py`:

```python
import csv
import io

from pydantic import ValidationError

from app.schemas.comparables import ComparableImportRow, ImportRowError


def parse_comparable_csv(
    content: str,
) -> tuple[list[ComparableImportRow], list[ImportRowError]]:
    parsed: list[ComparableImportRow] = []
    errors: list[ImportRowError] = []
    reader = csv.DictReader(io.StringIO(content))
    for row_number, raw_row in enumerate(reader, start=2):
        cleaned = {key: value for key, value in raw_row.items() if key is not None}
        try:
            parsed.append(ComparableImportRow.model_validate(cleaned))
        except ValidationError as exc:
            for detail in exc.errors():
                errors.append(
                    ImportRowError(
                        row_number=row_number,
                        field=".".join(str(part) for part in detail["loc"]),
                        message=str(detail["msg"]),
                    )
                )
    return parsed, errors
```

Create `backend/tests/sources/test_comparable_import.py`:

```python
from app.domain.enums import ComparableStatus
from app.sources.imports import parse_comparable_csv


def test_csv_parser_returns_valid_rows_and_precise_errors() -> None:
    content = """product_id,source,status,condition,currency,occurred_at,item_price_cents,shipping_cents,variant_match_confidence_bps,observation_count,sold_through_bps,source_note
00000000-0000-0000-0000-000000000012,EBAY_DE,SOLD,USED,EUR,2026-08-20T10:00:00Z,24900,690,10000,1,7000,authorized export
00000000-0000-0000-0000-000000000012,EBAY_DE,SOLD,USED,EUR,2026-08-21T10:00:00Z,-1,690,10000,1,7000,invalid
"""

    rows, errors = parse_comparable_csv(content)

    assert len(rows) == 1
    assert rows[0].status is ComparableStatus.SOLD
    assert rows[0].item_price_cents == 24900
    assert [(error.row_number, error.field) for error in errors] == [
        (3, "item_price_cents")
    ]
```

- [ ] **Step 6: Verify market and import tests**

Run:

```bash
cd backend
.venv/bin/pytest tests/domain/test_market_estimation.py tests/sources/test_comparable_import.py -v
```

Expected: four passing tests.

- [ ] **Step 7: Commit market estimation**

```bash
git add backend/app/domain/market.py backend/app/schemas/comparables.py backend/app/sources/imports.py backend/app/services/market_estimation.py backend/tests/domain/test_market_estimation.py backend/tests/sources/test_comparable_import.py
git commit -m "feat: estimate conservative resale values"
```

---

### Task 9: Calculate fees, tax estimates, direct costs, and risk reserves

**Files:**
- Create: `backend/app/domain/finance.py`
- Create: `backend/tests/domain/test_finance.py`

**Interfaces:**
- Consumes: integer-cent cash flows, basis-point fee/risk values, and `TaxProfileType`.
- Produces: `FeeProfile`, `RiskInputs`, `FinancialInputs`, `FinancialResult`, `calculate_financials()`.

- [ ] **Step 1: Write failing financial tests with exact expected cents**

Create `backend/tests/domain/test_finance.py`:

```python
import pytest

from app.domain.enums import TaxProfileType
from app.domain.finance import FeeProfile, FinancialInputs, RiskInputs, calculate_financials


def test_small_business_contribution_includes_fee_vat_and_reserves() -> None:
    result = calculate_financials(
        FinancialInputs(
            resale_item_price_cents=25000,
            buyer_shipping_cents=690,
            purchase_price_cents=18000,
            outbound_shipping_cents=690,
            packaging_cents=200,
            refurbishment_cents=0,
            travel_cents=0,
            labor_cents=1000,
            advertising_cents=0,
            fee=FeeProfile(500, 45, 1900, False),
            risk=RiskInputs(500, 1000, 300, 5000, 100, 10000),
            tax_profile=TaxProfileType.SMALL_BUSINESS,
            recoverable_input_vat_cents=0,
            margin_scheme_supplier_eligible=False,
        )
    )

    assert result.platform_fee_cents == 1330
    assert result.fee_vat_cents == 253
    assert result.risk_reserve_cents == 300
    assert result.estimated_tax_cents == 0
    assert result.contribution_profit_cents == 3917


def test_margin_scheme_requires_eligible_supplier_record() -> None:
    inputs = FinancialInputs.minimum(
        resale_item_price_cents=25000,
        purchase_price_cents=18000,
        tax_profile=TaxProfileType.MARGIN_SCHEME,
    )

    with pytest.raises(ValueError, match="eligible supplier"):
        calculate_financials(inputs)
```

- [ ] **Step 2: Run tests and verify the finance module is missing**

Run: `cd backend && .venv/bin/pytest tests/domain/test_finance.py -v`

Expected: FAIL during collection because `app.domain.finance` is absent.

- [ ] **Step 3: Implement immutable financial input and output types**

Create `backend/app/domain/finance.py` with these types and no floating-point arithmetic:

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.domain.enums import TaxProfileType
from app.domain.money import apply_basis_points


@dataclass(frozen=True, slots=True)
class FeeProfile:
    platform_fee_bps: int
    fixed_fee_cents: int
    fee_vat_bps: int
    fee_vat_recoverable: bool


@dataclass(frozen=True, slots=True)
class RiskInputs:
    return_probability_bps: int
    expected_return_cost_cents: int
    defect_probability_bps: int
    expected_defect_loss_cents: int
    fraud_probability_bps: int
    expected_fraud_loss_cents: int


@dataclass(frozen=True, slots=True)
class FinancialInputs:
    resale_item_price_cents: int
    buyer_shipping_cents: int
    purchase_price_cents: int
    outbound_shipping_cents: int
    packaging_cents: int
    refurbishment_cents: int
    travel_cents: int
    labor_cents: int
    advertising_cents: int
    fee: FeeProfile
    risk: RiskInputs
    tax_profile: TaxProfileType
    recoverable_input_vat_cents: int
    margin_scheme_supplier_eligible: bool

    @classmethod
    def minimum(
        cls,
        resale_item_price_cents: int,
        purchase_price_cents: int,
        tax_profile: TaxProfileType,
    ) -> "FinancialInputs":
        return cls(
            resale_item_price_cents=resale_item_price_cents,
            buyer_shipping_cents=0,
            purchase_price_cents=purchase_price_cents,
            outbound_shipping_cents=0,
            packaging_cents=0,
            refurbishment_cents=0,
            travel_cents=0,
            labor_cents=0,
            advertising_cents=0,
            fee=FeeProfile(0, 0, 0, True),
            risk=RiskInputs(0, 0, 0, 0, 0, 0),
            tax_profile=tax_profile,
            recoverable_input_vat_cents=0,
            margin_scheme_supplier_eligible=False,
        )


@dataclass(frozen=True, slots=True)
class FinancialResult:
    sale_receipts_cents: int
    platform_fee_cents: int
    fee_vat_cents: int
    risk_reserve_cents: int
    estimated_tax_cents: int
    contribution_profit_cents: int
    roi_bps: int
```

- [ ] **Step 4: Implement the complete calculation**

Add to `backend/app/domain/finance.py`:

```python
def _risk_reserve(risk: RiskInputs) -> int:
    return (
        apply_basis_points(risk.expected_return_cost_cents, risk.return_probability_bps)
        + apply_basis_points(risk.expected_defect_loss_cents, risk.defect_probability_bps)
        + apply_basis_points(risk.expected_fraud_loss_cents, risk.fraud_probability_bps)
    )


def _rounded_ratio(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    value = Decimal(numerator) / Decimal(denominator)
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _estimated_tax(inputs: FinancialInputs, sale_receipts_cents: int) -> int:
    if inputs.tax_profile in {TaxProfileType.PRIVATE, TaxProfileType.SMALL_BUSINESS}:
        return 0
    if inputs.tax_profile is TaxProfileType.STANDARD_VAT:
        output_vat = _rounded_ratio(sale_receipts_cents * 19, 119)
        return max(0, output_vat - inputs.recoverable_input_vat_cents)
    if not inputs.margin_scheme_supplier_eligible:
        raise ValueError("margin scheme requires an eligible supplier record")
    gross_margin = max(0, sale_receipts_cents - inputs.purchase_price_cents)
    return _rounded_ratio(gross_margin * 19, 119)


def calculate_financials(inputs: FinancialInputs) -> FinancialResult:
    sale_receipts = inputs.resale_item_price_cents + inputs.buyer_shipping_cents
    platform_fee = apply_basis_points(sale_receipts, inputs.fee.platform_fee_bps)
    platform_fee += inputs.fee.fixed_fee_cents
    fee_vat = 0 if inputs.fee.fee_vat_recoverable else apply_basis_points(
        platform_fee, inputs.fee.fee_vat_bps
    )
    reserve = _risk_reserve(inputs.risk)
    tax = _estimated_tax(inputs, sale_receipts)
    direct_costs = (
        inputs.purchase_price_cents
        + inputs.outbound_shipping_cents
        + inputs.packaging_cents
        + inputs.refurbishment_cents
        + inputs.travel_cents
        + inputs.labor_cents
        + inputs.advertising_cents
    )
    profit = sale_receipts - direct_costs - platform_fee - fee_vat - reserve - tax
    roi = _rounded_ratio(profit * 10000, inputs.purchase_price_cents)
    return FinancialResult(
        sale_receipts_cents=sale_receipts,
        platform_fee_cents=platform_fee,
        fee_vat_cents=fee_vat,
        risk_reserve_cents=reserve,
        estimated_tax_cents=tax,
        contribution_profit_cents=profit,
        roi_bps=roi,
    )
```

- [ ] **Step 5: Verify calculations and commit**

Run: `cd backend && .venv/bin/pytest tests/domain/test_finance.py -v`

Expected: two passing tests with exact cent assertions.

```bash
git add backend/app/domain/finance.py backend/tests/domain/test_finance.py
git commit -m "feat: calculate complete contribution economics"
```

---

### Task 10: Solve maximum purchase price and explain recommendations

**Files:**
- Create: `backend/app/domain/scoring.py`
- Create: `backend/app/services/max_purchase.py`
- Create: `backend/tests/domain/test_scoring.py`
- Create: `backend/tests/services/test_max_purchase.py`

**Interfaces:**
- Consumes: expected/downside `FinancialResult`, market confidence, stale state, match state, liquidity, and blocking risk state.
- Produces: `EvaluationPolicy`, `GateMetrics`, `ScoreInputs`, `RecommendationInputs`, `calculate_score()`, `recommend()`, `solve_max_purchase_price()`.

- [ ] **Step 1: Write failing solver and hard-gate tests**

Create `backend/tests/services/test_max_purchase.py`:

```python
from app.domain.scoring import EvaluationPolicy, GateMetrics
from app.services.max_purchase import solve_max_purchase_price


POLICY = EvaluationPolicy(1500, 1500, 0, 2000)


def metrics(purchase_price_cents: int) -> GateMetrics:
    expected_profit = 20000 - purchase_price_cents
    downside_profit = 18000 - purchase_price_cents
    roi = (
        (2 * expected_profit * 10000 + purchase_price_cents) // (2 * purchase_price_cents)
        if purchase_price_cents
        else 10000
    )
    return GateMetrics(expected_profit, downside_profit, roi)


def test_solver_returns_highest_price_that_passes_all_gates() -> None:
    maximum = solve_max_purchase_price(25000, POLICY, metrics)

    assert metrics(maximum).passes(POLICY) is True
    assert metrics(maximum + 1).passes(POLICY) is False
```

Create `backend/tests/domain/test_scoring.py`:

```python
from app.domain.enums import ConfidenceLevel, Recommendation
from app.domain.scoring import EvaluationPolicy, RecommendationInputs, recommend


def test_low_confidence_caps_profitable_offer_at_watch() -> None:
    result = recommend(
        RecommendationInputs(
            asking_landed_cents=15000,
            maximum_purchase_price_cents=18000,
            confidence=ConfidenceLevel.LOW,
            stale=False,
            ambiguous=False,
            blocking_risk=False,
            viable_purchase_price=True,
        )
    )

    assert result is Recommendation.WATCH


def test_blocking_risk_rejects_offer_before_score() -> None:
    result = recommend(
        RecommendationInputs(15000, 18000, ConfidenceLevel.HIGH, False, False, True, True)
    )

    assert result is Recommendation.REJECT
```

- [ ] **Step 2: Run tests and verify missing scoring modules**

Run:

```bash
cd backend
.venv/bin/pytest tests/domain/test_scoring.py tests/services/test_max_purchase.py -v
```

Expected: FAIL during collection because scoring and solver modules are absent.

- [ ] **Step 3: Implement policy, gates, score normalization, and recommendation order**

Create `backend/app/domain/scoring.py`:

```python
from dataclasses import dataclass

from app.domain.enums import ConfidenceLevel, Recommendation


@dataclass(frozen=True, slots=True)
class EvaluationPolicy:
    minimum_expected_profit_cents: int
    minimum_roi_bps: int
    minimum_downside_profit_cents: int
    risk_saturation_bps: int


@dataclass(frozen=True, slots=True)
class GateMetrics:
    expected_profit_cents: int
    downside_profit_cents: int
    roi_bps: int

    def passes(self, policy: EvaluationPolicy) -> bool:
        return (
            self.expected_profit_cents >= policy.minimum_expected_profit_cents
            and self.downside_profit_cents >= policy.minimum_downside_profit_cents
            and self.roi_bps >= policy.minimum_roi_bps
        )


@dataclass(frozen=True, slots=True)
class ScoreInputs:
    expected_profit_cents: int
    roi_bps: int
    liquidity_bps: int
    confidence: ConfidenceLevel
    risk_reserve_cents: int
    expected_sale_receipts_cents: int


@dataclass(frozen=True, slots=True)
class RecommendationInputs:
    asking_landed_cents: int
    maximum_purchase_price_cents: int
    confidence: ConfidenceLevel
    stale: bool
    ambiguous: bool
    blocking_risk: bool
    viable_purchase_price: bool


def _round_positive_ratio(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return (2 * numerator + denominator) // (2 * denominator)


def _target_score(value: int, target: int) -> int:
    if target <= 0:
        return 100 if value >= 0 else 0
    if value <= 0:
        return 0
    if value <= target:
        return _round_positive_ratio(value * 50, target)
    return min(100, 50 + _round_positive_ratio((value - target) * 50, target))


def calculate_score(inputs: ScoreInputs, policy: EvaluationPolicy) -> int:
    confidence_score = {
        ConfidenceLevel.LOW: 25,
        ConfidenceLevel.MEDIUM: 65,
        ConfidenceLevel.HIGH: 100,
    }[inputs.confidence]
    saturation = max(1, policy.risk_saturation_bps)
    risk_ratio_bps = (
        _round_positive_ratio(
            inputs.risk_reserve_cents * 10000,
            inputs.expected_sale_receipts_cents,
        )
        if inputs.expected_sale_receipts_cents > 0
        else saturation
    )
    inverse_risk = max(0, 100 - _round_positive_ratio(risk_ratio_bps * 100, saturation))
    liquidity_score = max(0, min(100, _round_positive_ratio(inputs.liquidity_bps, 100)))
    weighted_numerator = (
        35 * _target_score(inputs.expected_profit_cents, policy.minimum_expected_profit_cents)
        + 20 * _target_score(inputs.roi_bps, policy.minimum_roi_bps)
        + 15 * liquidity_score
        + 15 * confidence_score
        + 15 * inverse_risk
    )
    return _round_positive_ratio(weighted_numerator, 100)


def recommend(inputs: RecommendationInputs) -> Recommendation:
    if inputs.blocking_risk or not inputs.viable_purchase_price:
        return Recommendation.REJECT
    if inputs.ambiguous or inputs.stale or inputs.confidence is ConfidenceLevel.LOW:
        return Recommendation.WATCH
    if inputs.asking_landed_cents <= inputs.maximum_purchase_price_cents:
        return Recommendation.BUY
    return Recommendation.NEGOTIATE
```

- [ ] **Step 4: Implement the monotonic integer-cent solver**

Create `backend/app/services/max_purchase.py`:

```python
from collections.abc import Callable

from app.domain.scoring import EvaluationPolicy, GateMetrics


def solve_max_purchase_price(
    upper_bound_cents: int,
    policy: EvaluationPolicy,
    evaluate: Callable[[int], GateMetrics],
) -> int:
    low = 0
    high = max(0, upper_bound_cents)
    best = -1
    while low <= high:
        candidate = (low + high) // 2
        if evaluate(candidate).passes(policy):
            best = candidate
            low = candidate + 1
        else:
            high = candidate - 1
    return best
```

- [ ] **Step 5: Add score boundary tests**

Append these cases to `backend/tests/domain/test_scoring.py` and extend its imports with `ScoreInputs`, `_target_score`, and `calculate_score`:

```python
def test_target_score_boundaries_are_integer_exact() -> None:
    assert _target_score(1000, 1000) == 50
    assert _target_score(2000, 1000) == 100
    assert _target_score(0, 1000) == 0


def test_missing_liquidity_and_saturated_risk_score_conservatively() -> None:
    policy = EvaluationPolicy(1000, 2000, 0, 2000)
    result = calculate_score(
        ScoreInputs(
            expected_profit_cents=1000,
            roi_bps=2000,
            liquidity_bps=0,
            confidence=ConfidenceLevel.LOW,
            risk_reserve_cents=2000,
            expected_sale_receipts_cents=10000,
        ),
        policy,
    )

    assert result == 31


def test_twice_target_reaches_full_profit_and_roi_components() -> None:
    policy = EvaluationPolicy(1000, 2000, 0, 2000)
    result = calculate_score(
        ScoreInputs(2000, 4000, 0, ConfidenceLevel.LOW, 0, 10000),
        policy,
    )

    assert result == 74
```

- [ ] **Step 6: Verify and commit scoring**

Run:

```bash
cd backend
.venv/bin/pytest tests/domain/test_scoring.py tests/services/test_max_purchase.py -v
```

Expected: all solver, hard-gate, normalization, and recommendation-order tests pass.

```bash
git add backend/app/domain/scoring.py backend/app/services/max_purchase.py backend/tests/domain/test_scoring.py backend/tests/services/test_max_purchase.py
git commit -m "feat: explain deal scores and maximum bids"
```

---

### Task 11: Compare complete-PC resale with part-out economics

**Files:**
- Create: `backend/app/domain/part_out.py`
- Create: `backend/tests/domain/test_part_out.py`

**Interfaces:**
- Consumes: unique component IDs, downside sale receipts, per-item fees/costs, residual loss, and complete-PC downside profit.
- Produces: `PartOutComponent`, `PartOutResult`, `evaluate_part_out()`.

- [ ] **Step 1: Write failing no-double-count and conservative-choice tests**

Create `backend/tests/domain/test_part_out.py`:

```python
import pytest

from app.domain.part_out import PartOutComponent, evaluate_part_out


def test_duplicate_component_identity_is_rejected() -> None:
    component = PartOutComponent("gpu-1", 25000, 1330, 690, 200, 500, 300)

    with pytest.raises(ValueError, match="duplicate component"):
        evaluate_part_out(4500, [component, component], 0)


def test_part_out_subtracts_every_per_item_cost() -> None:
    result = evaluate_part_out(
        complete_pc_downside_profit_cents=4500,
        components=[
            PartOutComponent("gpu-1", 25000, 1330, 690, 200, 500, 300),
            PartOutComponent("cpu-1", 9500, 520, 290, 100, 250, 100),
        ],
        residual_loss_cents=2000,
    )

    assert result.part_out_profit_cents == 28220
    assert result.selected_scenario == "PART_OUT"
```

- [ ] **Step 2: Run tests and verify missing part-out module**

Run: `cd backend && .venv/bin/pytest tests/domain/test_part_out.py -v`

Expected: FAIL during collection because `app.domain.part_out` is absent.

- [ ] **Step 3: Implement mutually exclusive scenario evaluation**

Create `backend/app/domain/part_out.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PartOutComponent:
    component_id: str
    downside_sale_receipts_cents: int
    platform_fee_cents: int
    shipping_cents: int
    packaging_cents: int
    incremental_labor_cents: int
    risk_reserve_cents: int


@dataclass(frozen=True, slots=True)
class PartOutResult:
    complete_pc_profit_cents: int
    part_out_profit_cents: int
    selected_scenario: str


def evaluate_part_out(
    complete_pc_downside_profit_cents: int,
    components: list[PartOutComponent],
    residual_loss_cents: int,
) -> PartOutResult:
    identities = [component.component_id for component in components]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate component in part-out scenario")
    part_out_profit = -residual_loss_cents
    for component in components:
        part_out_profit += (
            component.downside_sale_receipts_cents
            - component.platform_fee_cents
            - component.shipping_cents
            - component.packaging_cents
            - component.incremental_labor_cents
            - component.risk_reserve_cents
        )
    selected = (
        "PART_OUT"
        if part_out_profit > complete_pc_downside_profit_cents
        else "COMPLETE_PC"
    )
    return PartOutResult(
        complete_pc_profit_cents=complete_pc_downside_profit_cents,
        part_out_profit_cents=part_out_profit,
        selected_scenario=selected,
    )
```

- [ ] **Step 4: Verify the arithmetic and commit**

Run: `cd backend && .venv/bin/pytest tests/domain/test_part_out.py -v`

Expected: two passing tests with exact cent values.

```bash
git add backend/app/domain/part_out.py backend/tests/domain/test_part_out.py
git commit -m "feat: compare complete PC and part-out value"
```

---

### Task 12: Orchestrate and persist complete deal evaluations

**Files:**
- Create: `backend/app/services/evaluation.py`
- Create: `backend/tests/services/test_evaluation.py`

**Interfaces:**
- Consumes: `ListingObservationModel`, normalized product state, `MarketEstimate`, effective cost/risk data, and pure financial/scoring functions.
- Produces: `EvaluationService.evaluate(session, observation_id, cost_profile_id) -> EvaluationSnapshotModel`.

- [ ] **Step 1: Write a failing service test for a profitable medium-confidence offer**

Seed an observation at EUR 180 plus EUR 6.90 acquisition shipping, eight exact sold comparables near EUR 250, the small-business fee profile from Task 9, and no blocking rule. Assert the service persists one snapshot whose recommendation is `BUY`, comparable IDs contain the eight sold records, profile version equals 1, downside profit is non-negative, and reasons contain both `8 exact sold comparables` and `asking cost is within maximum purchase price`.

Use this final assertion block:

```python
assert snapshot.recommendation is Recommendation.BUY
assert len(snapshot.comparable_ids) == 8
assert snapshot.cost_profile_version == 1
assert snapshot.downside_profit_cents >= 0
assert "8 exact sold comparables" in snapshot.reasons
assert "asking cost is within maximum purchase price" in snapshot.reasons
```

- [ ] **Step 2: Run the test and verify the orchestration module is absent**

Run: `cd backend && .venv/bin/pytest tests/services/test_evaluation.py -v`

Expected: FAIL during collection because `app.services.evaluation` is absent.

- [ ] **Step 3: Implement orchestration without duplicating formulas**

Implement `EvaluationService` so it:

1. Loads the observation, raw listing, product, effective profile, effective risk rules, and sold/active comparables.
2. Refuses to evaluate a missing or ambiguous product by storing no snapshot and raising `EvaluationBlocked(code="AMBIGUOUS_PRODUCT")`.
3. Converts database records to the domain inputs from Tasks 8-10.
4. Calculates expected and downside financial results separately.
5. Solves the maximum purchase price using downside resale and all three hard financial gates.
6. Applies blocking risk evidence and stale/low-confidence caps before recommendation.
7. Calculates the ranking score independently of recommendation.
8. Stores effective versions, comparable IDs, source observations, all cash inputs, outputs, and concise reasons in one immutable snapshot transaction.

Use these exact public types:

```python
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import EvaluationSnapshotModel


@dataclass(frozen=True, slots=True)
class EvaluationBlocked(Exception):
    code: str


class EvaluationService:
    async def evaluate(
        self,
        session: AsyncSession,
        observation_id: UUID,
        cost_profile_id: UUID,
    ) -> EvaluationSnapshotModel:
        return await self._evaluate_loaded(session, observation_id, cost_profile_id)
```

The private method may be split into focused conversion helpers, but all arithmetic must call the pure functions already tested in Tasks 8-10.

- [ ] **Step 4: Add fail-closed service cases**

Add tests for ambiguous product, low comparable confidence, stale comparables, blocking risk evidence, and calculation failure. Assert respectively: no snapshot plus `AMBIGUOUS_PRODUCT`, `WATCH`, `WATCH`, `REJECT`, and no recommendation plus a diagnostic error code.

- [ ] **Step 5: Run service and domain regression tests**

Run:

```bash
cd backend
.venv/bin/pytest tests/services/test_evaluation.py tests/domain tests/services/test_max_purchase.py -v
```

Expected: all evaluation and pure-domain tests pass.

- [ ] **Step 6: Commit evaluation orchestration**

```bash
git add backend/app/services/evaluation.py backend/tests/services/test_evaluation.py
git commit -m "feat: orchestrate explainable deal evaluations"
```

---

### Task 13: Expose listing import, review, comparable, and deal APIs

**Files:**
- Create: `backend/app/schemas/deals.py`
- Create: `backend/app/api/imports.py`
- Create: `backend/app/api/review.py`
- Create: `backend/app/api/deals.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/api/test_imports.py`
- Create: `backend/tests/api/test_deals.py`

**Interfaces:**
- Consumes: `IngestionService`, `EvaluationService`, comparable CSV parser, and persistence models.
- Produces: `POST /api/v1/imports/listings`, `POST /api/v1/imports/comparables/preview`, `POST /api/v1/imports/comparables/commit`, `POST /api/v1/review/{observation_id}/resolve`, `GET /api/v1/deals`, `GET /api/v1/deals/{evaluation_id}`.

- [ ] **Step 1: Write failing API contract tests**

Create `backend/tests/api/test_imports.py` with a dependency-overridden database session and this companion payload:

```python
payload = {
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
    "import_method": "CONFIRMED_EXTENSION"
}
```

Assert the first POST returns 201 with `created: true`, the identical POST returns 200 with `created: false`, and adding an `images`, `metadata`, `seller_phone`, or `seller_email` property returns 422 because extras are forbidden. Add a second payload whose description contains an email address and German mobile number; assert the stored description contains `[REDACTED-CONTACT]` twice and neither original contact value.

Create `backend/tests/api/test_deals.py` with one persisted snapshot. Assert list output contains only its latest snapshot and detail output includes the complete input snapshot, comparable IDs, reasons, maximum price, expected/downside profit, confidence, and recommendation.

- [ ] **Step 2: Run API tests and verify route absence**

Run:

```bash
cd backend
.venv/bin/pytest tests/api/test_imports.py tests/api/test_deals.py -v
```

Expected: FAIL because both routes return 404.

- [ ] **Step 3: Define strict request and response schemas**

Create `backend/app/schemas/deals.py`:

```python
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.domain.enums import ConfidenceLevel, Recommendation


class CompanionImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["KLEINANZEIGEN_DE", "MANUAL"]
    external_id: str = Field(min_length=1, max_length=240)
    source_url: HttpUrl
    captured_at: datetime
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=8000)
    asking_price_cents: int = Field(ge=0)
    shipping_cents: int = Field(default=0, ge=0)
    condition: str = Field(default="", max_length=120)
    location_summary: str = Field(default="", max_length=240)
    sale_format: str = Field(default="CLASSIFIED_AD", max_length=40)
    import_method: Literal["CONFIRMED_EXTENSION", "MANUAL"]


class DealListItem(BaseModel):
    evaluation_id: uuid.UUID
    observation_id: uuid.UUID
    title: str
    asking_landed_cents: int
    expected_profit_cents: int
    downside_profit_cents: int
    maximum_purchase_price_cents: int
    expected_roi_bps: int
    score: int
    confidence: ConfidenceLevel
    recommendation: Recommendation
    evaluated_at: datetime


class DealDetail(DealListItem):
    source_url: HttpUrl
    input_snapshot: dict[str, object]
    comparable_ids: list[str]
    reasons: list[str]
    risk_reserve_cents: int
```

- [ ] **Step 4: Implement thin imports and review handlers**

`backend/app/api/imports.py` converts `CompanionImportRequest` to `SourceEnvelope`, sets server-owned metadata to `{}`, calls `IngestionService`, and returns status 201 for created or 200 for duplicate. Before conversion, call a focused `sanitize_import_text()` helper that replaces email and German telephone patterns in description text with `[REDACTED-CONTACT]`; apply the same helper in the manual-import path and test that harmless model numbers are unchanged. Comparable preview parses without persistence; commit accepts the exact preview rows plus a SHA-256 preview token and rejects altered rows.

`backend/app/api/review.py` accepts exactly `{product_id, condition, confirmed_flags}`. It updates only the derived observation review fields, records a user-correction audit entry in raw metadata under a new `corrections` array, and never mutates raw title, description, price, URL, or checksum.

Use router prefixes `/imports` and `/review` and explicit `response_model` values on every route.

- [ ] **Step 5: Implement latest-evaluation deal queries**

`backend/app/api/deals.py` uses a window function ordered by `EvaluationSnapshotModel.created_at DESC` partitioned by observation ID. List supports validated `recommendation`, `category`, `source`, `confidence`, `minimum_profit_cents`, and `sort` query parameters. Detail loads exactly one snapshot and returns 404 for unknown IDs.

Register all three routers in `backend/app/api/router.py`.

- [ ] **Step 6: Verify API contracts and commit**

Run:

```bash
cd backend
.venv/bin/pytest tests/api/test_imports.py tests/api/test_deals.py -v
.venv/bin/ruff check app tests/api
```

Expected: all API tests pass and Ruff reports no findings.

```bash
git add backend/app/schemas/deals.py backend/app/api/imports.py backend/app/api/review.py backend/app/api/deals.py backend/app/api/router.py backend/tests/api/test_imports.py backend/tests/api/test_deals.py
git commit -m "feat: expose imports review and deal APIs"
```

---

### Task 14: Expose watchlist, profile, risk, inventory, test, alert, and health APIs

**Files:**
- Create: `backend/app/schemas/operations.py`
- Create: `backend/app/api/watchlists.py`
- Create: `backend/app/api/settings.py`
- Create: `backend/app/api/inventory.py`
- Create: `backend/app/api/alerts.py`
- Create: `backend/app/api/source_health.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/api/test_operations.py`

**Interfaces:**
- Consumes: operations persistence models and stable enums.
- Produces: versioned CRUD endpoints required by the dashboard; no endpoint returns secret values.

- [ ] **Step 1: Write failing CRUD and secret-redaction tests**

Create `backend/tests/api/test_operations.py` with these assertions:

```python
watchlist = {
    "name": "RTX 3060 12GB Berlin",
    "marketplace": "EBAY_DE",
    "category": "GPU",
    "include_terms": ["rtx 3060", "12gb"],
    "exclude_terms": ["ti", "8gb", "defekt", "ovp"],
    "filters": {"pickup_postal_code": "10115", "pickup_radius_km": 100},
    "polling_interval_seconds": 900,
    "enabled": True
}

assert client.post("/api/v1/watchlists", json=watchlist).status_code == 201
assert client.post(
    "/api/v1/watchlists", json={**watchlist, "polling_interval_seconds": 60}
).status_code == 422
settings = client.get("/api/v1/settings").json()
assert settings["ebay_client_id"] in {"SET", "EMPTY", "MISSING"}
assert settings["ebay_client_secret"] in {"SET", "EMPTY", "MISSING"}
assert "secret_value" not in str(settings)
```

Also create an inventory item, append a test run, acknowledge an alert, and assert the source-health response includes `last_success_at`, `quota_remaining`, `stale_estimate_count`, `review_queue_count`, and `failed_job_count`.

- [ ] **Step 2: Run the tests and verify 404 failures**

Run: `cd backend && .venv/bin/pytest tests/api/test_operations.py -v`

Expected: FAIL because the operations routes are not registered.

- [ ] **Step 3: Define validated operations schemas**

In `backend/app/schemas/operations.py`, define `WatchlistCreate` with polling interval `ge=300`, `CostProfileCreate` and `RiskRuleCreate` with effective dates and monotonic version fields, `InventoryCreate` with non-negative acquisition values, and `TestRunCreate` with positive duration. Use `ConfigDict(extra="forbid")` on every write model.

Define credential status as:

```python
from enum import StrEnum


class CredentialStatus(StrEnum):
    SET = "SET"
    EMPTY = "EMPTY"
    MISSING = "MISSING"
```

- [ ] **Step 4: Implement operations routers with explicit ownership**

- `watchlists.py`: list, create, update, enable, disable, and delete watchlists.
- `settings.py`: list effective profiles/rules, create a new immutable version, and report credentials only as `SET`, `EMPTY`, or `MISSING`.
- `inventory.py`: create/list/detail inventory items and append immutable test runs.
- `alerts.py`: list unacknowledged alerts and set `acknowledged_at`.
- `source_health.py`: aggregate last successful poll, latest quota, stale estimates, review queue, and terminal job counts.

Use 404 for missing IDs, 409 for duplicate names/versions, and 422 for domain validation. Register all routers in `api/router.py`.

- [ ] **Step 5: Verify operations routes and commit**

Run:

```bash
cd backend
.venv/bin/pytest tests/api/test_operations.py -v
.venv/bin/ruff check app tests/api
```

Expected: all operations tests pass and no credential value appears in captured output.

```bash
git add backend/app/schemas/operations.py backend/app/api/watchlists.py backend/app/api/settings.py backend/app/api/inventory.py backend/app/api/alerts.py backend/app/api/source_health.py backend/app/api/router.py backend/tests/api/test_operations.py
git commit -m "feat: expose dashboard operations APIs"
```

---

### Task 15: Poll eBay through the official API with idempotent jobs

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/sources/ebay.py`
- Create: `backend/tests/sources/fixtures/ebay_search_rtx3060.json`
- Create: `backend/tests/sources/test_ebay.py`
- Create: `worker/__init__.py`
- Create: `worker/worker.py`
- Create: `worker/tasks.py`
- Create: `worker/scheduler.py`
- Create: `worker/tests/test_tasks.py`
- Modify: `backend/Dockerfile`
- Modify: `compose.yaml`

**Interfaces:**
- Consumes: `WatchlistModel`, `SourceEnvelope`, `IngestionService`, `JobRunModel`, Redis URL, and eBay application credentials.
- Produces: `EbayBrowseClient.search(watchlist) -> list[SourceEnvelope]`, Dramatiq actor `poll_ebay_watchlist(watchlist_id: str, bucket: str)`, scheduler dispatch for due enabled watchlists.

- [ ] **Step 1: Write failing eBay response-mapping and secret tests**

Create a recorded fixture containing two item summaries: one used RTX 3060 12GB fixed-price item with shipping and one defective result. Use `httpx.MockTransport` to return a token response and then the fixture.

Create `backend/tests/sources/test_ebay.py` and assert:

```python
results = await client.search(watchlist)

assert len(results) == 2
assert results[0].source is Marketplace.EBAY_DE
assert results[0].external_id == "v1|123456789|0"
assert results[0].asking_price_cents == 17999
assert results[0].shipping_cents == 690
assert results[0].import_method == "EBAY_API"
assert "client-secret" not in caplog.text
```

- [ ] **Step 2: Run the adapter test and verify missing-client failure**

Run: `cd backend && .venv/bin/pytest tests/sources/test_ebay.py -v`

Expected: FAIL during collection because `app.sources.ebay` is absent.

- [ ] **Step 3: Add typed secret settings and the official client**

Add `SecretStr | None` settings for `ebay_client_id` and `ebay_client_secret`, plus `ebay_marketplace_id: str = "EBAY_DE"`.

Create `backend/app/sources/ebay.py` with injected `httpx.AsyncClient`, cached token expiry, and these constants:

```python
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
```

The token request uses HTTP Basic auth and form data `grant_type=client_credentials` plus the scope. Search sends `Authorization: Bearer`, `X-EBAY-C-MARKETPLACE-ID: EBAY_DE`, query `q`, leaf category when configured, limit 200, and only supported filters assembled from the watchlist. Map monetary decimals through `Decimal` to integer cents using half-up rounding.

Raise typed exceptions `EbayAuthenticationError`, `EbayQuotaError`, `EbayInvalidQueryError`, and `EbayTransientError`. Exception messages contain status and eBay error IDs, never request headers or token content.

- [ ] **Step 4: Verify the adapter mapping and error taxonomy**

Add tests for HTTP 401, 429, 400, and 503 and assert their exact typed exception. Run: `cd backend && .venv/bin/pytest tests/sources/test_ebay.py -v`.

Expected: mapping, redaction, and all four error-taxonomy tests pass.

- [ ] **Step 5: Write failing worker idempotency and terminal-error tests**

In `worker/tests/test_tasks.py`, invoke the actor function directly with repository and adapter fakes. Assert two calls for the same `poll:{watchlist_id}:{bucket}` key perform discovery once; transient failures increment attempts and re-raise; authentication failures store terminal status `FAILED` with error code `EBAY_AUTH` and do not retry.

- [ ] **Step 6: Implement broker, actor, and scheduler**

`worker/worker.py` configures `dramatiq.brokers.redis.RedisBroker(url=settings.redis_url)`.

`worker/tasks.py` exposes an actor with `max_retries=5`, `min_backoff=1000`, and `max_backoff=60000`. Before external work it atomically inserts `JobRunModel.idempotency_key`; a unique conflict means successful no-op. It loads the watchlist, calls the eBay client, ingests every envelope, enqueues normalization/evaluation for created observations, updates `last_polled_at`, and stores the latest quota when available.

`worker/scheduler.py` wakes every 30 seconds, selects enabled watchlists whose interval has elapsed, calculates a UTC bucket from polling interval, and sends the actor. It never dispatches a Kleinanzeigen watchlist.

- [ ] **Step 7: Add worker and scheduler services to Compose**

Update the backend image so root `worker/` is copied to `/app/worker`. Add `worker` command `dramatiq worker.tasks` and `scheduler` command `python -m worker.scheduler`, each using the same environment and waiting on PostgreSQL/Redis health.

- [ ] **Step 8: Run adapter, worker, and regression tests**

Run:

```bash
cd backend
PYTHONPATH=.:.. .venv/bin/pytest tests/sources/test_ebay.py ../worker/tests/test_tasks.py tests/services/test_ingestion.py -v
cd ..
docker compose config --quiet
```

Expected: all tests pass and Compose configuration validates.

- [ ] **Step 9: Commit official eBay polling**

```bash
git add backend/app/core/config.py backend/app/sources/ebay.py backend/tests/sources backend/Dockerfile worker compose.yaml
git commit -m "feat: poll eBay through official API"
```

---

### Task 16: Establish the frontend shell and validated API client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/Dockerfile`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/AppShell.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/tests/setup.ts`
- Create: `frontend/tests/AppShell.test.tsx`
- Modify: `compose.yaml`

**Interfaces:**
- Consumes: versioned API responses from Tasks 13-14.
- Produces: `apiRequest<T>(path, schema, init)`, route shell for `/`, `/deals`, `/watchlists`, `/market`, `/inventory`, `/settings`, and shared status styling.

- [ ] **Step 1: Create package configuration and a failing shell test**

Create `frontend/package.json`:

```json
{
  "name": "escraper-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "test:watch": "vitest",
    "e2e": "playwright test"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.102.6",
    "react": "^19.2.8",
    "react-dom": "^19.2.8",
    "react-router-dom": "^7.18.2",
    "recharts": "^3.10.1",
    "zod": "^4.4.3"
  },
  "devDependencies": {
    "@playwright/test": "^1.62.1",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.1.0",
    "jsdom": "^27.4.0",
    "typescript": "^7.0.2",
    "vite": "^8.2.2",
    "vitest": "^4.1.11"
  }
}
```

Create `frontend/tests/AppShell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { routes } from "../src/app/router";

describe("AppShell", () => {
  it("renders every primary navigation destination", () => {
    const router = createMemoryRouter(routes, { initialEntries: ["/"] });
    render(<RouterProvider router={router} />);

    for (const label of ["Overview", "Deals", "Watchlists", "Market", "Inventory", "Settings"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});
```

- [ ] **Step 2: Install and verify the route-module failure**

Run:

```bash
cd frontend
npm install
npm test -- AppShell.test.tsx
```

Expected: FAIL because `src/app/router.tsx` is absent.

- [ ] **Step 3: Implement accessible shell and routes**

Build `AppShell` with a skip link, `<nav aria-label="Primary">`, visible active route state, a source-health summary region, `<main id="main-content">`, and responsive navigation. Route modules initially render truthful headings and loading-safe empty states; no page displays invented market numbers.

Use `createBrowserRouter` and export the same `routes` array for memory-router tests. Wrap the router in `QueryClientProvider` in `main.tsx` with one retry for GET requests and no automatic mutation retry.

- [ ] **Step 4: Implement validated API access**

Create `frontend/src/api/client.ts`:

```ts
import type { ZodType } from "zod";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new Error(`API ${response.status} for ${path}`);
  }
  return schema.parse(await response.json());
}
```

Define Zod schemas in `api/types.ts` matching health, deal list/detail, source health, watchlists, market series, profiles, inventory, and alerts. Export inferred TypeScript types from those schemas; do not duplicate interfaces by hand.

- [ ] **Step 5: Add responsive visual tokens and status semantics**

Use CSS custom properties for canvas, surface, text, muted text, borders, accent, positive, warning, danger, focus ring, spacing, radius, and shadow. Implement a readable light-first dashboard with a dark sidebar on wide screens and a compact top navigation on small screens. `StatusBadge` maps `BUY`, `NEGOTIATE`, `WATCH`, `REJECT`, and source states to text plus color; color is never the only signal.

- [ ] **Step 6: Add frontend container and Compose service**

Create `frontend/Dockerfile`:

```dockerfile
FROM node:24-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
```

Add this Compose service:

```yaml
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        VITE_API_BASE_URL: http://localhost:8000/api/v1
    ports:
      - "127.0.0.1:5173:8080"
    depends_on:
      backend:
        condition: service_started
```

- [ ] **Step 7: Verify shell tests and production build**

Run:

```bash
cd frontend
npm test -- AppShell.test.tsx
npm run build
cd ..
docker compose config --quiet
```

Expected: shell test passes, TypeScript/Vite build exits 0, and Compose validates.

- [ ] **Step 8: Commit the frontend foundation**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html frontend/Dockerfile frontend/src frontend/tests compose.yaml
git commit -m "feat: establish dashboard frontend shell"
```

---

### Task 17: Build overview, deals, and explainable deal detail

**Files:**
- Create: `frontend/src/features/overview/OverviewPage.tsx`
- Create: `frontend/src/features/deals/DealsPage.tsx`
- Create: `frontend/src/features/deals/DealDetailPage.tsx`
- Create: `frontend/src/features/deals/DealTable.tsx`
- Create: `frontend/src/features/deals/EconomicsBreakdown.tsx`
- Create: `frontend/src/features/deals/ComparableChart.tsx`
- Create: `frontend/src/components/Money.tsx`
- Create: `frontend/src/components/ConfidenceLabel.tsx`
- Modify: `frontend/src/app/router.tsx`
- Create: `frontend/tests/DealsPage.test.tsx`
- Create: `frontend/tests/DealDetailPage.test.tsx`

**Interfaces:**
- Consumes: deal list/detail, alerts, and source-health APIs.
- Produces: filtered/sorted deals and an auditable detail experience with no hidden calculations.

- [ ] **Step 1: Write failing rendered-page tests**

Mock API responses with one `NEGOTIATE` deal. Assert the deals table renders title, asking cost, expected profit, downside profit, ROI, confidence, score, maximum price, and recommendation. In detail, assert active asks and realized sales have separate headings, all cost lines are visible, and reasons include both comparable count and price boundary.

Use exact money assertions `€180.00`, `€41.00`, `€14.00`, and `€172.00` by fixing test locale to `de-DE` and currency to `EUR`.

- [ ] **Step 2: Run tests and verify missing page failures**

Run: `cd frontend && npm test -- DealsPage.test.tsx DealDetailPage.test.tsx`

Expected: FAIL because the feature modules are absent.

- [ ] **Step 3: Implement shared monetary and confidence presentation**

`Money` uses `Intl.NumberFormat("de-DE", {style: "currency", currency: "EUR"})` from integer cents. `ConfidenceLabel` renders level, exact sold-comparable count, newest sale age, and stale state. Neither component accepts preformatted values.

- [ ] **Step 4: Implement overview and deals table**

Overview renders counts for new passing candidates, negotiation opportunities, required acquisition capital, review queue, failed jobs, and stale estimates. Deals supports URL-backed filters for recommendation, category, source, confidence, minimum profit, and sort. Empty, loading, API-error, and no-filter-match states have distinct text.

- [ ] **Step 5: Implement detail economics and evidence chart**

Deal detail sections are Source Evidence, Product Match, Realized Comparables, Active Supply, Economics, Risk Reserve, Recommendation Reasons, and Evaluation History. `ComparableChart` plots realized values and active asks as distinct series and labels the downside/median lines. The 75th percentile is informational and never labeled as the target buying basis.

- [ ] **Step 6: Verify interaction and accessibility behavior**

Add tests that change a recommendation filter, sort by maximum price, navigate from row to detail, and tab through source link, filters, and table actions. Run:

```bash
cd frontend
npm test -- DealsPage.test.tsx DealDetailPage.test.tsx
npm run build
```

Expected: rendered tests and production build pass.

- [ ] **Step 7: Commit the acquisition dashboard**

```bash
git add frontend/src/features/overview frontend/src/features/deals frontend/src/components/Money.tsx frontend/src/components/ConfidenceLabel.tsx frontend/src/app/router.tsx frontend/tests/DealsPage.test.tsx frontend/tests/DealDetailPage.test.tsx
git commit -m "feat: show explainable acquisition deals"
```

---

### Task 18: Build watchlists, market, settings, inventory, and test records

**Files:**
- Create: `frontend/src/features/watchlists/WatchlistsPage.tsx`
- Create: `frontend/src/features/market/MarketPage.tsx`
- Create: `frontend/src/features/settings/SettingsPage.tsx`
- Create: `frontend/src/features/inventory/InventoryPage.tsx`
- Create: `frontend/src/features/inventory/InventoryDetailPage.tsx`
- Modify: `frontend/src/app/router.tsx`
- Create: `frontend/tests/OperationsPages.test.tsx`

**Interfaces:**
- Consumes: operations endpoints from Task 14.
- Produces: user-managed watchlists/profile versions and auditable physical inventory/test evidence.

- [ ] **Step 1: Write failing operations-page tests**

Assert that:

- Watchlist creation rejects 60 seconds and accepts 900 seconds.
- Include and exclude terms remain separate editable token lists.
- Market page displays downside, median, upper informational value, sold count, data age, active supply, and liquidity source.
- Settings displays eBay credentials only as `SET`, `EMPTY`, or `MISSING`.
- Inventory accepts serial number, acquisition cents, condition notes, and a test run with procedure/tool/duration/result/measured values/evidence paths.

- [ ] **Step 2: Run the test and verify missing page failures**

Run: `cd frontend && npm test -- OperationsPages.test.tsx`

Expected: FAIL because operations feature modules are absent.

- [ ] **Step 3: Implement watchlist and market pages**

Watchlist form uses controlled fields and submits integer radius/price/interval values. It explains that only eBay watchlists are scheduled. Market page never derives sold price from active listings and displays a `WATCH-only` callout when confidence is low or data stale.

- [ ] **Step 4: Implement versioned settings**

Settings lists effective fee/tax/risk versions, offers clone-to-new-version rather than in-place editing, and requires effective date plus reason. Credential cards show status only. Include the disclaimer: `Tax values are estimates; confirm the selected profile with a qualified adviser.`

- [ ] **Step 5: Implement inventory and test evidence**

Inventory list shows acquisition basis, accumulated costs, disposition, latest test state, and source deal when present. Detail appends immutable test runs; existing run values have no edit action. Evidence paths are displayed as local references and are never uploaded externally.

- [ ] **Step 6: Verify and commit operations UI**

Run:

```bash
cd frontend
npm test -- OperationsPages.test.tsx
npm run build
```

Expected: operations tests and build pass.

```bash
git add frontend/src/features/watchlists frontend/src/features/market frontend/src/features/settings frontend/src/features/inventory frontend/src/app/router.tsx frontend/tests/OperationsPages.test.tsx
git commit -m "feat: manage market rules and inventory evidence"
```

---

### Task 19: Add the explicit-click Kleinanzeigen companion extension

**Files:**
- Create: `extension/package.json`
- Create: `extension/tsconfig.json`
- Create: `extension/vite.config.ts`
- Create: `extension/manifest.json`
- Create: `extension/src/extract.ts`
- Create: `extension/src/pairing.ts`
- Create: `extension/src/popup.tsx`
- Create: `extension/src/popup.html`
- Create: `extension/tests/fixtures/kleinanzeigen-rtx3060.html`
- Create: `extension/tests/extract.test.ts`
- Create: `extension/tests/popup.test.tsx`
- Create: `backend/app/core/security.py`
- Create: `backend/app/api/extension.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/api/test_extension.py`

**Interfaces:**
- Consumes: the active tab DOM, explicit user action, pairing endpoint, and companion listing import API.
- Produces: `extractListing(document, url) -> ExtractedListing`, preview/edit/confirm popup, short-lived hashed pairing token, no background collection.

- [ ] **Step 1: Write failing extractor tests against a local fixture**

The fixture contains Product JSON-LD and visible title, price, condition, location, shipping, and description, plus seller name, telephone, email, and image elements. Assert:

```ts
const result = extractListing(document, "https://www.kleinanzeigen.de/s-anzeige/2971234567");

expect(result).toEqual({
  externalId: "2971234567",
  sourceUrl: "https://www.kleinanzeigen.de/s-anzeige/2971234567",
  title: "MSI GeForce RTX 3060 12GB",
  description: "Gebraucht, getestet, Abholung oder Versand.",
  askingPriceCents: 17000,
  shippingCents: 690,
  condition: "Gebraucht",
  locationSummary: "10115 Berlin",
  saleFormat: "CLASSIFIED_AD"
});
expect(JSON.stringify(result)).not.toContain("seller@example.test");
expect(JSON.stringify(result)).not.toContain("0151");
expect(JSON.stringify(result)).not.toContain("image.jpg");
```

- [ ] **Step 2: Run the extension test and verify missing extractor failure**

Run: `cd extension && npm install && npm test -- extract.test.ts`

Expected: FAIL because `src/extract.ts` is absent.

- [ ] **Step 3: Declare minimum browser permissions**

Create Manifest V3 with only `activeTab`, `scripting`, and `storage` permissions, one popup action, and host permission `http://localhost:8000/*`. Do not declare Kleinanzeigen host permissions, background service workers, webRequest, cookies, tabs, downloads, or broad URL patterns.

Add `EXTENSION_ORIGIN=` to `.env.example` and `extension_origin: str | None = None` to backend settings. Pairing stays disabled while this value is empty. After loading the unpacked extension, copy its stable generated ID into the local `.env` as the exact origin `chrome-extension://<id>`; CORS and the extension API both use that single value, never a wildcard.

- [ ] **Step 4: Implement current-document extraction**

`extractListing` first parses Product/Offer JSON-LD from the already loaded document, then uses focused visible DOM fallbacks. It performs no `fetch`, click, navigation, refresh, timer, observer, or pagination. Price parsing accepts German decimal separators and rounds to integer cents. The return type contains only the nine expected fields from the test.

- [ ] **Step 5: Write failing pairing and confirmation tests**

Assert the popup starts with `Import disabled`, obtains fields only after the user presses `Read current listing`, allows editing every extracted field, and sends only after `Confirm import`. Assert closing the popup before confirmation performs zero POSTs. Backend tests assert expired, revoked, incorrectly originated, and plaintext-token lookup attempts return 401.

- [ ] **Step 6: Implement secure local pairing and popup flow**

`backend/app/core/security.py` generates 32 random bytes, returns the URL-safe token once, stores only SHA-256, expires it after 15 minutes for initial pairing, and exchanges it for a revocable 30-day extension token. `api/extension.py` requires exact configured `chrome-extension://<id>` origin and `X-Extension-Token` before delegating to the normal import route.

`popup.tsx` has four explicit states: unpaired, ready, preview, submitting/result. It never stores listing content after submission and stores only the long-lived token in `chrome.storage.local`.

- [ ] **Step 7: Verify extension and backend security tests**

Run:

```bash
cd extension
npm test
npm run build
cd ../backend
.venv/bin/pytest tests/api/test_extension.py tests/api/test_imports.py -v
```

Expected: extractor, explicit-confirmation, pairing, origin, expiry, and redaction tests pass; extension bundle builds.

- [ ] **Step 8: Commit the companion extension**

```bash
git add extension backend/app/core/security.py backend/app/api/extension.py backend/app/api/router.py backend/tests/api/test_extension.py
git commit -m "feat: add explicit-click listing companion"
```

---

### Task 20: Harden, document, and verify the complete local MVP

**Files:**
- Create: `backend/app/core/logging.py`
- Create: `backend/tests/core/test_logging.py`
- Create: `backend/scripts/seed_demo.py`
- Create: `backend/scripts/verify_ebay.py`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/deal-flow.spec.ts`
- Create: `frontend/e2e/operations-flow.spec.ts`
- Create: `README.md`
- Modify: `compose.yaml`
- Modify: `.env.example`

**Interfaces:**
- Consumes: the complete local stack and all prior task interfaces.
- Produces: redacted structured logs, deterministic demo seed, credential-safe live eBay check, rendered critical-flow evidence, and operator documentation.

- [ ] **Step 1: Write failing redaction tests**

Create `backend/tests/core/test_logging.py` and pass a nested event containing `Authorization`, `X-Extension-Token`, `ebay_client_secret`, email, and phone values. Assert logged JSON contains `[REDACTED]` for each sensitive field and retains safe fields `source`, `job_type`, `status`, `duration_ms`, and `error_code`.

- [ ] **Step 2: Implement structured redacting logs**

Use one recursive sanitizer shared by API exception logging, eBay adapter logging, and worker job logging. Key matching is case-insensitive for authorization, cookie, token, secret, email, phone, and contact fields. Raw external descriptions and payload dictionaries are never logged.

- [ ] **Step 3: Add deterministic demo data and failing browser flows**

`seed_demo.py` inserts canonical catalog products, one effective small-business cost profile, initial research-derived risk rules, 20 sold RTX 3060 12GB comparables, one active eBay offer, one ambiguous review item, one failed job, and one inventory item with test evidence. It uses stable UUIDs and upserts by natural key.

Write Playwright flows that:

1. Open Overview and confirm source/review/failure states.
2. Filter Deals to `BUY`, open detail, and verify realized versus active evidence plus complete economics.
3. Change minimum target settings by creating a new version and observe a new evaluation snapshot.
4. Create and disable an eBay watchlist.
5. Add an inventory test run and verify it cannot be edited.

- [ ] **Step 4: Run browser tests and verify they fail before missing support is completed**

Run:

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_demo.py
cd frontend
npx playwright install chromium
npm run e2e
```

Expected on the first run: failing assertions identify any missing seeded/API/rendered behavior. Implement only the missing behavior required by those assertions, then rerun until all flows pass.

- [ ] **Step 5: Add a credential-safe eBay acceptance command**

`backend/scripts/verify_ebay.py` prints exactly these credential states without values:

```text
EBAY_CLIENT_ID=SET|EMPTY|MISSING
EBAY_CLIENT_SECRET=SET|EMPTY|MISSING
```

If either is not `SET`, exit 2 and print `LIVE_EBAY=OPEN`. If both are set, request one `RTX 3060 12GB` active result through `EbayBrowseClient`, print `LIVE_EBAY=PASS count=<n>` and exit 0, or print `LIVE_EBAY=FAIL code=<typed-code>` and exit 1. Never print request headers or response bodies.

- [ ] **Step 6: Write complete local operator documentation**

README sections are Architecture, Prerequisites, Setup, Configuration, Database Migrations, Demo Data, Tests, eBay Live Check, Companion Installation, Kleinanzeigen Boundary, Calculation Semantics, Credential Safety, Backup, Troubleshooting, and Verification Status. Document that sold data is authorized manual/CSV input and that active asks do not prove realized price.

- [ ] **Step 7: Run the complete verification matrix**

Run fresh:

```bash
cd backend
.venv/bin/ruff check app tests scripts
.venv/bin/pytest -v
cd ../frontend
npm test
npm run build
npm run e2e
cd ../extension
npm test
npm run build
cd ..
docker compose config --quiet
docker compose ps
docker compose exec backend alembic current
git diff --check
git status --short
```

Expected: all automated tests pass, both builds succeed, browser flows pass, Compose is healthy, Alembic reports head, no whitespace errors exist, and only intended task files are modified.

Run live eBay separately:

```bash
docker compose exec backend python scripts/verify_ebay.py
```

Expected: `LIVE_EBAY=PASS` only when credentials and a real API call succeed. Exit 2 is reported as open, not passed.

- [ ] **Step 8: Commit final hardening and documentation**

```bash
git add backend/app/core/logging.py backend/tests/core/test_logging.py backend/scripts frontend/playwright.config.ts frontend/e2e README.md compose.yaml .env.example
git commit -m "test: verify local flipping dashboard MVP"
```

---

## Spec coverage map

- Purpose, design decisions, scope, and non-goals: Global Constraints; Tasks 1, 13-20.
- Kleinanzeigen compliance boundary: Tasks 13 and 19; live automation remains absent.
- Repository and system architecture: Tasks 1, 3-6, 15-16.
- Core domain model: Tasks 2-5.
- Source adapter and eBay: Tasks 6, 13, 15.
- Product Research and CSV imports: Tasks 8 and 13.
- Product normalization: Task 7.
- Market estimation and confidence: Task 8.
- Financial, tax-estimate, and risk model: Tasks 9, 10, and 12.
- Complete-PC part-out: Task 11.
- Dashboard pages: Tasks 16-18.
- Background jobs: Task 15.
- Error handling and fail-closed quality: Tasks 6-15 and 20.
- Security and privacy: Tasks 1, 13-15, 19, and 20.
- Observability and auditability: Tasks 4, 5, 14, 15, and 20.
- Testing strategy and acceptance criteria: every task uses red-green verification; Task 20 runs the full matrix.
- Local operation and configuration: Tasks 1, 15, 16, and 20.
- Deferred capabilities remain absent from every task.

## Execution checkpoints

- Checkpoint A after Task 6: local backend, schema, and immutable source ingestion.
- Checkpoint B after Task 12: complete pure and persisted evaluation pipeline.
- Checkpoint C after Task 15: API surface and official eBay polling.
- Checkpoint D after Task 18: complete rendered dashboard.
- Checkpoint E after Task 20: companion, security, documentation, and acceptance evidence.
