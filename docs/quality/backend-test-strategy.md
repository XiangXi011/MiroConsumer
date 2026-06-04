# Backend Test Strategy

The backend test suite is large enough that a local full run can exceed an
interactive review window. Treat merge readiness as layered evidence instead of
one blocking local command.

Before opening or splitting a PR, inspect the current branch size:

```powershell
./scripts/change_inventory.ps1
```

## Fast Quality Gate

Run this before handing off a backend change:

```powershell
./scripts/quality_gate.ps1 -BackendOnly
```

For OpenClaw or research-flow changes, include the backend smoke subset:

```powershell
./scripts/quality_gate.ps1 -BackendOnly -BackendSmoke
```

The equivalent expanded commands are:

```powershell
cd backend
uv run ruff check app tests
.venv\Scripts\python.exe -m pytest tests\consumer\test_research_ingest.py tests\api\test_openclaw_routes.py tests\services\application\test_openclaw_orchestrator.py -v --tb=short --no-cov
```

This gate covers lint, research ingestion, OpenClaw routes, and OpenClaw
orchestration. Add touched-file tests to this command for the files changed in
the current batch.

## Frontend Gate

Run this before handing off a frontend or shared API-contract change:

```powershell
./scripts/quality_gate.ps1 -FrontendOnly
```

## Slow Full Regression

Run this when time allows, or delegate it to CI when local execution exceeds the
review window:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\ -v --tb=short --no-cov
```

If it times out locally, record:

- the exact command;
- the timeout duration;
- how many tests were collected, if available;
- which fast gate and touched-file tests passed.

Do not claim the full backend suite passed unless the full command exits with
code 0.

## CI Expectations

CI owns the heavier gates:

- backend Ruff: `uv run --python 3.12 ruff check app tests`;
- backend coverage regression: `uv run --python 3.12 pytest --cov=app --cov-report=term-missing --cov-fail-under=80`;
- integration tests with dockerized services;
- frontend typecheck and Vitest;
- consumer golden smoke tests;
- benchmarks and security scans.

Local development should stay fast enough to run repeatedly; CI should provide
the expensive confidence layer.

## Search Gateway Ownership

The `search-gateway/` directory is treated as an external local checkout in this
repository. Current local checkouts point at:

```text
https://github.com/XiangXi011/web_search.git
```

Keep `search-gateway/` changes in that repository unless a separate change
explicitly converts this project to use a tracked submodule or vendored service
directory.
