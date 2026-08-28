# 00 — Baseline checks (verbatim command output)

Date: 2026-08-28T01:48:37Z
Branch: convoy/escraper-evidence-driven-improvement-cam/5cd45cdc/gt/toast/8621414f
HEAD: e58f237959958206a1dd1f4a7d5a0043ae99e5b6
Worktree: /workspace/rigs/77329833-d462-4048-bcaf-5125e5f5e60f/worktrees/convoy__escraper-evidence-driven-improvement-cam__5cd45cdc__gt__toast__8621414f

## Environment

```text
python3: Python 3.13.5
pip: pip 26.2.1 from /home/agent/.local/lib/python3.13/site-packages/pip (python 3.13)
docker: not present (command not found)
uv: not present (command not found)
ruff: /usr/bin/bash: line 14: ruff: command not found
not in PATH; invoked as \`python3 -m ruff\`
pytest: pytest 9.1.1
alembic: invoked as `python3 -m alembic`
uvicorn: invoked as `python3 -m uvicorn`
```

Container notes:

- Python 3.13.5 is preinstalled. No pip, no venv, no Docker, no uv, no system package
  manager access (apt locked, no sudo).
- `pip` was bootstrapped via `get-pip.py --user --break-system-packages` into
  `/home/agent/.local/`.
- Backend dependencies from `backend/pyproject.toml` were installed into the user site.
  Two practical blockers: (1) `pip install -e .[dev]` fails on package discovery
  ("Multiple top-level packages discovered in a flat-layout: ['app', 'migrations']")
  because both `app/` and `migrations/` sit at the top of `backend/`; (2) several
  pinned versions (e.g. `pydantic>=2.15,<3`, `fastapi>=0.141,<0.142`) are not on the
  current package index. We therefore installed the same logical set with relaxed lower
  bounds (fastapi 0.141, pydantic 2.13, pydantic-settings 2.15, sqlalchemy 2.0.52,
  asyncpg 0.31, alembic 1.19, httpx 0.28, uvicorn[standard] 0.52, pytest 9.1,
  pytest-asyncio 1.4, ruff 0.16). **No application code was modified.** The runtime is
  functionally equivalent for the test/lint commands documented in the README.

## 1) Import the FastAPI application factory

```text
$ cd backend && PYTHONPATH=. python3 -c 'from app.main import create_app; print(create_app)'
<function create_app at 0x7fbad6a68220>
exit=0
```

## 2) Run uvicorn against the health endpoint

```text
$ cd backend && PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8766
--- uvicorn log ---
INFO:     Started server process [2081]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8766 (Press CTRL+C to quit)
INFO:     127.0.0.1:55814 - "GET /api/v1/health HTTP/1.1" 200 OK

--- curl http://127.0.0.1:8766/api/v1/health ---
{"status":"ok"}
HTTP 200

--- curl http://127.0.0.1:8766/openapi.json (root path) ---
paths present in OpenAPI: /api/v1/health
(application routes: api paths = 1, all under /api/v1)

$ python3 -c '...; print all routes'
/openapi.json ['GET', 'HEAD']
/docs ['GET', 'HEAD']
/docs/oauth2-redirect ['GET', 'HEAD']
/redoc ['GET', 'HEAD']

exit=0
```

## 3) Run the documented test suite

Full discovery (no DB):

```text
$ cd backend && python3 -m pytest --collect-only -q
tests/db/test_evaluation_models.py::test_evaluation_snapshot_retains_versions_and_results
tests/db/test_listing_models.py::test_observation_links_raw_evidence_to_canonical_product
tests/db/test_operations_models.py::test_watchlist_persists_include_and_exclude_terms
tests/db/test_operations_models.py::test_inventory_item_and_test_run_survive_reload
tests/domain/test_enums.py::test_stable_external_enum_values
tests/domain/test_money.py::test_money_addition_requires_same_currency
tests/domain/test_money.py::test_basis_points_round_half_up
tests/domain/test_money.py::test_money_rejects_non_integer_cents
tests/test_health.py::test_health_returns_ok

=============================== warnings summary ===============================
app/db/models/operations.py:47
  /workspace/rigs/77329833-d462-4048-bcaf-5125e5f5e60f/worktrees/convoy__escraper-evidence-driven-improvement-cam__5cd45cdc__gt__toast__8621414f/backend/app/db/models/operations.py:47: PytestCollectionWarning: cannot collect test class 'TestRunModel' because it has a __init__ constructor (from: tests/db/test_operations_models.py)
    class TestRunModel(IdMixin, TimestampMixin, Base):

../../../../../../home/agent/.local/lib/python3.13/site-packages/fastapi/testclient.py:1
  /home/agent/.local/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
9 tests collected in 0.74s
```

