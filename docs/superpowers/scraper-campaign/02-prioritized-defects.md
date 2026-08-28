# 02 — Prioritized Top-5 defects in scraper-related code

> Evidence-driven defect list for the eScraper backend as of HEAD
> `92ab06b` on branch
> `convoy/escraper-evidence-driven-improvement-cam/5cd45cdc/gt/toast/9d66b18f`.
>
> Source of truth: `backend/app/` (currently: `domain/money.py`, `domain/enums.py`,
> `db/models/*`, `api/health.py`, `core/config.py`, `main.py`) and the spec
> `docs/superpowers/specs/2026-08-27-pc-hardware-flipping-dashboard-design.md`
> sections 13, 14, 15.
>
> No scraper code, no eBay adapter, no normalization / dedup / scoring /
> finance / ranking service exists yet. Every defect listed here is in code
> that is part of the agreed contract and that the rest of the campaign will
> exercise. Defects are ranked by **severity × likelihood × blast radius**.
> The campaign will fix them in order.

## D1 (P1) — `apply_basis_points` does not validate the basis-point range

- **Where:** `backend/app/domain/money.py:11-14`
- **Current behavior:** accepts any integer including negatives, values
  greater than `10_000` (i.e. rates > 100 %), and `bool` (which is an `int`
  subclass in Python). The `TypeError` check only guards against
  non-`int` values.
- **Why it matters:** every spec-defined financial rule (platform fee,
  risk reserve, ROI, ranking weights, confidence score) is a
  basis-point percentage. A negative rate would silently flip the sign
  of a fee, a value > 10 000 bps would silently produce a fee > 100 %,
  and a `bool` would bypass the type check. None of these is caught
  today.
- **Spec reference:** §14 "percentages are integer basis points
  (`10000 bps = 100 %`)". §15 ranking-score table uses weights that
  must sum to 100 %. Without range validation any caller can pass a
  `True` and pay 0.01 %.
- **Severity:** High. Blast radius: every downstream calculation
  that ever calls `apply_basis_points` (risk reserve, fee, tax,
  ROI, scoring).
- **Fix sketch:** validate `0 <= basis_points <= 10_000` (or document
  the supported contract); reject `bool` explicitly; add
  `ValueError` (not `TypeError`) for out-of-range integers.
- **Regression test:** add
  `tests/domain/test_money.py::test_apply_basis_points_rejects_out_of_range`
  and `::test_apply_basis_points_rejects_bool` before the fix.

## D2 (P2) — `Money.__post_init__` does not validate cents range

- **Where:** `backend/app/domain/money.py:17-36`
- **Current behavior:** `Money` only checks `isinstance(self.cents, int)`.
  Negative values, zero, and `bool` are all silently accepted.
- **Why it matters:** spec §14 "Money is integer cents" with the
  contract that `0 cents` is the floor for non-cash balances and that
  risk-reserve / tax / profit fields are non-negative in the
  `EvaluationSnapshotModel`. Allowing `Money(-1)` lets a future
  service author a "negative fee" or a "negative reserve" by accident
  and produce a `BUY` recommendation against a phantom cost.
- **Severity:** Medium-High. Blast radius: every financial model
  field.
- **Fix sketch:** add `>= 0` check and a `ValueError("money cents must be
  non-negative")`; explicitly reject `bool` (which is an `int`
  subclass).
- **Regression test:**
  `tests/domain/test_money.py::test_money_rejects_negative_cents`
  and `::test_money_rejects_bool`.

## D3 (P3) — `Settings.frontend_origin` is typed as `AnyHttpUrl` but the
FastAPI CORS code coerces it through `str(...).rstrip("/")`  *(resolved in iter4)*

- **Where:** `backend/app/main.py:13`,
  `backend/app/core/config.py:12`.
- **Current behavior:** `frontend_origin` is a `pydantic.AnyHttpUrl`,
  which serialises to a string with a trailing slash. `str()` in CORS
  will therefore become `http://localhost:5173/` even if the user set
  `http://localhost:5173`. The current code rips the trailing slash
  off, but the same is not done for the case where a user
  configures multiple origins (which the spec doesn't yet
  require, but the model breaks if it ever does).
