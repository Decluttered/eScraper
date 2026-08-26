# PC Hardware Flipping Dashboard - Design Specification

**Date:** 2026-08-27

**Status:** Approved design, pending written-spec review

**Project:** eScraper

**Operating model:** Local-first, single-user application for Germany

## 1. Purpose

This document specifies the first usable foundation for a dashboard that discovers, normalizes, evaluates, and tracks used gaming-PC component offers in Germany.

The system answers five operational questions:

1. What exact component or component bundle is being offered?
2. What is a defensible current resale-price range?
3. What profit remains after all direct, platform, tax-estimate, labor, and risk costs?
4. What is the highest economically justified purchase price?
5. Why does the system recommend `BUY`, `NEGOTIATE`, `WATCH`, or `REJECT`?

The application is a decision-support tool. It does not buy items, contact sellers, place bids, publish sales listings, or provide binding legal or tax advice.

## 2. Design decisions

The approved design uses a modular monolith:

- React and TypeScript frontend
- FastAPI Python backend
- PostgreSQL as the system of record
- Redis-backed background job processing
- Separate Python worker process
- A user-triggered browser companion extension
- Docker Compose for local operation

Python is used for normalization, price statistics, financial calculations, and future model-assisted classification. Frontend and backend communicate through a versioned HTTP API.

The application is local-first and single-user in the MVP. Public hosting, multi-user access, and mobile applications are outside this specification.

## 3. Research assessment and corrected assumptions

The supplied market research is treated as a set of useful hypotheses, not as a static price catalog.

The following themes are retained as configurable signals:

- VRAM capacity, CUDA suitability, gaming performance, and power demand affect GPU liquidity.
- AM4 upgrade components and Mini-ITX boards may have attractive liquidity.
- Intel desktop CPUs from the 13th and 14th generations require elevated risk treatment.
- Part-out opportunities can outperform complete-system resale.
- Component-specific inspection and test evidence affects expected loss.
- Windows 11 compatibility affects the resale prospects of older platforms.

The following research assumptions must not be hard-coded:

- Example purchase and sale prices are not current market truth.
- A fixed 11.5 percent eBay fee is not valid for every account, category, condition, or date.
- A subjective 1-100 score without source evidence is not sufficient for a purchase decision.
- Active asking prices are not equivalent to realized sale prices.
- SSD health percentages are not exact universal remaining-life measurements.
- A short benchmark cannot prove long-term component reliability.
- Difference taxation does not apply merely because the seller operates commercially.

Authoritative references used to correct the assumptions:

- eBay business seller fees: https://www.ebay.de/help/selling/fees-credits-invoices/gebhren-fr-gewerbliche-verkufer-die-der-zahlungsabwicklung-teilnehmen?id=4809
- eBay Product Research: https://www.ebay.de/help/selling/selling-tools/terapeak-recherche?id=4853
- eBay Browse API: https://developer.ebay.com/develop/api/buy
- eBay Marketplace Insights restriction: https://developer.ebay.com/api-docs/buy/static/ref-buy-browse-filters.html
- Kleinanzeigen terms: https://themen.kleinanzeigen.de/nutzungsbedingungen/
- German VAT Act section 25a: https://www.gesetze-im-internet.de/ustg_1980/__25a.html
- German Civil Code section 476: https://www.gesetze-im-internet.de/bgb/__476.html
- Intel Vmin Shift guidance: https://www.intel.com/content/www/us/en/support/articles/000102331/processors.html
- Windows 10 end of support: https://support.microsoft.com/en-US/Windows/Deployment/Updates-Lifecycle/windows-10-support-has-ended-on-october-14-2025
- Windows 11 supported AMD processors: https://learn.microsoft.com/en-us/windows-hardware/design/minimum/supported/windows-11-supported-amd-processors
- NVMe drive-life definition: https://nvmexpress.org/wp-content/uploads/NVM-Express-Management-Interface-Specification-Revision-2.0-2024.08.05-Ratified.pdf

## 4. Scope

### 4.1 MVP capabilities

The MVP shall provide:

