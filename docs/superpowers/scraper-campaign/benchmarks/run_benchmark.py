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
    passed = 0
    failed = 0
    for line in out.splitlines():
        line = line.strip()
        for token in line.replace(",", "").split():
            if token.isdigit():
                idx = line.find(token)
                tail = line[idx + len(token):]
                if tail.startswith(" passed"):
                    passed = int(token)
                elif tail.startswith(" failed"):
                    failed = int(token)
    return {
        "command": "pytest -q --ignore=tests/db",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "tests_passed": passed,
        "tests_failed": failed,
    }


def _lint(cwd: Path) -> dict[str, object]:
    code, out, elapsed = _run(
        [sys.executable, "-m", "ruff", "check", "app", "tests"],
        cwd,
    )
    last_line = ""
    for line in out.splitlines()[::-1]:
        if line.strip():
            last_line = line.strip()
            break
    return {
        "command": "ruff check app tests",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "result_line": last_line,
    }


def _app_factory(cwd: Path) -> dict[str, object]:
    code, out, elapsed = _run(
        [sys.executable, "-c", "from app.main import create_app; print('ok')"],
        cwd,
    )
    return {
        "command": "python -c 'from app.main import create_app; print(\"ok\")'",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "output": "ok" if code == 0 else (out.strip().splitlines()[-1] if out.strip() else ""),
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
    last_line = ""
    for line in out.splitlines()[::-1]:
        if line.strip():
            last_line = line.strip()
            break
    return {
        "command": "fastapi TestClient GET /api/v1/health",
        "returncode": code,
        "elapsed_seconds": round(elapsed, 4),
        "response": last_line,
    }


_TIMING_KEYS = {"elapsed_seconds"}


def _split_timing(step_result: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    """Return (deterministic, timing) views of a step result.

    The benchmark JSON written to ``--out`` contains only the
    deterministic view, so two consecutive runs are byte-identical
    when nothing changed in the code. Wall-clock timings are written
    to a sidecar file.
    """
    deterministic = {k: v for k, v in step_result.items() if k not in _TIMING_KEYS}
    timing = {k: v for k, v in step_result.items() if k in _TIMING_KEYS}
    return deterministic, timing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="JSON file to write the deterministic benchmark result to",
    )
    args = parser.parse_args()

    steps: dict[str, dict[str, object]] = {}
    timings: dict[str, dict[str, object]] = {}
    for name, fn in (
        ("collect", _collect),
        ("run_tests", _run_tests),
        ("lint", _lint),
        ("app_factory", _app_factory),
        ("health_smoke", _health_smoke),
    ):
        raw = fn(BACKEND)
        deterministic, timing = _split_timing(raw)
        steps[name] = deterministic
        timings[name] = timing

    result = {
        "schema_version": 1,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "backend_dir": str(BACKEND),
        "steps": steps,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    timings_path = args.out.with_name(args.out.stem + ".timings.json")
    timings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "steps": timings,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    overall_ok = all(int(step["returncode"]) == 0 for step in steps.values())
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