- **Why it matters:** subtle — today's only test is
  `tests/test_health.py::test_health_returns_ok`, which doesn't
  exercise CORS. Once a frontend or an extension origin is added,
  silent string mangling will produce 401s or open up CORS to a
  wrong origin.
- **Severity:** Medium (latent, but cheap to fix).
- **Fix sketch:** centralise origin normalisation in `Settings` so
  the CORS middleware and any future consumer always see a clean
  list of origins without trailing slashes. Add a unit test that
  reads the settings and asserts the normalised value.
- **Regression test:**
  `tests/core/test_config.py::test_settings_frontend_origin_has_no_trailing_slash`.

## D4 (P4) — `apply_basis_points` is silent for zero rates and for the
rounding convention  *(deferred — not a correctness defect)*

- **Where:** `backend/app/domain/money.py:11-14`.
- **Current behavior:** the function uses `ROUND_HALF_UP`. That is
  correct for fees and tax, but the spec §14 also mentions that
  percentages "round to the nearest cent" with **no** explicit
  convention. Two adjacent calls (e.g. tax + fee applied in sequence)
  can disagree by 1 cent because of the order. Today the test
  `apply_basis_points(25690, 500) == 1285` only covers a single
  call.
- **Why it matters:** every `EvaluationSnapshotModel.expected_profit_cents`
  is the sum of many such roundings. A 1-cent difference per line
  item is acceptable, but a divergence that grows per call is not.
- **Severity:** Low-Medium.
- **Fix sketch:** document the rounding contract on
  `apply_basis_points`; add a regression test for the sequence
  "apply platform fee then VAT" and assert the documented total.

## D5 (P5) — `HealthResponse` does not surface the configured app
version and uses `Literal["ok"]` only  *(resolved in iter5)*

- **Where:** `backend/app/api/health.py:8-13`,
  `backend/app/core/config.py:7-15`.
- **Current behavior (was):** the health endpoint returned
  `{"status": "ok"}` regardless of which release / commit was
  running. Operations could not distinguish a `v0.1.0` from `v0.2.0`
  via a probe, which is required once the worker / scheduler is
  live (so that a canary can verify the right image is in front of
  Redis / Postgres).
- **Fix (iter5):** added `app_version: str = "0.0.0"` to `Settings`
  (overridable via the `APP_VERSION` env var thanks to the existing
  `pydantic-settings` `BaseSettings` machinery) and added
  `version: str` to `HealthResponse`. The endpoint now returns
  `{"status": "ok", "version": "<app_version>"}`.
- **Why it matters:** low for the current slice (no frontend,
  no worker, no CI), but the moment a deploy pipeline exists
  the endpoint becomes the only machine-readable signal. Adding it
  now is essentially free.
- **Severity:** Low.
- **Fix sketch:** extend `Settings` with `app_version: str = "0.0.0"`
  (overridable via `APP_VERSION` env var or `pyproject.toml`
  version), include it in `HealthResponse` as `version: str`, and
  document the change.
- **Regression test:**
  `tests/api/test_health.py::test_health_returns_version`.

## Other candidates intentionally NOT in the Top-5

These were considered and dropped because either the spec does not yet
constrain them, or they require a feature that does not exist
(e.g. we cannot dedup-fix dedup before the ingestion service exists).

- **Missing eBay Browse API adapter** — feature, not a defect.
- **No normalization / scoring / finance service** — features, not defects.
- **No Alembic / Postgres in the test container** — environment limitation
  documented in `00-baseline-checks.md`, not a code defect.
- **`Settings.redis_url` declared but unused** — by design (Dramatiq
  is a future slice).
- **`ProductModel.ebay_product_id` never populated** — no source
  adapter exists; covered by the eBay-adapter feature work.

## How the campaign will pick the next defect

1. D1 → D5 in order, one defect per iteration.
2. If a defect is fixed but the benchmark shows no improvement or a
   regression, revert and try the next one.
3. After 5 iterations, or once all Top-5 defects are resolved AND
   the last two evaluations show no meaningful improvement, the
   campaign stops and produces `04-final-report.md`.