- eBay active-listing polling through the official Browse API
- Manual market-comparable imports derived from eBay Product Research
- CSV import for research data and user-owned observations
- User-triggered import of one currently open Kleinanzeigen listing
- Canonical product and variant normalization
- Immutable listing observations and evaluation snapshots
- Configurable cost, fee, tax-estimate, labor, and risk profiles
- Conservative market-price ranges
- Expected and downside profit calculations
- Maximum justified purchase-price calculation
- Explainable recommendations and ranking scores
- Watchlists and in-application alerts
- Basic inventory and test-record tracking for purchased items
- Source health, data freshness, and job-failure visibility

### 4.2 Explicit non-goals

The MVP shall not provide:

- Automated Kleinanzeigen browsing, polling, pagination, or background collection
- CAPTCHA solving, anti-bot bypass, stealth automation, or login automation
- Automatic purchasing, bidding, negotiation, or seller messaging
- Automatic eBay sales listing publication
- Seller contact-data collection
- Image copying from Kleinanzeigen
- Automated benchmark execution on attached hardware
- Machine-learning price prediction
- Public internet exposure or multi-user authorization
- Binding tax, legal, warranty, or accounting determinations

## 5. Compliance boundary for Kleinanzeigen

Kleinanzeigen prohibits automated crawlers, scrapers, and other automated collection mechanisms without express written consent. Tool choice does not change this boundary.

The MVP browser extension is therefore a companion import tool, not a crawler:

- It operates only in the active tab opened by the user.
- It runs only after an explicit user click.
- It does not navigate, paginate, poll, refresh, or schedule requests.
- It does not automate login or bypass access restrictions.
- It extracts only the minimum fields required for evaluation.
- It displays a preview that the user must confirm or edit.
- It does not transfer seller contact details or listing images.
- It sends data only to the paired local backend.

The supported fields are source URL, external listing identifier when visible, title, asking price, condition text, location summary, shipping or pickup option, description text selected for product identification, and capture time.

A future automated Playwright connector may implement the same source-adapter contract only after the user has documented express permission from Kleinanzeigen. It remains absent and disabled in the MVP.

## 6. Repository layout

The intended repository structure is:

```text
eScraper/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── domain/
│   │   ├── services/
│   │   └── sources/
│   ├── migrations/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   └── routes/
│   └── tests/
├── worker/
│   ├── jobs/
│   └── tests/
├── extension/
│   ├── src/
│   └── tests/
├── docs/
│   └── superpowers/
│       └── specs/
├── compose.yaml
└── README.md
```

The backend owns domain rules and persistence. The worker imports backend domain and service modules rather than duplicating evaluation logic.

## 7. System architecture

