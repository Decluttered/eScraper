# 01 — Baseline state of the eScraper scraper-related code

> Evidence-driven inventory of the eScraper backend as of HEAD
> `e58f237` on branch
> `convoy/escraper-evidence-driven-improvement-cam/5cd45cdc/gt/toast/8621414f`.
>
> Source of truth:
> `README.md`, `docs/superpowers/specs/2026-08-27-pc-hardware-flipping-dashboard-design.md`,
> `docs/superpowers/plans/2026-08-27-pc-hardware-flipping-dashboard.md`,
> `backend/`, `compose.yaml`, `.env.example`. The verbatim run logs live in
> `00-baseline-checks.md` in this directory.

## (a) Intended business workflow

From the approved spec (sections 1, 4.1, 17) the MVP answers five operational
questions per offer:

1. Which component or bundle is offered?
2. What is a defensible current resale-price range?
3. What profit remains after fees, shipping, labor, risk reserves, and tax estimate?
4. What is the highest economically justified purchase price?
5. Why does the system recommend `BUY` / `NEGOTIATE` / `WATCH` / `REJECT`?

Workflow target: configure watchlists → worker polls eBay Browse API →
observations are normalized → market comparables and finance model produce
`EvaluationSnapshot`s → dashboard surfaces deals → user decides → purchased
items are tracked in inventory with test evidence → sold results feed the
feedback loop. eScraper **buys, bids, messages, and publishes nothing**.

## (b) Supported markets and search modes

Currently in code:

- **Currency:** only `Currency.EUR` (single value, integer cents).
- **Marketplace enum:** `EBAY_DE`, `KLEINANZEIGEN_DE`, `MANUAL` — declared,
  but no source adapter or ingestion path uses them yet.
- **ProductCategory:** `GPU, CPU, MAINBOARD, RAM, SSD, PSU, CASE, COOLER,
  COMPLETE_PC, OTHER`.
- **Condition:** `USED, REFURBISHED, UNTESTED, DEFECTIVE, UNKNOWN`.
- **ComparableStatus:** `ACTIVE, SOLD`.
- **TaxProfileType:** `PRIVATE, SMALL_BUSINESS, STANDARD_VAT, MARGIN_SCHEME`.

Marketplace value used in `.env.example` is `EBAY_DE`, which matches the spec.
**No search / polling / Browse API code exists yet.** The "search input → eBay
result collection" step is not implemented; the only end-to-end capability is
`GET /api/v1/health`.

## (c) Adapter strategy

| Channel | Status | Evidence |
| --- | --- | --- |
| Official eBay Browse API (OAuth + search) | **missing** | no `backend/app/sources/ebay.py`; `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` declared in `.env.example` but unused by any module |
| Kleinanzeigen companion extension | **missing** | no `extension/` directory; spec keeps it explicitly *absent* until permission is documented |
| Kleinanzeigen automated Playwright scraper | **explicitly out of scope** | spec §5; plan task 12+; no Playwright dependency in `pyproject.toml` |
| CSV / Product Research comparable import | **missing** | no `backend/app/sources/imports.py`; no `backend/app/schemas/`; no `backend/app/services/` |
| HTTP scraping (requests/httpx against eBay HTML) | **missing** | `httpx` is a declared dependency, but no source adapter uses it |
| Fixture-driven tests | **missing for scraper** | only Health/Money/Enums fixture-style tests exist; nothing exercises a fake `EbaySourceAdapter` |

The only HTTP client in the dependency graph is `httpx`, declared but
unconsumed.

## (d) Pipeline stages — present / stubbed / missing

The spec (§7, §12–15) defines an eight-stage pipeline: search input → eBay
result collection → field extraction → normalization → dedup → filtering →
value/margin estimation → opportunity scoring → ranking → output/persistence.
We map each stage to what is in the repo today:

