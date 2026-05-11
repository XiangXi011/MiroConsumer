# Test Result

Date: 2026-05-11
Branch: phase7/gatekeeper-comprehensive-fixes

## Passed

| Command | Result |
|---|---|
| `cd backend && uv run --python 3.12 pytest tests/e2e/test_consumer_concept_test_golden_flow.py::test_consumer_concept_test_golden_flow_is_structurally_complete -q` | Pass: 1 passed. Reproduced and fixed the report tenant guard regression in the golden flow. |
| `cd backend && uv run --python 3.12 pytest tests/security/test_api_tenant_permissions.py tests/test_auth.py tests/security/test_tenant_isolation.py tests/security/test_permissions.py -q` | Pass: 38 passed. Covers API tenant isolation, runtime permission checks, auth, and tenant guard contracts. |
| `cd backend && uv run --python 3.12 pytest --cov=app --cov-report=term-missing` | Pass: 1922 passed, 3 skipped, 32 warnings; total coverage 73%. |
| `cd frontend && npm ci && npm run build && npm test` | Pass: npm audit found 0 vulnerabilities; Vite build succeeded; 25 test files / 288 tests passed. |
| `bandit -r backend/app/ -ll --skip B101` | Pass: no medium/high issues identified; no files skipped; no `#nosec` skips. |
| `pip-audit` | Pass: no known vulnerabilities found. |
| `cd frontend && npm test -- navigation.test.js` | Pass: 2 passed. Confirms router no longer references stale `Process.vue`, create success navigation, error render, and no alert behavior. |

## Blocked

| Command | Result |
|---|---|
| `docker build -t miroconsumer:test .` | Blocked by local host environment: Docker CLI cannot connect to `npipe:////./pipe/dockerDesktopLinuxEngine`; Docker Desktop Linux engine pipe is missing / daemon is not reachable. |
| `trivy image --severity HIGH,CRITICAL --exit-code 1 miroconsumer:test` | Blocked by local host environment: `trivy` is not installed or not on PATH, so PowerShell reports `The term 'trivy' is not recognized`. The image scan also depends on the Docker image that could not be built locally. |

## Notes

- Docker/Trivy were attempted after the passing backend, frontend, Bandit, and pip-audit checks. The remaining failure is host tooling availability, not a test skip or security-check downgrade.
- CI workflow coverage for Docker build-before-push and pinned Trivy scan ordering remains covered by backend CI contract tests.
