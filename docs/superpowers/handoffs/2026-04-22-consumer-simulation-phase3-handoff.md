# Consumer Simulation Phase 3 交接文档

## 1. 交接结论

`consumer_test` 的 Phase 3 已在 `codex/consumer-simulation-phase1` 上完成并通过当前验收。

当前基线已经具备：

- Phase 3A：双源 Tiered RAG 研究底座
- Phase 3B：研究员干预与 branch rerun
- Phase 3C：社会化沙盘升级
- Phase 3D：研究资产化与对比工作台

## 2. 当前工作区

- 仓库根目录：`D:\project\MiroFish`
- 实际实现 worktree：`D:\project\MiroFish\.worktrees\consumer-simulation-phase1`
- 当前分支：`codex/consumer-simulation-phase1`

## 3. Phase 3 关键代码位置

### 3.1 Phase 3A：研究底座

- `backend/app/services/consumer/source_registry.py`
- `backend/app/services/consumer/document_ingest.py`
- `backend/app/services/consumer/url_ingest.py`
- `backend/app/services/consumer/finding_distiller.py`
- `backend/app/services/consumer/lane_b_provider.py`
- `backend/app/services/consumer/project_research_persistence.py`
- `backend/app/services/consumer/research_ingest.py`

结果：

- 上传文件与 URL 会落到 `backend/uploads/projects/<project_id>/research/`
- 项目级 research artifacts 会持久化 `findings.json` 与 `research_snapshot.json`
- Step 4/5 已能展示 citation-ready findings、source catalog 和 retrieval traces

### 3.2 Phase 3B：干预与分支

- `backend/app/services/consumer/intervention_manager.py`
- `backend/app/api/simulation.py`
- `backend/app/services/simulation_runner.py`
- `frontend/src/components/Step3Simulation.vue`
- `frontend/src/components/Step4Report.vue`
- `frontend/src/components/Step5Interaction.vue`

结果：

- 支持 `clarification_injection / revised_claim_injection / evidence_reveal`
- 支持 fork round、branch resume、branch status、branch comparison
- Step 3/4/5 已具备 branch-aware workflow

### 3.3 Phase 3C：社会化沙盘

- `backend/app/services/consumer/social_topology.py`
- `backend/app/services/consumer/cascade_metrics.py`
- `backend/app/services/consumer/event_engine.py`
- `backend/app/services/consumer/orchestrator.py`
- `backend/app/services/consumer/scoring.py`
- `backend/app/services/consumer/report_context.py`
- `frontend/src/utils/consumerMode.js`
- `frontend/src/components/Step3Simulation.vue`
- `frontend/src/components/Step4Report.vue`

结果：

- persona 被映射到 `bridge / amplifier / skeptic / lurker / regular`
- propagation event 已具备 community / role / cross-community metadata
- `cascade_metrics` 已在 API、Step 3、Step 4、Step 5 prompt 中打通

### 3.4 Phase 3D：研究资产与对比

- `backend/app/services/consumer/asset_library.py`
- `backend/app/services/consumer/comparison_engine.py`
- `backend/app/api/report.py`
- `frontend/src/api/report.js`
- `frontend/src/components/Step4Report.vue`
- `frontend/src/components/Step5Interaction.vue`
- `frontend/src/utils/consumerMode.js`

结果：

- 支持导出 `consumer_research_pack`
- 支持 persisted comparison snapshot
- 支持三类比较：
  - `run_vs_run`
  - `branch_vs_base`
  - `project_vs_project`
- Step 4 已有 Research Assets / Comparison Workspace
- Step 5 已有 comparison-aware follow-up prompts

## 4. 新增/重要 API

### 4.1 Simulation API

- `GET /api/simulation/<simulation_id>/consumer-summary`
- `POST /api/simulation/<simulation_id>/branches`
- `GET /api/simulation/<simulation_id>/branches`
- `POST /api/simulation/<simulation_id>/branches/<branch_id>/interventions`
- `POST /api/simulation/<simulation_id>/branches/<branch_id>/resume`
- `GET /api/simulation/<simulation_id>/branches/<branch_id>/status`
- `GET /api/simulation/<simulation_id>/branches/<branch_id>/comparison`

### 4.2 Report API

- `POST /api/report/research-assets/export`
- `GET /api/report/research-assets`
- `GET /api/report/research-assets/<asset_id>`
- `POST /api/report/compare`
- `GET /api/report/comparisons`
- `GET /api/report/comparisons/<comparison_id>`

## 5. 当前验收结果

### 5.1 后端

命令：

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend
.\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/integration
```

结果：

- `270 passed`

### 5.2 前端

命令：

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1
node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js
```

结果：

- `61 passed`

### 5.3 构建

命令：

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend
npm run build
```

结果：

- 构建成功

## 6. 当前已知限制

- `Lane B` 已有 grounded provider 路径和 deterministic fallback，但更强的真实外部 provider 仍是下一阶段优化点
- `project_vs_project` 对比当前优先使用项目 research artifacts 与发现差异；若项目缺少 run-level 结果，则接受度字段会保守显示
- Kimi For Coding 在 prepare 阶段仍偏慢
- `response_format=json_object` 仍依赖 proxy 兼容
- 前端仍保留两个非阻断 warning：
  - `pendingUpload.js` 动静态导入混用
  - chunk size warning

## 7. 下一步建议

优先建议进入 Phase 4，而不是回头重做 Phase 3：

1. 升级更强的真实 research / RAG provider
2. 优化 prepare 性能与更大样本规模
3. 把 comparison workspace 扩展为 benchmark / category memory / recurring insight library
4. 继续做资产复用，但保持显式 lineage 与可追溯性

## 8. 参考文档

- `PRD.md`
- `docs/superpowers/specs/2026-04-21-consumer-simulation-phase3-roadmap-design.md`
- `docs/superpowers/plans/2026-04-21-consumer-simulation-phase3-master-plan.md`