| # | Stage | Status | Where / evidence |
| --- | --- | --- | --- |
| 1 | Search input (watchlists / CSV / Kleinanzeigen) | **missing** | no `watchlists/` routes; `WatchlistModel` exists in DB but is never created or polled |
| 2 | eBay result collection (Browse API polling) | **missing** | no `sources/ebay.py`, no worker, no Dramatiq code despite `dramatiq[redis]` in deps |
| 3 | Field extraction (raw → envelope) | **missing** | no extraction logic; `RawListingModel` only exists as a DB row |
| 4 | Normalization (canonical product, variant, condition, confidence) | **missing** | spec §12; `ProductCategory` and `Condition` enums exist, but no tokenizer, no alias matcher, no `NormalizationResult` |
| 5 | Dedup | **partial / passive** | `RawListingModel` declares `UniqueConstraint("source", "external_id", "payload_checksum")` so the DB will refuse duplicates, but the service that actually computes the checksum and inserts the row is **not implemented** |
| 6 | Filtering (sold-vs-active, confidence, ambiguity) | **missing** | spec §15 hard-gate logic absent; no `Recommendation` derivation in code |
| 7 | Value / margin estimation (downside / expected / optimistic percentiles, fees, tax) | **missing** | no `domain/finance.py`, no `services/market_estimation.py`, no `max_purchase.py` |
| 8 | Opportunity scoring (5-component weighted score) | **missing** | no `domain/scoring.py`; only the `EvaluationSnapshotModel` row schema exists |
| 9 | Ranking & output / persistence (EvaluationSnapshot, dashboard, alerts) | **partial** | `EvaluationSnapshotModel` + the three Alembic revisions are committed. No service writes to them. The FastAPI app exposes no deal / ranking endpoint |
| – | Background worker (Dramatiq / Redis) | **missing** | `dramatiq[redis]` and `redis` are pinned in `pyproject.toml` but no `worker/` directory, no `tasks.py`, no broker bootstrap |
| – | Frontend (React + TanStack Query + Vite) | **missing** | no `frontend/` directory |
| – | Companion extension (Chrome MV3, active-tab only) | **missing** | no `extension/` directory |
| – | Inventory + test runs UI | **missing** | models exist, no service or API |

## (e) Profit / fee / shipping / confidence formulas

The spec defines the following. **None are implemented in code yet**, but they
are the contract that later iterations will exercise.

### Sale receipts → contribution profit (spec §14)

```text
sale receipts
- purchase price
- platform and payment fees
- outbound shipping and packaging
- refurbishment parts
- travel cost
- valued labor
- advertising and listing costs
- estimated tax
- expected return, defect, and fraud reserve
= expected contribution profit
```

### Platform fee (spec §14)

"Follows the effective fee profile rather than assuming that only the item
price is charged. Fee rules are versioned by marketplace, category, item
condition, seller status, and effective date." A single hard-coded 11.5% is
**explicitly rejected** (spec §3).

### Risk reserve (spec §14)

```text
return probability * expected return cost
+ latent-defect probability * expected loss given defect
+ fraud probability * expected loss given fraud
```

### Maximum purchase price (spec §14.2)

"The highest price at which all configured gates still pass using the downside
resale value. It is solved against the complete financial model because fee and
tax estimates may depend on the purchase or sale amount."

Defaults: minimum expected contribution EUR 15.00, minimum expected ROI 15 %,
minimum downside contribution EUR 0.00. Money is integer cents; percentages
are integer basis points (`10000 bps = 100 %`).

### Confidence (spec §13.3)

- **HIGH:** at least 20 exact sold comparables in the last 90 days.
- **MEDIUM:** at least 8 in the last 180 days.
- **LOW:** fewer, related variants, or active-listing-only → recommendation
  capped at `WATCH`.

### Ranking score (spec §15)

