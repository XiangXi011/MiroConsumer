# Branch Split Plan

Current branch `review-fixes-2026` is too large for one comfortable review.
Treat it as a staging branch and split it into smaller PRs before merge.

## Current Inventory Commands

Use this script before preparing each PR:

```powershell
./scripts/change_inventory.ps1
./scripts/change_inventory.ps1 -ShowFiles
```

Use this script to check local stack size before opening stacked PRs:

```powershell
./scripts/stack_inventory.ps1
./scripts/stack_inventory.ps1 -Markdown
```

Use this script as the default local quality gate:

```powershell
./scripts/quality_gate.ps1
```

## Current Local Stack Pointers

The staging branch now has local stack pointers that mark reviewable cut points.
Use these as cherry-pick boundaries when preparing smaller PRs from the target
base; do not merge the full staging branch directly.

| Stack | Pointer | Scope |
| --- | --- | --- |
| 01 | `codex/stack-01-engineering-health` | quality gates, docs, CI, ignore hygiene |
| 02 | `codex/stack-02-openclaw-backend` | initial OpenClaw backend flow and status helpers |
| 03 | `codex/stack-03-report-foundations` | report models, prompts, parsers, workflow helpers |
| 04 | `codex/stack-04-consumer-report-helpers` | report consumer context state helpers |
| 05 | `codex/stack-05-step4-report-ui-panels` | Step4 report UI panel extraction |
| 06 | `codex/stack-06-step5-component-shells` | Step5 component shell extraction |
| 07 | `codex/stack-07-step5-composables` | Step5 composable extraction |
| 08 | `codex/stack-08-step4-composables` | Step4 composable extraction |
| 09 | `codex/stack-09-openclaw-session-fix` | deterministic OpenClaw session persistence |
| 10 | `codex/stack-10-report-manager-module` | report manager extraction |
| 11 | `codex/stack-11-report-logging-module` | report logging extraction |
| 12 | `codex/stack-12-consumer-report-mixin` | consumer report mixin extraction |
| 13 | `codex/stack-13-report-tool-mixin` | report tool mixin extraction |
| 14 | `codex/stack-14-step4-style-extraction` | Step4 scoped/global style extraction |
| 15 | `codex/stack-15-consumer-report-mixin-split` | consumer report context/render mixin split |
| 16 | `codex/stack-16-workflow-panel-style-extraction` | workflow panel scoped style extraction |
| 17 | `codex/stack-17-openclaw-evidence-helpers` | OpenClaw evidence helper extraction |
| 18 | `codex/stack-18-report-tool-displays-split` | report tool display component split |
| 19 | `codex/stack-19-consumer-confidence-helpers` | consumer confidence helper extraction |
| 20 | `codex/stack-20-consumer-branching-helpers` | consumer branching/comparison helper extraction |
| 21 | `codex/stack-21-branch-split-stack-map` | stack pointer map documentation |
| 22 | `codex/stack-22-stack-inventory-script` | stack inventory script and documentation |

When preparing a PR from a stack pointer, validate the stack against its parent
stack instead of the final staging head. Example:

```powershell
git diff --stat codex/stack-17-openclaw-evidence-helpers..codex/stack-18-report-tool-displays-split
```

## Split Order

### PR 1: Engineering Health Gate

Scope:

- `.github/workflows/ci.yml`
- `.gitignore`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `frontend/tsconfig.json`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/quality/backend-test-strategy.md`
- `docs/quality/branch-split-plan.md`
- `scripts/change_inventory.ps1`
- `scripts/quality_gate.ps1`

Intent:

- restore frontend typecheck;
- make Ruff executable locally and in CI, with syntax-level `E9` enabled first;
- keep local tool artifacts and external `search-gateway/` checkouts out of
  main repo status;
- document the layered backend test strategy and branch split process.

Validation:

```powershell
./scripts/quality_gate.ps1
git status --short --branch
```

### PR 2: Backend OpenClaw And Research Flow

Scope:

- `backend/app/api/openclaw.py`
- `backend/app/services/application/openclaw_*.py`
- `backend/app/services/application/graph_app_service.py`
- `backend/app/services/consumer/openclaw_research_brief.py`
- `backend/app/services/consumer/research_ingest.py`
- matching tests under `backend/tests/api/`, `backend/tests/services/application/`,
  and `backend/tests/consumer/`.

Intent:

- isolate OpenClaw orchestration, session, route, and research-ingest behavior;
- keep this PR focused on backend request-to-project flow.

Validation:

```powershell
cd backend
uv run ruff check app tests
uv run --python 3.12 pytest tests\consumer\test_research_ingest.py tests\api\test_openclaw_routes.py tests\services\application\test_openclaw_orchestrator.py -v --tb=short --no-cov
```

### PR 3: Backend Consumer Simulation And Reporting

Scope:

- `backend/app/services/consumer/`
- `backend/app/services/report_agent.py`
- `backend/app/services/simulation_*.py`
- `backend/app/api/consumer*.py`
- `backend/app/api/report.py`
- matching consumer, report, and simulation tests.

Intent:

- keep consumer simulation, report rendering, report-agent behavior, and
  simulation runtime changes together;
- avoid mixing frontend UI review with backend runtime review.

Validation:

```powershell
cd backend
uv run ruff check app tests
.venv\Scripts\python.exe -m pytest tests\consumer tests\api\test_consumer_routes.py tests\api\test_report_api_response.py tests\services\test_report_agent.py -v --tb=short --no-cov
```

If this command becomes too slow, split PR 3 into:

- consumer models and graph building;
- society runtime;
- report agent and report APIs.

Recommended stack mapping after the backend report-agent slimming work:

- PR 3a: report foundations and manager/logging modules:
  `codex/stack-03-report-foundations` and `codex/stack-10-report-manager-module`
  through `codex/stack-11-report-logging-module`.
- PR 3b: consumer report generation mixins:
  `codex/stack-12-consumer-report-mixin`,
  `codex/stack-13-report-tool-mixin`, and
  `codex/stack-15-consumer-report-mixin-split`.
- PR 3c: any remaining simulation/runtime files, after a fresh inventory proves
  they are not bundled with unrelated frontend changes.

### PR 4: Frontend OpenClaw Workspace

Scope:

- `frontend/src/views/OpenClawWorkspaceView.vue`
- `frontend/src/components/openclaw/`
- `frontend/src/api/openclaw.ts`
- `frontend/src/router/index.ts`
- `frontend/src/utils/openclawBusinessStatus.ts`
- matching frontend tests.

Intent:

- isolate the OpenClaw-specific UI workflow and API contracts.

Validation:

```powershell
cd frontend
npm run typecheck
npx vitest run tests\openclawContracts.test.js tests\openclawUxV2.test.js
```

### PR 5: Frontend Report And Consumer UI

Scope:

- `frontend/src/components/Step4Report.vue`
- `frontend/src/components/Step5Interaction.vue`
- `frontend/src/components/consumer/`
- `frontend/src/api/report.ts`
- `frontend/src/utils/reportContent.ts`
- `frontend/src/utils/safeMarkdown.ts`
- matching frontend tests.

Intent:

- keep report UX, action workspace, markdown safety, and consumer panels in one
  UI-focused review.
- keep the later architecture-only splits (`stack-14`, `stack-16`, `stack-18`,
  `stack-19`, `stack-20`) separate from behavior changes when possible.

Validation:

```powershell
cd frontend
npm run typecheck
npx vitest run tests\reportContent.test.js tests\safeMarkdown.test.js tests\safeMarkdownTableAffordance.test.js tests\e2eRepairContracts.test.js
```

Recommended stack mapping after frontend slimming:

- PR 5a: Step4 composables and report panels:
  `codex/stack-05-step4-report-ui-panels`,
  `codex/stack-08-step4-composables`, and
  `codex/stack-14-step4-style-extraction`.
- PR 5b: Step5 component shells and composables:
  `codex/stack-06-step5-component-shells` through
  `codex/stack-07-step5-composables`.
- PR 5c: report workflow/tool display and consumer utility splits:
  `codex/stack-16-workflow-panel-style-extraction`,
  `codex/stack-18-report-tool-displays-split`,
  `codex/stack-19-consumer-confidence-helpers`, and
  `codex/stack-20-consumer-branching-helpers`.

### PR 6: Product Docs, Locales, And Demo Seed Material

Scope:

- `docs/architecture/`
- `docs/product/`
- `locales/`
- `seed-document/`
- product-facing README updates, if any.

Intent:

- keep copy, localized labels, and demo artifacts out of behavior-heavy PRs.

Validation:

```powershell
./scripts/quality_gate.ps1 -FrontendOnly
```

## Review Rules

- Do not merge the staging branch directly.
- Each PR should start from the target base and cherry-pick or reapply only its
  listed scope.
- Each PR should include a fresh `./scripts/change_inventory.ps1` output in the
  PR description.
- If a PR still touches more than 80 files, split it again.
- Keep `search-gateway/` changes in `https://github.com/XiangXi011/web_search.git`
  unless a separate PR explicitly introduces a submodule or vendored service.