```text
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

Every externally obtained listing is stored first as an immutable raw observation. Domain processing creates derived records and immutable evaluation snapshots. Reprocessing never overwrites the evidence used by an earlier decision.

## 8. Core domain model

All primary keys use UUIDs. Monetary values use integer cents. Percentages and rates use integer basis points. Timestamps are stored in UTC. Marketplace and currency are explicit fields, initially `EBAY_DE`, `KLEINANZEIGEN_DE`, and `EUR`.

### 8.1 Product

Represents a canonical hardware item or supported bundle definition.

Key fields:

- category: GPU, CPU, MAINBOARD, RAM, SSD, PSU, CASE, COOLER, COMPLETE_PC, OTHER
- manufacturer
- canonical model
- variant
- identifiers such as EAN, MPN, and eBay product ID when known
- structured attributes by category
- Windows 11 compatibility status where applicable
- normalization aliases

Category-specific attributes include GPU VRAM and chip model, CPU socket and generation, mainboard chipset and form factor, RAM generation/capacity/module count/speed, and SSD capacity/interface.

### 8.2 RawListing

Stores the received source payload or confirmed manual import without later mutation.

Key fields:

- source and external identifier
- source URL
- capture timestamp
- raw title and selected description
- raw monetary and location fields
- raw condition
- payload checksum
- import method

### 8.3 ListingObservation

Represents normalized facts about a listing at a point in time.

Key fields:

- raw listing reference
- product reference or review-required status
- normalized asking price and shipping
- normalized condition
- sale format
- seller type when supplied by an authorized source
- model-match confidence
- flags such as defective, bundle, empty-box risk, pickup-only, or unclear variant

### 8.4 MarketComparable

Represents an active or realized comparable observation.

Key fields:

- product and condition
- listing or aggregate source
- active versus sold status
- realized item price and shipping when known
- observation or sale date
- geographic market
- variant-match confidence
- source-quality level

### 8.5 CostProfile

An effective-dated configuration containing:

- platform percentage and fixed fees
- fee VAT recoverability behavior
- listing and advertising costs
- outbound and return shipping assumptions
- packaging cost
- travel cost
- refurbishment parts
- labor hourly rate and expected minutes by category
- minimum expected profit
- minimum ROI
- minimum downside profit
- risk reserve defaults
- tax-estimate profile

### 8.6 RiskRule

An effective-dated, structured rule with category, matching facts, severity, evidence requirement, reserve adjustment, recommendation cap, and explanation.

Research-derived initial rule candidates include:

- Elevated Intel 13th/14th generation desktop CPU risk without suitable invoice and warranty evidence
- Unknown ex-mining GPU history
- Used AIO or custom liquid cooling
- Modular PSU with missing or unverified original cables
- SSD with weak or missing health evidence
- Mainboard socket-pin or VRM damage indicators
- GPU artifact, hotspot, fan, or PCB damage indicators

These are editable rules, not permanent universal facts.

### 8.7 EvaluationSnapshot

Stores all inputs, rule versions, results, and explanations for one evaluation.

Key outputs:

- downside, expected, and optimistic resale prices
- expected and downside contribution profit
- expected ROI
- maximum justified purchase price
- liquidity estimate
- data confidence
- risk reserve and risk severity
- ranking score
- recommendation
- human-readable reason list

### 8.8 InventoryItem and TestRun

Tracks purchased hardware, acquisition costs, serial number, documented condition, refurbishment spend, test evidence, disposition, and eventual sale result.

TestRun stores the named procedure, tool, duration, configuration, result, measured values, notes, and evidence-file references. The MVP records test results; it does not execute benchmarks automatically.

## 9. Source adapter contract

Every source adapter implements three concerns:

1. Discover or accept source records.
2. Convert them to a source-neutral raw-listing envelope.
3. Report source health, rate-limit state, and recoverable errors.

Adapters never calculate market values or recommendations.

The source-neutral envelope contains source, external ID, URL, captured time, title, description subset, price, shipping, condition, location summary, sale format, and raw metadata.

## 10. eBay integration

The eBay connector uses the official Browse API with application credentials supplied by the user's eBay Developer account.

It shall:

- Search active German marketplace listings for configured watchlists.
- Apply supported category, condition, price, location, and purchase-format filters.
- Respect API quotas and response rate-limit information.
- Persist the external item ID and a checksum for deduplication.
- Create a new observation only when relevant listing data changes.
- Retry transient failures with bounded exponential backoff.
- Mark authentication and quota errors as visible source-health failures.

The Browse API does not serve as proof of realized sale price. Actual sold comparables enter through Product Research-derived manual or CSV import. The UI labels active asks and realized sales separately.

## 11. Product Research and CSV imports

The user can enter aggregate Product Research values or import a structured CSV prepared from data they are authorized to use.

Supported comparable fields are:

- canonical product or matching identifiers
- condition
- marketplace
- sale date or aggregate date range
- realized item price
- realized shipping
- number of observations for aggregate rows
- sales rate when available
- source note

Imports are previewed and validated before persistence. Invalid currency, ambiguous product mapping, impossible dates, or missing realized prices are rejected with row-level explanations.

## 12. Product normalization

Normalization is deterministic first and review-driven when ambiguous.

The pipeline performs:

1. Text cleanup and token normalization.
2. Category detection.
3. Manufacturer and model alias matching.
4. Variant extraction.
5. Condition and defect-language extraction.
6. Bundle and empty-box detection.
7. Confidence calculation.
8. Exact match, review-required, or unsupported classification.

Examples that must remain distinct include:

- RTX 3060 12 GB versus RTX 3060 8 GB
- RTX 3060 versus RTX 3060 Ti
- Ryzen 5 5600 versus Ryzen 5 5600G or 5600X
- B550 ATX versus B550 Mini-ITX
- DDR5-6000 CL30 versus DDR5-6000 with unknown latency
- Working versus defective or untested condition

An ambiguous listing cannot receive `BUY`. A user correction creates an alias suggestion without rewriting the original listing.

## 13. Market-value estimation

### 13.1 Comparable priority

Evidence priority is:

1. Recent realized sales with exact variant and comparable condition
2. Older realized sales with exact variant and comparable condition
3. Realized sales with a close but explicitly discounted match
4. Active exact-match listings
5. User-entered estimate

Active asking prices describe supply and competition. They do not become realized prices.

### 13.2 Statistical method

For realized comparable samples:

- Normalize item price and shipping separately.
- Weight exact variants above related variants.
- Weight equivalent conditions above weaker matches.
- Apply recency weighting with a configurable half-life, initially 45 days.
- Remove extreme outliers using a median-absolute-deviation rule when at least seven observations exist.
- Calculate weighted 25th, 50th, and 75th percentiles.

The 25th percentile is the downside or quick-sale value. The weighted median is the expected value. The 75th percentile is informational and is never used to justify the maximum purchase price.

### 13.3 Confidence levels

Initial deterministic confidence rules are:

- High: at least 20 exact sold comparables in the last 90 days
- Medium: at least 8 exact sold comparables in the last 180 days
- Low: fewer than 8 exact sold comparables, related-variant dependence, or active-listing-only evidence

Low confidence caps the recommendation at `WATCH` regardless of the ranking score.

The thresholds are effective-dated configuration and may be calibrated from actual outcomes.

## 14. Financial model

The calculation separates observable cash flows from estimated reserves and tax treatment.

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

The platform fee base follows the effective fee profile rather than assuming that only the item price is charged. Fee rules are versioned by marketplace, category, item condition, seller status, and effective date.

The risk reserve is:

```text
return probability * expected return cost
+ latent-defect probability * expected loss given defect
+ fraud probability * expected loss given fraud
```

Category defaults are editable and later calibrated from the user's own inventory and sales outcomes.

### 14.1 Tax-estimate profiles

The system provides distinct estimate profiles for:

- Private scenario
- Small-business scenario
- Standard VAT scenario
- Margin-scheme scenario under section 25a UStG

The margin-scheme profile is selectable only when the acquisition record includes a compatible supplier-tax classification. Required purchase, sale, and assessment-basis records are retained.

Every tax result is labeled as an estimate. The system does not determine the user's legal status or replace professional advice.

### 14.2 Maximum purchase price

The maximum justified purchase price is the highest price at which all configured gates still pass using the downside resale value. It is solved against the complete financial model because fee and tax estimates may depend on the purchase or sale amount.

Initial configurable defaults are:

- Minimum expected contribution profit: EUR 15.00
- Minimum expected ROI: 15 percent
- Minimum downside contribution profit: EUR 0.00

Category-specific overrides are supported.

## 15. Risk gates, score, and recommendation

Hard gates run before ranking.

An offer cannot receive `BUY` when any of these conditions applies:

- Downside profit is below the configured minimum.
- Expected profit or ROI is below the configured minimum.
- Product or variant match is ambiguous.
- Market-data confidence is low.
- A blocking risk rule lacks required evidence.
- The current landed acquisition cost exceeds the maximum purchase price.

The approved ranking score is:

- 35 percent expected absolute contribution profit
- 20 percent expected ROI
- 15 percent liquidity
- 15 percent comparable-data confidence
- 15 percent inverse expected risk

Each component uses the following deterministic initial normalization:

- Profit and ROI: zero or less scores 0, the configured minimum scores 50, and twice the configured minimum scores 100, with linear interpolation between these points.
- Liquidity: an authorized sold-through percentage, clamped to 0-100 percent, maps directly to 0-100 points. If sold-through data is unavailable, the liquidity component scores 0; comparable-data confidence remains independently determined by section 13.3.
- Comparable confidence: low scores 25, medium scores 65, and high scores 100.
- Inverse risk: a zero risk reserve scores 100; a reserve equal to 20 percent or more of expected sale receipts scores 0, with linear interpolation in between. The 20 percent saturation point is configurable.

The weighted result is rounded to the nearest integer. The score ranks candidates but never overrides a hard gate.

Recommendations are derived as follows:

- `BUY`: all gates pass at the current landed acquisition cost.
- `NEGOTIATE`: the offer would pass at or below the calculated maximum purchase price.
- `WATCH`: data is insufficient or stale, but no blocking defect makes the offer unsuitable.
- `REJECT`: a blocking risk applies or no non-negative viable purchase price exists.

Every result includes concise reasons, the maximum price, expected profit, downside profit, comparable count, data age, and major risk drivers.

## 16. Complete-PC and part-out evaluation

A complete-PC listing can be evaluated through two mutually exclusive scenarios:

1. Resale as one complete PC
2. Part-out into individually saleable components

Part-out value is:

```text
sum of downside component sale receipts
- per-item platform fees
- per-item shipping and packaging
- incremental testing, cleaning, and listing labor
- expected value loss of unsold residual parts
- aggregate risk reserve
```

The system prevents double-counting by assigning each identified component to exactly one scenario. Unknown components receive zero resale value until reviewed. The recommendation shows both scenarios and selects the more conservative passing option.

## 17. Dashboard experience

### 17.1 Overview

Shows new passing candidates, best negotiation opportunities, expected capital required, stale-data warnings, failed jobs, and source health.

### 17.2 Deals

Provides filtering and sorting by recommendation, category, expected profit, ROI, score, source, confidence, location, age, and required capital.

### 17.3 Deal detail

Shows:

- Original source link and captured values
- Canonical product match and confidence
- Comparable distribution and data provenance
- Active asks versus realized sales
- Full cost and reserve breakdown
- Maximum purchase price
- Rule explanations
- Evaluation history
- User decision and notes

### 17.4 Watchlists

Configures product models, include and exclude terms, categories, conditions, price ceilings, eBay location filters, polling interval, and alert behavior.

### 17.5 Market data

Displays downside, median, and upper price series, comparable counts, data freshness, active supply, and liquidity evidence per product.

### 17.6 Inventory and tests

Tracks acquisition, serial number, physical condition, costs, refurbishment, test procedures, evidence, listing status, and eventual disposition.

### 17.7 Settings

Manages cost profiles, score targets, risk rules, tax estimates, source credentials status, extension pairing, imports, and data-retention settings.

## 18. Background jobs

The worker supports:

- Poll configured eBay watchlists
- Normalize new or changed observations
- Re-evaluate affected listings after market or rule changes
- Mark stale market estimates
- Generate in-application alerts
- Retry recoverable source failures
- Retain terminal job failures for inspection

Jobs are idempotent. Their idempotency key combines job type, source, watchlist or entity ID, and relevant observation version.

Polling intervals are configurable but constrained by eBay quotas. Retries use bounded exponential backoff with jitter. Authentication, authorization, invalid-query, and quota-exhaustion errors are not retried indefinitely.

## 19. Error handling and data quality

The system fails closed for buying recommendations.

- Unknown products enter a review queue.
- Ambiguous variants cannot receive `BUY`.
- Missing sold comparables produce low confidence.
- Stale estimates cap the recommendation at `WATCH`.
- Invalid import rows are isolated without rejecting valid rows.
- Source failures preserve the last successful data but clearly mark its age.
- Calculation failures produce no recommendation and record a diagnostic identifier.
- Failed jobs are visible and manually retryable.

User-facing errors explain the action required without exposing credentials or internal stack traces.

## 20. Security and privacy

- eBay credentials are stored only in ignored local environment configuration.
- Secrets are never returned by API responses or displayed in logs.
- The extension pairs with a short-lived local token and sends data only to an allowlisted local origin.
- Backend CORS configuration permits only the local frontend and paired extension origin.
- Imported text is treated as untrusted data and is never rendered as executable HTML.
- SQL access uses parameterized ORM queries and validated schemas.
- Seller contact details are not collected.
- Kleinanzeigen images are not copied.
- Logs redact authorization headers, tokens, and unexpected personal data.
- The application binds to localhost by default.

Public deployment requires a separate security design covering authentication, TLS termination, authorization, rate limiting, backups, and remote secret management.

## 21. Observability and auditability

The MVP records:

- Source request outcome and duration without sensitive payloads
- Import counts and validation failures
- Normalization result and confidence
- Rule and cost-profile versions used by every evaluation
- Job attempts and terminal errors
- Alert creation and acknowledgement
- User corrections and decisions

The dashboard exposes source health, last successful poll, quota state when available, pending review count, stale estimate count, and failed job count.

## 22. Testing strategy

Implementation follows test-driven development.

### 22.1 Backend unit tests

- Money and basis-point arithmetic
- Effective-dated fee selection
- Each tax-estimate profile
- Risk reserve calculation
- Maximum purchase-price solver
- Hard gates, score, and recommendation
- Part-out versus complete-system isolation
- Data-confidence thresholds

### 22.2 Normalization tests

Fixture sets cover representative GPU, CPU, mainboard, RAM, SSD, PSU, and complete-PC titles, including misleading variants, defective items, empty boxes, and bundles.

### 22.3 Integration tests

- PostgreSQL repositories and migrations
- Redis-backed job idempotency
- Recorded eBay Browse API responses
- Product Research and CSV import validation
- API error contracts

Live eBay calls are separate credential-dependent acceptance checks and are never represented as passed by fixture tests.

### 22.4 Extension tests

- Extraction from local saved HTML fixtures
- Explicit-click requirement
- Preview and edit behavior
- Minimum-field transfer
- Rejection of seller contact fields and images
- Pairing and local-origin restrictions

Tests do not automate the live Kleinanzeigen site.

### 22.5 Frontend tests

- Calculation breakdown rendering
- Confidence and stale-data states
- Review queue and correction flow
- Watchlist editing
- Deal filtering and sorting
- Inventory and test entry

Browser end-to-end tests verify the critical local flows against controlled fixtures.

## 23. Local operation and configuration

Docker Compose starts PostgreSQL, Redis, backend, worker, and frontend. The extension is built separately and loaded locally by the user.

Required configuration categories are:

- eBay client credentials and marketplace
- database and Redis connection values
- local frontend and extension origins
- polling and retention defaults
- initial cost and risk profile values

The repository provides an example environment file containing names and safe placeholders only. Real credentials must never be committed.

Database migrations are the only supported way to change persisted schema.

## 24. Delivery slices

The design is delivered as five vertical slices within one MVP:

1. Foundation: local stack, schema, health endpoints, and fixture-based pipeline
2. Evaluation: normalization, market statistics, finance, risk, score, and deal-detail API
3. eBay and watchlists: official active-listing polling, deduplication, and source health
4. Dashboard: overview, deals, detail, market data, settings, and alerts
5. Companion and inventory: confirmed Kleinanzeigen import, inventory, and test records

Each slice must leave the application runnable and its implemented behavior tested.

## 25. Acceptance criteria

The MVP is accepted locally when all of the following are demonstrated:

- Docker Compose starts the application stack from documented commands.
- A seeded listing becomes a normalized, explainable evaluation.
- Money and fee calculations use cents and effective-dated rate profiles.
- An ambiguous product is held for review and cannot receive `BUY`.
- Low or stale comparable confidence caps the result at `WATCH`.
- Maximum purchase price changes correctly when costs or target ROI change.
- Complete-PC and part-out values do not double-count components.
- eBay credentials can be configured without appearing in logs or UI.
- A live eBay acceptance run succeeds when valid credentials and network access are supplied; otherwise it remains explicitly open.
- The companion imports exactly one user-opened fixture listing after confirmation.
- No live Kleinanzeigen automation is present or executed.
- Failed jobs and stale data are visible in the dashboard.
- Core frontend routes render and critical interactions pass browser tests.
- Automated backend, worker, frontend, and extension test suites pass.

## 26. Deferred capabilities

The following require separate future design and approval:

- Authorized automated Kleinanzeigen connector
- External notifications such as email, Telegram, or mobile push
- Automatic eBay listing publication
- Multi-user roles and public hosting
- Automated hardware benchmark capture
- Predictive machine-learning pricing
- Accounting-system export
- Automated seller messaging or purchasing

## 27. Final design boundary

The MVP provides explainable acquisition intelligence and a documented workflow from discovery to inventory evidence. It deliberately stops before autonomous marketplace actions and before any unapproved Kleinanzeigen automation.

The implementation plan must preserve this boundary and must not claim live eBay, tax, legal, or rendered-browser acceptance without explicit evidence from the corresponding integration check.