| Weight | Component | Initial normalization |
| --- | --- | --- |
| 35 % | expected absolute contribution profit | 0/50/100 anchors at ≤ 0, minimum, 2 × minimum |
| 20 % | expected ROI | same anchors |
| 15 % | liquidity | sold-through % (0–100), else 0 |
| 15 % | comparable-data confidence | LOW=25, MEDIUM=65, HIGH=100 |
| 15 % | inverse expected risk | 0 reserve → 100, 20 %+ reserve → 0 |

### Hard gates (spec §15)

`BUY` is impossible if any of these is true: downside profit below minimum;
expected profit or ROI below minimum; product or variant ambiguous; market
confidence LOW; blocking risk rule lacks evidence; landed cost > max price.

The only formula that *is* implemented is the tiny integer-cent / basis-point
helper `apply_basis_points` in `backend/app/domain/money.py:11-14`:

```python
def apply_basis_points(cents: int, basis_points: int) -> int:
    if not isinstance(cents, int) or not isinstance(basis_points, int):
        raise TypeError("amount and rate must use integers")
    return _round_decimal(Decimal(cents) * Decimal(basis_points) / Decimal(10_000))
```

plus `Money` arithmetic in `backend/app/domain/money.py:17-36` and the
stable enums in `backend/app/domain/enums.py:1-57`.

## (f) Install / test / exec commands (documented)

From `README.md` and `backend/pyproject.toml`:

```text
# Setup (Host, PowerShell examples from README; Linux equivalents are equivalent)
cp .env.example .env                # create local env (gitignored)
docker compose up -d --build        # start postgres, redis, backend
docker compose ps                   # verify health
curl http://127.0.0.1:8000/api/v1/health   # expect {"status":"ok"}
# OpenAPI UI: http://127.0.0.1:8000/docs

# Backend without Docker (host)
cd backend
python -m venv .venv
source .venv/bin/activate            # or .venv\Scripts\Activate.ps1 on Windows
pip install -e ".[dev]"              # currently fails (see baseline checks)
ruff check app tests
pytest -v

# Migrations (planned, README §"Datenbank-Migrationen")
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current

# Live eBay acceptance (planned)
docker compose exec backend python scripts/verify_ebay.py
```

What actually works today, as captured in `00-baseline-checks.md`:

- `python3 -c "from app.main import create_app; print(create_app)"` → exit 0
- `python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000` →
  `GET /api/v1/health` returns `{"status":"ok"}` HTTP 200 (see OpenAPI
  with the single path `/api/v1/health`)
- `python3 -m ruff check app tests` → "All checks passed!", exit 0
- `python3 -m pytest -v --ignore=tests/db` → 5 passed (Money, Enums, Health)
- `python3 -m pytest -v` → 5 passed + 4 ERROR (DB tests cannot connect)
- `python3 -m alembic history` → three revisions; `alembic upgrade head`
  cannot run (no PostgreSQL)

What does **not** run in this container: `docker compose …`, `alembic upgrade
head` (no DB), `mypy` (not configured anywhere), the full backend test
suite (no DB), and any eBay Browse API call (no adapter and no credentials).

## (g) Required vs optional credentials

From `.env.example` and `backend/app/core/config.py:7-15`:

| Variable | Required? | Used by | Notes |
| --- | --- | --- | --- |
| `DATABASE_URL` | required by `compose.yaml` and the app `Settings` default | `app/core/config.py`, `app/db/session.py` (via the engine) | `postgresql+asyncpg://escraper:escraper@…/escraper`; health endpoint does not need it |
| `REDIS_URL` | optional today | `Settings` only; no consumer in code | reserved for the planned Dramatiq worker; health and current tests do not need it |
| `FRONTEND_ORIGIN` | optional | CORS middleware in `app/main.py:14-17` | defaults to `http://localhost:5173`; only matters once a frontend is added |
| `LOG_LEVEL` | optional | `Settings` (no logging module is wired yet) | default `INFO` |
| `EBAY_CLIENT_ID` | optional / *geplant* | none in code; declared in `.env.example` empty by default | "leave empty until integration exists" per README |
| `EBAY_CLIENT_SECRET` | optional / *geplant* | none in code; declared in `.env.example` empty by default | "never commit", per README |
| `EBAY_MARKETPLACE_ID` | optional | none in code; default `EBAY_DE` | reserved |

