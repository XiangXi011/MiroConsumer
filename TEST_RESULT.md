# Test Result

Date: 2026-05-11
Branch: phase7/gatekeeper-comprehensive-fixes

## Passed

| Command | Result |
|---|---|
| `cd backend && uv run --python 3.12 pytest --cov=app --cov-report=term-missing` | Pass: 1915 passed, 3 skipped, coverage 73%. |
| `cd frontend && npm ci && npm run build && npm test` | Pass: npm audit 0 vulnerabilities, Vite build success, 25 test files / 288 tests passed. |
| `bandit -r backend/app/ -ll --skip B101` | Pass: no issues identified; no files skipped; no `#nosec` skips. |
| `pip-audit` | Pass: no known vulnerabilities found. |
| `cd backend && uv run --python 3.12 --with pip-audit pip-audit` | Pass: no known vulnerabilities found in backend project environment; local project package skipped because it is not on PyPI. |
| `cd backend && uv run --python 3.12 pytest tests/security/test_bandit_regressions.py tests/consumer/test_url_ingest.py tests/consumer/society/test_network_topology.py tests/consumer/society/test_population_factory.py tests/consumer/society/test_society_runtime_checkpointing.py tests/utils/test_llm_client.py -q` | Pass: 37 passed. |
| `cd frontend && npm test -- navigation.test.js` | Pass: 2 passed. |

## Blocked

| Command | Result |
|---|---|
| `docker build -t miroconsumer:test .` | Blocked: Docker CLI is installed, but Docker Desktop daemon is unavailable. `docker info` fails with missing `npipe:////./pipe/dockerDesktopLinuxEngine`; `com.docker.service` is stopped and cannot be started without elevated permissions. |
| `trivy image --severity HIGH,CRITICAL --exit-code 1 miroconsumer:test` | Blocked by the same Docker daemon issue and missing local image. Trivy installation attempts via Chocolatey and Go were blocked by non-admin lock/permission and network TLS/proxy failures. CI workflow uses pinned Trivy action and has a pytest contract test. |

## Notes

- Docker Desktop WSL distribution reports `docker-desktop` running, but Windows Docker CLI cannot connect to either `desktop-linux` or `default` daemon pipes.
- The Docker workflow is still repaired and covered by `backend/tests/ci/test_docker_workflow.py`; local image build/scan must be rerun on a host with Docker service access.
