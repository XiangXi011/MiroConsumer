# MiroConsumer

Consumer simulation platform: Flask backend + Vue frontend + search-gateway microservice.

## Quick Commands

```bash
# Backend quick quality gate
./scripts/quality_gate.ps1

# Change inventory before splitting or opening a PR
./scripts/change_inventory.ps1

# Backend-only quick gate
./scripts/quality_gate.ps1 -BackendOnly

# Backend quick gate details
cd backend && uv run ruff check app tests
cd backend && .venv/Scripts/python.exe -m pytest tests/consumer/test_research_ingest.py tests/api/test_openclaw_routes.py tests/services/application/test_openclaw_orchestrator.py -v --tb=short --no-cov

# Run single test file
cd backend && .venv/Scripts/python.exe -m pytest tests/consumer/test_research_ingest.py -v --tb=short --no-cov

# Slow backend full regression
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short --no-cov

# Run frontend tests
./scripts/quality_gate.ps1 -FrontendOnly

# Start dev environment
docker-compose up -d

# Codemap: project overview
codemap --depth 3 .

# Codemap: dependency analysis
codemap --deps --only py .

# Codemap: check what changed
codemap --diff .

# Codemap: impact of a file
codemap --importers backend/app/config.py .
```

## Architecture

- **backend/**: Flask app (220 source files, 216 test files)
  - `app/api/` - route handlers
  - `app/services/consumer/` - core business logic (society simulation, interviews, experiments)
  - `app/services/application/` - app-level services (queue, cache, concurrency)
  - `app/repositories/` - data access (SQLAlchemy + filesystem)
  - `app/models/` - domain models (project, task)
  - `app/auth/` - authentication & tenant isolation
- **frontend/**: Vue 3 SPA with Vite
  - `src/components/` - UI components (27 .vue files)
  - `src/api/` - backend API clients
  - `src/utils/` - business logic helpers
- **search-gateway/**: Independent search microservice with SearXNG
  - Local `search-gateway/` checkouts are ignored in this repo; use the external `web_search` repository or a submodule decision in a separate change.

## Key Hub Files (change carefully)

- `backend/app/config.py` - 46 importers
- `backend/app/services/consumer/models.py` - 37 importers
- `backend/app/services/consumer/society/population_models.py` - 27 importers
- `backend/app/repositories/sqlalchemy.py` - 25 importers
- `backend/app/services/report_agent.py` - 23 importers

## Test Structure

Tests mirror source: `tests/consumer/` tests `services/consumer/`, etc.
Use `--no-cov` flag to avoid coverage collection overhead during development.
For merge readiness, prefer the quick quality gate plus touched-file tests first; run the slow full regression separately when time allows.