**For the health check and the existing no-DB tests, no credentials and no
services are required.** For the DB tests, PostgreSQL on `localhost:5432`
with `escraper/escraper/escraper_test` is needed (see
`backend/tests/db/conftest.py:9-12`).

## (h) End-to-end pipeline map (current vs target)

```text
# Target (spec §7)
React dashboard
   |
Versioned FastAPI HTTP API
   |
   +-- Source adapters
   |     +-- eBay Browse API
   |     +-- Confirmed companion import
   |     +-- CSV and comparable import
   |
   +-- Product normalization
   +-- Market estimation
   +-- Financial evaluation
   +-- Risk rules and recommendation
   +-- Inventory and test records
   |
PostgreSQL system of record
   |
Redis queue <--> Python worker
```

```text
# Today (Slice 1 + merged persistence slices)
React dashboard                       (missing)
   |
Versioned FastAPI HTTP API           (1 path: /api/v1/health)
   |
   +-- Source adapters               (missing — no backend/app/sources/)
   +-- Product normalization         (missing)
   +-- Market estimation             (missing)
   +-- Financial evaluation          (missing)
   +-- Risk rules and recommendation (missing)
   +-- Inventory and test records    (DB models present, no service / API)
   |
PostgreSQL system of record          (compose + Alembic env + 3 migrations; no live DB)
   |
Redis queue <--> Python worker       (no worker, no tasks)
```

The pieces that are present are: the FastAPI app factory and CORS, the
Pydantic `Settings`, the `HealthResponse` model, the SQLAlchemy `Base` /
`IdMixin` / `TimestampMixin`, the `Product`, `ProductAlias`,
`RawListing`, `ListingObservation`, `MarketComparable`, `CostProfile`,
`RiskRule`, `EvaluationSnapshot`, `Watchlist`, `Alert`,
`InventoryItem`, `TestRun`, `JobRun`, `ExtensionPairing` models, three
Alembic revisions creating the corresponding tables, the `compose.yaml`
service definitions, the `.env.example`, and tests for Health / Money / Enums
plus DB persistence tests for each model group (currently unable to execute
without a live PostgreSQL).

## File inventory used for this analysis

```text
backend/app/
app/__init__.py
app/api/__init__.py
app/api/health.py
app/api/router.py
app/core/__init__.py
app/core/config.py
app/db/__init__.py
app/db/base.py
app/db/models/__init__.py
app/db/models/evaluation.py
app/db/models/listing.py
app/db/models/market.py
app/db/models/operations.py
app/db/models/product.py
app/db/session.py
app/domain/__init__.py
app/domain/enums.py
app/domain/money.py
app/main.py

backend/tests/
tests/db/conftest.py
tests/db/test_evaluation_models.py
tests/db/test_listing_models.py
tests/db/test_operations_models.py
tests/domain/test_enums.py
tests/domain/test_money.py
tests/test_health.py

backend/migrations/
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/0001_products_and_listings.py
backend/migrations/versions/0002_market_and_evaluations.py
backend/migrations/versions/0003_operations.py
```

Note that `backend/app/` does **not** contain any of: `services/`,
`sources/`, `schemas/`, or `domain/market.py`, `domain/finance.py`,
`domain/scoring.py`, `domain/part_out.py`, `domain/normalization.py`. No
Python file imports `requests`, `playwright`, `selenium`, `scrapy`, or
`lxml`. The only eBay string in the codebase appears in
`backend/app/db/models/product.py` (column `ebay_product_id`, never
populated) and in a few test URLs.
