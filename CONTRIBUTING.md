# Contributing Guide

Updated: 2026-05-13

## 1. Development Principles

MiroConsumer changes are accepted when they are small, testable, and traceable to
the product or remediation spec that motivated them. Prefer existing patterns
over new abstractions unless the new abstraction removes real duplication or
reduces risk.

## 2. Branch Naming

Use short descriptive branch names:

- `feature/<topic>` for new product behavior
- `fix/<topic>` for bug fixes
- `hotfix/<topic>` for urgent production fixes
- `codex/<topic>` for Codex-assisted remediation branches

Do not work directly on `main`.

## 3. Local Setup With Docker Compose

1. Install Docker Desktop or another Docker-compatible runtime.
2. Copy environment defaults:
   `cp .env.example .env`
3. Set `LLM_API_KEY`, `ZEP_API_KEY`, `SECRET_KEY`, and `JWT_SECRET_KEY`.
4. Start the stack:
   `docker compose up -d`
5. Open the frontend at `http://localhost:3000`.
6. Check backend readiness at `http://localhost:5001/ready`.

The default compose stack starts PostgreSQL, Redis, MinIO, the backend, and the
frontend. MinIO console access is loopback-bound in production compose files.

## 4. Manual Backend Setup

1. Install Python 3.12.
2. Install `uv`.
3. From the repository root, run:
   `cd backend && uv sync`
4. Set required environment variables:
   `LLM_API_KEY`, `ZEP_API_KEY`, `SECRET_KEY`, `JWT_SECRET_KEY`.
5. Optional local services:
   PostgreSQL for repository integration tests, Redis for queues/rate limits,
   and MinIO for S3-compatible artifact storage.
6. Start the backend:
   `cd backend && uv run python run.py`

## 5. Manual Frontend Setup

1. Install Node.js 24 for CI parity, or Node.js 18+ for local development.
2. Install dependencies:
   `cd frontend && npm ci`
3. Start Vite:
   `npm run dev`
4. Run type checking:
   `npm run typecheck`
5. Build production assets:
   `npm run build`

## 6. Code Style

Backend:

- Target Python 3.12.
- Use `from __future__ import annotations` in new Python files.
- Keep route handlers thin and push behavior into application or domain services.
- Prefer Pydantic request models over raw `request.get_json()`.
- Add module docstrings for public modules and complex domain logic.

Frontend:

- Use TypeScript for new source files.
- Keep API clients in `frontend/src/api`.
- Keep reusable state in composables under `frontend/src/composables`.
- Run `npm run typecheck` after changing typed modules.

## 7. Formatting And Linting

Use the repository configuration when adding lint tools. Python style follows
PEP 8 and should be compatible with ruff/black defaults. Frontend code should
use the existing Vite/Vitest/TypeScript conventions.

Recommended pre-commit flow:

```bash
python -m pip install pre-commit
pre-commit install
```

If a hook is unavailable locally, run the equivalent CI command before pushing.

## 8. Testing Guidelines

Use TDD for behavior changes:

1. Write or update the smallest failing test.
2. Run the focused test and confirm the failure is meaningful.
3. Implement the smallest change that passes it.
4. Run the focused test again.
5. Run the relevant regression suite.

Backend baseline:

```bash
python -m pytest backend/tests/ -x -q
```

Focused backend tests can disable global coverage while iterating:

```bash
python -m pytest backend/tests/spec/test_name.py -q -o addopts=
```

Frontend baseline:

```bash
npm run typecheck --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend
```

Coverage requirements:

- backend coverage gate: at least 80 percent
- frontend short-term coverage gate: at least 60 percent branch coverage and 70
  percent lines/functions/statements
- new high-risk code should include direct regression tests

## 9. Fixture Usage

Keep fixtures deterministic. Prefer explicit payload builders over large opaque
JSON blobs. Do not add real API keys, customer data, or private research assets
to fixtures. Use small representative examples that exercise the contract.

## 10. Commit Messages

Use Conventional Commits:

- `feat: add persona pack patch endpoint`
- `fix: reject wildcard CORS in production`
- `test: cover branch diff confidence deltas`
- `docs: document AlertManager rollout`
- `chore: align changelog version gate`

Include the spec ID in the body when the work closes a remediation item.

## 11. CHANGELOG Format

MiroConsumer uses Keep a Changelog style release notes:

- headings use `## [x.y.z] - YYYY-MM-DD`
- versions follow SemVer
- sections use `Added`, `Changed`, `Fixed`, and `Security`
- dates use ISO 8601 (`YYYY-MM-DD`)
- the top release heading must match `backend/pyproject.toml`

The CI version consistency check runs:

```bash
cd backend
uv run --python 3.12 python scripts/check_version_consistency.py --root ..
```

## 12. Pull Request Checklist

Every PR should include:

- problem statement or linked issue/spec
- summary of user-visible behavior
- focused tests that failed before the implementation
- regression commands run locally
- migration notes for schema or API changes
- screenshots or recordings for frontend UX changes
- security notes for auth, tenant, CORS, prompt, or dependency changes

## 13. Issue Template Reference

When filing issues, include:

- affected phase or spec ID
- exact route, component, or module
- reproduction steps
- expected behavior
- actual behavior
- logs or screenshots
- suggested verification command

## 14. Security And Compliance

Do not commit secrets. Do not log raw prompts, API keys, passwords, JWTs, or
customer research data. Keep dependency updates traceable through Dependabot or
an equivalent reviewed PR. AGPL compliance and SBOM handling are documented in
`docs/compliance.md`.

## 15. Deployment Notes

Deployment, rollback, autoscaling, alerting, and backup procedures live in
`docs/deployment.md`. Operations SLOs and benchmark gates live in
`docs/operations.md`.
