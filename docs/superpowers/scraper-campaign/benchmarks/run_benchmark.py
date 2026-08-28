"""Headless benchmark for the eScraper backend.

Measures the deterministic, no-DB slice of the campaign:

* test-suite collection time
* test-suite execution time and pass count
* ruff lint pass
* import of the FastAPI application factory (proves `app.main` is
  importable and dependency wiring is correct)
* a smoke run of the health endpoint via the FastAPI TestClient

The script writes its result to a JSON file so that two consecutive
runs can be diffed. It does **not** start a real uvicorn process
or touch PostgreSQL / Redis.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, float]:
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": ".", "PATH": __import__("os").environ.get("PATH", "")},
    )
    elapsed = time.perf_counter() - started
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output, elapsed


def _collect(cwd: Path) -> dict[str, object]:
    code, out, elapsed = _run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd,
    )
    tests = sorted(
        line.strip()
        for line in out.splitlines()
        if "::" in line and not line.startswith(("=", "-"))
    )
    return {
        "command": "pytest --collect-only -q",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "tests_collected": len(tests),
        "tests": tests,
    }


def _run_tests(cwd: Path) -> dict[str, object]:
    code, out, elapsed = _run(
        [sys.executable, "-m", "pytest", "-q", "--ignore=tests/db"],
        cwd,
    )
    return {
        "command": "pytest -q --ignore=tests/db",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "output_tail": "\n".join(out.splitlines()[-12:]),
    }


def _lint(cwd: Path) -> dict[str, object]:
    code, out, elapsed = _run(
        [sys.executable, "-m", "ruff", "check", "app", "tests"],
        cwd,
    )
    return {
        "command": "ruff check app tests",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "output_tail": "\n".join(out.splitlines()[-8:]),
    }


def _app_factory(cwd: Path) -> dict[str, object]:
    code, out, elapsed = _run(
        [sys.executable, "-c", "from app.main import create_app; print(create_app)"],
        cwd,
    )
    return {
        "command": "python -c 'from app.main import create_app; print(create_app)'",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "output_tail": out.strip().splitlines()[-1] if out.strip() else "",
    }


def _health_smoke(cwd: Path) -> dict[str, object]:
    code, out, elapsed = _run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from app.main import create_app; "
                "c = TestClient(create_app()); "
                "r = c.get('/api/v1/health'); "
                "print(r.status_code, r.text.strip())"
            ),
        ],
        cwd,
    )
    return {
        "command": "fastapi TestClient GET /api/v1/health",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "output_tail": out.strip().splitlines()[-1] if out.strip() else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="JSON file to write the benchmark result to",
    )
    args = parser.parse_args()

    steps: dict[str, dict[str, object]] = {}
    for name, fn in (
        ("collect", _collect),
        ("run_tests", _run_tests),
        ("lint", _lint),
        ("app_factory", _app_factory),
        ("health_smoke", _health_smoke),
    ):
        steps[name] = fn(BACKEND)

    result = {
        "schema_version": 1,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "backend_dir": str(BACKEND),
        "steps": steps,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    overall_ok = all(int(step["returncode"]) == 0 for step in steps.values())
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