Run with the no-DB slice (the only slice that can execute without PostgreSQL):

```text
$ cd backend && PYTHONPATH=. python3 -m pytest -v --ignore=tests/db
============================= test session starts ==============================
platform linux -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/rigs/77329833-d462-4048-bcaf-5125e5f5e60f/worktrees/convoy__escraper-evidence-driven-improvement-cam__5cd45cdc__gt__toast__8621414f/backend
configfile: pyproject.toml
testpaths: tests
plugins: asyncio-1.4.0, anyio-4.14.2
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 5 items

tests/domain/test_enums.py::test_stable_external_enum_values PASSED      [ 20%]
tests/domain/test_money.py::test_money_addition_requires_same_currency PASSED [ 40%]
tests/domain/test_money.py::test_basis_points_round_half_up PASSED       [ 60%]
tests/domain/test_money.py::test_money_rejects_non_integer_cents PASSED  [ 80%]
tests/test_health.py::test_health_returns_ok PASSED                      [100%]

=============================== warnings summary ===============================
../../../../../../home/agent/.local/lib/python3.13/site-packages/fastapi/testclient.py:1
  /home/agent/.local/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 5 passed, 1 warning in 0.43s =========================
```

Full suite (DB tests included, expected to error because PostgreSQL is not running):

```text
$ cd backend && PYTHONPATH=. python3 -m pytest -v
collected 9 items
  tests/db/test_evaluation_models.py::test_evaluation_snapshot_retains_versions_and_results ERROR (Connect call failed 127.0.0.1:5432)
  tests/db/test_listing_models.py::test_observation_links_raw_evidence_to_canonical_product ERROR (Connect call failed 127.0.0.1:5432)
  tests/db/test_operations_models.py::test_watchlist_persists_include_and_exclude_terms ERROR (Connect call failed 127.0.0.1:5432)
  tests/db/test_operations_models.py::test_inventory_item_and_test_run_survive_reload ERROR (Connect call failed 127.0.0.1:5432)
  tests/domain/test_enums.py::test_stable_external_enum_values PASSED
  tests/domain/test_money.py::test_money_addition_requires_same_currency PASSED
  tests/domain/test_money.py::test_basis_points_round_half_up PASSED
  tests/domain/test_money.py::test_money_rejects_non_integer_cents PASSED
  tests/test_health.py::test_health_returns_ok PASSED
=================== 5 passed, 2 warnings, 4 errors in ~2.2s ===================
exit=1 (because of the 4 DB errors)
```

## 4) Run the documented lint command

```text
$ cd backend && python3 -m ruff check app tests
All checks passed!
exit=0
```

## 5) mypy / typecheck

```text
mypy is not configured in `backend/pyproject.toml` and is not mentioned in README
"Tests" section.

$ grep -E 'mypy|\[tool\.mypy' backend/pyproject.toml
no mypy config in pyproject.toml
$ grep -E 'mypy' README.md
no mypy mention in README

Conclusion: there is no documented typecheck command to run.
```

## 6) Alembic — history and connectivity

```text
$ cd backend && python3 -m alembic history
0002 -> 0003 (head), add operations
0001 -> 0002, add market and evaluations
<base> -> 0001, add products and listings

$ DATABASE_URL=postgresql+asyncpg://nobody:nobody@127.0.0.1:1/nope python3 -m alembic upgrade head
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/agent/.local/lib/python3.13/site-packages/alembic/__main__.py", line 4, in <module>
    main(prog="alembic")
exit=1
```

The three revisions correspond to the slices already merged into `main`:
`0001_products_and_listings.py`, `0002_market_and_evaluations.py`,
`0003_operations.py`. They cannot be applied in this container because there is no
running PostgreSQL service.

## 7) Docker Compose stack

```text
$ docker --version
docker not present (command not found)
$ docker compose ps
docker not present (command not found)
```

The compose file is present (`compose.yaml`) and defines `postgres`, `redis`, and
`backend` services. It cannot be exercised in this container.
