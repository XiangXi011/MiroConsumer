# MiroConsumer 项目交接文档

---

## 1. 文档元数据

| 字段 | 值 |
|---|---|
| 日期 | 2026-04-24 |
| 分支 | `codex/phase5-closure` |
| 最新提交 | `fc7049d` docs: add phase7 productionization plan |
| 工作区 | `D:\project\MiroFish\.worktrees\phase5a-identity` |
| 仓库根 | `D:\project\MiroFish` |
| 主分支 | `main` |
| 产品名称 | MiroConsumer |

---

## 2. 一页纸执行摘要

MiroConsumer 是一个 AI 驱动的消费者传播测试平台，用于在产品上线前验证概念（concept）和文案（copy）的市场接受度与传播风险。它区别于传统的静态评分工具，核心在于模拟消费者之间的社交传播效应：第一轮消费者仅对原始概念/文案产生第一印象，后续轮次中消费者相互影响，产生放大、质疑、误读和态度迁移。系统最终输出带有结构化 VOC（消费者原声）证据的传播报告。

当前代码库已完成 Phase 1~Phase 6E 的全部交付，具备概念测试、文案测试、包装测试、A/B 测试、价格测试五种任务类型，支持分支干预（branch/intervention）、研究资产化、对比工作台、基准回放（benchmark replay）、证据验证与置信度评分。Phase 7 已规划但尚未开始，目标是将当前基于文件系统和进程内线程的执行骨架升级为可生产化部署的数据库 + 队列架构。

全量后端测试 723 passed，前端测试 172 passed，`npm run build` 通过，git diff --check clean。唯一剩余警告是 `zep_cloud` 与 Python 3.14 的 Pydantic v1 兼容警告（已有，非阻断）。

---

## 3. 产品定位与支持的工作流

### 3.1 产品定位

MiroConsumer 回答的问题：

- 这个概念/文案在首次接触时会引起兴趣还是犹豫？
- 哪些卖点会在消费者之间的对话中自然传播？
- 哪些说法可能被放大、质疑或误读？
- 不同消费者细分（拥护者、阻碍者、观望者）如何形成？
- 上线前应该改写什么？

### 3.2 支持的测试类型

| 任务类型 | 说明 |
|---|---|
| `concept_test` | 评估产品概念本身是否具有说服力、可信度或令人困惑 |
| `copy_feedback` | 看哪些文案触发兴趣、怀疑、分享或扭曲 |
| `packaging_test` | 测试包装描述、外观线索和信任信号 |
| `ab_test` | 多版本（variant）对比测试 |
| `price_test` | 测试价格接受度、阻力点和价格上下文感知 |

### 3.3 标准六步工作流

1. **创建消费者测试** — 提交包含概念、文案、受众、场景、研究目标的结构化 brief。
2. **构建消费者图谱** — 将 claims、drivers、anxieties 和受众细分转换为传播就绪的图结构。
3. **准备模拟** — 生成消费者画像包（persona pack）和运行时配置。
4. **运行传播模拟** — Round 0 第一印象，Round 1-N 传播演化。
5. **生成消费者报告** — 查看接受度迁移、共鸣点、争议点、误读和代表性 VOC。
6. **追问** — 向报告 agent 或代表性消费者追问深层原因。

### 3.4 产品面模式

- **唯一产品面模式**：`consumer_test` — 所有新建项目默认走此模式。
- **`project_type=default`** — 降级为维护者专用内部兼容模式，不在 UI 中暴露。该模式的原有流程仍然可用，但不再面向终端用户。

---

## 4. 当前工程状态与验证证据

### 4.1 自动化验证结果（Phase 6E 结束时的最新基线）

| 验证项 | 命令 | 结果 |
|---|---|---|
| 后端全量 pytest | `python -m pytest tests/ --tb=short -q` | 723 passed, 1 warning in 108.97s |
| 前端 node 测试 | `node --test tests/*.test.js tests/composables/*.test.js` | 172 passed |
| 前端构建 | `npm run build` | success |
| Git diff whitespace | `git diff --check` | clean |

> 注：唯一的 1 个 warning 是既有 `zep_cloud` 与 Python 3.14 的 Pydantic v1 兼容警告，与当前代码无关。

### 4.2 关键测试覆盖矩阵

| 测试域 | 文件数 | 覆盖范围 |
|---|---|---|
| API 路由 | `tests/api/` | 消费者路由、干预、分支、规范路由、项目类型契约 |
| 消费者域服务 | `tests/consumer/` | 混合内核、内核适配器、编排器、评分、报告上下文、证据验证、置信度、基准回放、干预管理、社会拓扑、级联指标、画像包、Lane B 治理、研究摄入、来源质量、文档/URL 摄入、检索、发现提炼、比较引擎、资产库、项目研究持久化、状态访问器、API 守卫、访问策略、事件引擎、消费者应用服务、消费者应用服务 provider 边界 |
| 契约测试 | `tests/contracts/` | 消费者契约（请求/响应 schema） |
| 模型 | `tests/models/` | Project 模型、Task 模型 |
| 仓库 | `tests/repositories/` | 文件系统仓库（filesystem repositories） |
| 应用服务 | `tests/services/application/` | 任务执行器可观测性 |
| 工具 | `tests/utils/` | LLM 客户端 JSON 兼容性 |
| 前端 | `frontend/tests/` | 消费者 brief、消费者模式、待上传状态、图 API、消费者 API 行为、组合式函数状态 |

### 4.3 尚未执行的验证

- **全链路手动冒烟测试（whole-phase smoke）**：已延期，等待用户触发。这是 Phase 6D 就绪门中定义的唯一未执行验收项。

---

## 5. 架构总览

### 5.1 技术栈

| 层 | 技术 |
|---|---|
| 前端框架 | Vue 3 + Vite + vue-router + vue-i18n |
| 前端图表 | D3 |
| 后端框架 | Flask + flask-cors |
| 后端依赖管理 | uv (Python) |
| LLM 客户端 | 基于 OpenAI SDK 格式的兼容层，默认 `qwen-plus` via 阿里百炼 |
| 知识图谱 | Zep (getzep.com) |
| 模拟骨架 | 基于 OASIS (Open Agent Social Interaction Simulations) |
| 持久化 | 文件系统 JSON/JSONL（Phase 7 前无数据库） |
| 后台任务 | `threading.Thread(daemon=True)`（Phase 7 前无队列） |

### 5.2 后端分层架构

```
frontend (Vue/Vite)  <--HTTP/JSON-->  Flask API Routes
                                            |
                                    Application Services
                                    (请求到领域编排层)
                                            |
                                    Consumer Domain Services
                                    (业务逻辑核心)
                                            |
                                    Repositories (ABC)
                                    <-- 文件系统实现 -->
                                            |
                                    ProjectManager + storage/
                                    (JSON/JSONL on disk)
```

#### 5.2.1 API 路由层 (`backend/app/api/`)

| 蓝图 | 文件 | 职责 |
|---|---|---|
| `graph_bp` (`/api/graph`) | `graph.py` | 图构建、消费者 brief 摄入、来源质量摘要 |
| `simulation_bp` (`/api/simulation`) | `simulation.py` | 模拟创建、prepare、start、consumer-summary、分支/干预/恢复/状态/对比（legacy shim） |
| `report_bp` (`/api/report`) | `report.py` | 报告生成、研究资产导出/列表/详情、对比创建/列表/详情、基准注册/回放 |
| `consumer_bp` (`/api/consumer`) | `consumer.py` | **规范消费者路由**：simulation consumer-summary、branches、interventions、research-assets、comparisons |

> 消费者规范路由 (`/api/consumer/*`) 与 legacy 路由 (`/api/simulation/*`、`/api/report/*`) 并存；legacy 路由作为兼容 shim，内部委托给 ConsumerAppService。

#### 5.2.2 应用服务层 (`backend/app/services/application/`)

| 服务 | 文件 | 职责 |
|---|---|---|
| `GraphAppService` | `graph_app_service.py` | 图构建编排、persona pack 解析、brief 转换 |
| `SimulationAppService` | `simulation_app_service.py` | 模拟生命周期（create/prepare/run）编排 |
| `ReportAppService` | `report_app_service.py` | 报告生成编排 |
| `BranchAppService` | `branch_app_service.py` | 分支创建、干预注入、状态恢复 |
| `BenchmarkAppService` | `benchmark_app_service.py` | 基准注册与回放 |
| `ConsumerAppService` | `consumer_app_service.py` | 消费者测试端到端编排（研究/provider 边界已解耦） |
| `TaskExecutor` | `task_executor.py` | 统一 prepare/run/report 执行与重试语义 |

#### 5.2.3 消费者领域服务层 (`backend/app/services/consumer/`)

按功能域分组：

**Brief / 模型 / 适配**
- `models.py` — 消费者领域模型（`ConsumerBusinessBrief`、`ResearchFinding`、`PropagationEvent`、`ConsumerPhase2Summary` 等）
- `brief_adapter.py` — 将前端 payload 转换为规范 brief

**图谱构建**
- `graph_builder.py` — 从 brief 构建消费者传播图（nodes/edges/visibility tiers）
- `persona_pack.py` / `persona_pack_registry.py` — 画像包资产化管理（generic/industry/category/geography/custom）

**研究摄入与来源治理（Phase 2~4A）**
- `research_ingest.py` — 研究 findings 生成与解析
- `source_registry.py` — 来源注册
- `source_quality.py` — 来源质量评分（trust tier、freshness、coverage）
- `document_ingest.py` / `url_ingest.py` — 文件与 URL 摄入
- `finding_distiller.py` — findings 提炼
- `lane_b_provider.py` — Lane B（公共网络补充）provider
- `retrieval.py` — 检索与治理痕迹记录
- `project_research_persistence.py` — 项目级研究产物持久化

**模拟运行时内核（Phase 6C 升级）**
- `kernel_adapter.py` — 内核适配器 ABC（`SimulationKernelAdapter`、`SimulationKernelResult`）
- `legacy_kernel.py` — 遗留确定性内核（byte-for-byte 回退）
- `hybrid_kernel.py` — 混合内核：使用 prior-round 状态、画像特质、发现多样性和拓扑信号产生多样化引用和有意义的态度迁移
- `propagation_state.py` — 每 agent 轮次间可变状态（态度历史、参与度历史、累积风险暴露、社会强化计数）
- `orchestrator.py` — 消费者模拟编排（Round 0 隐藏 `Restricted/Propagation_Only`，Round 2+ 高搜索画像可见全部节点）
- `access_policy.py` — 可见性规则解析
- `event_engine.py` — 传播事件分类与构建
- `social_topology.py` — 社会拓扑映射（bridge/amplifier/skeptic/lurker/regular）
- `cascade_metrics.py` — 级联指标计算

**评分与报告**
- `scoring.py` — 消费者评分（态度迁移 + 证据 bundle + 置信度附加）
- `report_context.py` — 报告上下文构建（含 trigger_finding_ids、event_ids、因果链）
- `confidence_scoring.py` — 置信度评分
- `evidence_validator.py` — 证据验证门控（`weak_support` / `insufficient_support` 标记）

**干预与分支（Phase 3B）**
- `intervention_manager.py` — 干预管理（`clarification_injection`、`revised_claim_injection`、`evidence_reveal`）

**资产与对比（Phase 3D~4）**
- `asset_library.py` — 研究资产库
- `comparison_engine.py` — 对比引擎（`run_vs_run`、`branch_vs_base`、`project_vs_project`）
- `benchmark_registry.py` / `benchmark_replay.py` — 基准注册与回放

**API 守卫与状态访问**
- `api_guard.py` — 消费者 API 守卫
- `simulation_state_accessor.py` — 消费者模拟状态访问器

#### 5.2.4 模拟管理层（与 OASIS 骨架交互）

| 模块 | 文件 | 职责 |
|---|---|---|
| `SimulationManager` | `simulation_manager.py` | 模拟生命周期管理（create/prepare/run/save） |
| `SimulationRunner` | `simulation_runner.py` | 模拟运行内核（consumer runner、branch runner、stateful branch replay） |
| `OasisProfileGenerator` | `oasis_profile_generator.py` | OASIS profile 生成 |
| `SimulationConfigGenerator` | `simulation_config_generator.py` | 模拟配置生成 |
| `PrepareManifest` | `prepare_manifest.py` | prepare 产物元数据持久化与复用计数 |
| `ReportAgent` | `report_agent.py` | 报告 agent 渲染与上下文注入 |

#### 5.2.5 仓库层 (`backend/app/repositories/`)

- `__init__.py` — 仓库 ABC（`ProjectRepository`、`SimulationRepository`、`BranchRepository`、`ReportRepository`、`BenchmarkRepository`、`ConsumerStateRepository`、`ConsumerProjectResearchProvider`）
- `filesystem.py` — 文件系统实现（当前唯一激活实现）

> Phase 7 将引入 SQLAlchemy 数据库实现，`DB_URL` 存在时自动切换。

#### 5.2.6 基础设施 / 工具层

| 模块 | 文件 | 职责 |
|---|---|---|
| `LLMClient` | `utils/llm_client.py` | 统一 LLM 调用、JSON 兼容性回退、fenced block 清理、`<think>` 剥离 |
| `Config` | `config.py` | 应用配置（LLM、Zep、Boost） |
| `logger.py` | `utils/logger.py` | 日志设置 |
| `retry.py` | `utils/retry.py` | 重试工具 |
| `file_parser.py` | `utils/file_parser.py` | 文件解析 |
| `locale.py` | `utils/locale.py` | 本地化工具 |

### 5.3 前端架构

```
frontend/src/
  views/
    Home.vue              # 消费者 brief 输入（唯一入口，无模式切换器）
    MainView.vue          # 主布局
    SimulationView.vue    # 模拟总览
    SimulationRunView.vue # 模拟运行
    ReportView.vue        # 报告视图
    InteractionView.vue   # 交互/追问视图
    Process.vue           # 流程页
  components/
    Step2EnvSetup.vue     # Step 2: 环境设置（research findings、来源质量展示）
    Step3Simulation.vue   # Step 3: 模拟运行（branch/intervention 工作区外壳）
    Step4Report.vue       # Step 4: 报告（consumer header、对比、研究资产工作区外壳）
    Step5Interaction.vue  # Step 5: 交互/追问（对比快照工作区）
    consumer/
      BranchInterventionWorkspace.vue    # 分支/干预工作区
      ComparisonSnapshotWorkspace.vue    # 对比快照工作区
      ComparisonWorkspace.vue            # 对比工作台
      ConsumerReportHeader.vue           # 消费者报告头部
      ResearchAssetWorkspace.vue         # 研究资产工作区
  composables/consumer/
    useBranchInterventionState.js        # 分支/干预状态组合式函数
    useComparisonState.js                # 对比状态组合式函数
    useResearchAssetState.js             # 研究资产状态组合式函数
  api/
    consumer.js           # 规范消费者 API（所有消费者端点）
    ontologyFormData.js   # 表单数据构建器（默认 consumer_test）
    graph.js              # 图 API（re-export ontologyFormData）
    report.js             # 报告 API（consumer 函数 re-export 自 consumer.js）
    simulation.js         # 模拟 API（legacy shim）
  store/
    pendingUpload.js      # 待上传状态（含 projectType、researchMode）
  utils/
    consumerBrief.js      # brief 构造与规范化
    consumerMode.js       # 消费者模式工具（事件标签、置信度 badge、因果追问 prompt）
  i18n/                   # 国际化（en.json、zh.json）
  router/index.js         # 路由（懒加载、手动 chunking）
```

### 5.4 关键模块依赖关系

```
Home.vue (consumer_test only)
  -> graph.js / ontologyFormData.js
    -> GraphAppService (backend)
      -> graph_builder.py + persona_pack_registry.py
      -> research_ingest.py + source_quality.py

Step3Simulation.vue
  -> SimulationAppService
    -> simulation_manager.py
      -> SimulationRunner
        -> orchestrator.py
          -> HybridSimulationKernel (default) / LegacySimulationKernel (fallback)
          -> access_policy.py + event_engine.py + social_topology.py
        -> propagation_state.py (round-to-round state)

Step4Report.vue
  -> ReportAppService
    -> report_agent.py
      -> report_context.py + scoring.py + evidence_validator.py + confidence_scoring.py
    -> comparison_engine.py + asset_library.py
    -> benchmark_registry.py + benchmark_replay.py

ConsumerAppService (跨层编排)
  -> ConsumerProjectResearchProvider (ABC)
  -> ConsumerStateRepository (ABC)
```

---

## 6. 阶段历史：Phase 1 ~ Phase 6E + Phase 7 规划

### Phase 1 — 消费者测试基线（2026-04-20~21）

- 迁入 `BusinessBrief / persona / scoring / report schema`
- 落地 `concept_test + copy_feedback + propagation-aware simulation`
- 消费者项目元数据持久化（`project_type / consumer_brief / consumer_context`）
- Round 0 / Round 1-N 语义、VOC 展示
- 前端 Step 2-5 消费者模式适配
- 中英 locale 补齐

### Phase 2 — Realism 升级（2026-04-21）

- `research_mode / auto_enrich`：基于 brief 内容的确定性合成研究
- Research findings 进入 graph 与 simulation config
- Persona-aware knowledge visibility（Round 0 仅 Initial，Round 1+ Propagation_Only 全局可见，Restricted 仅高搜索+高认知可见）
- Typed propagation events（社区/角色/跨社区元数据）
- Causal summary / causal report context
- Step 2-5 前端承接 research / event / causal 信息

### Phase 3 — 研究底座 + 干预 + 社会拓扑 + 资产化（2026-04-21~22）

- **Phase 3A**：双源 Tiered RAG 研究底座（source registry、document/url ingest、finding distiller、lane_b_provider、project research persistence）
- **Phase 3B**：研究员干预与分支 rerun（intervention_manager、branch fork/resume/status/comparison）
- **Phase 3C**：社会化沙盘升级（social topology、 cascade metrics、propagation event 社区元数据）
- **Phase 3D**：研究资产化与对比工作台（asset library、comparison engine、三类比较：run_vs_run / branch_vs_base / project_vs_project）

### Phase 4 — 可信度升级 + 测试扩展 + 效率升级（2026-04-22）

- **Phase 4A**：来源质量治理（source_quality.py）、证据验证（evidence_validator.py）、置信度评分（confidence_scoring.py）、基准回放（benchmark_registry.py / benchmark_replay.py）
- **Phase 4B**：测试品类扩展 — 新增 `packaging_test`、`ab_test`、`price_test`
- **Phase 4C**：工程效率升级 — LLMClient 共享 JSON 兼容层、prepare manifest 持久化、前端路由懒加载与手动 chunking

### Phase 5 — 产品与架构清理（2026-04-22~23）

- 产品身份全面统一为 `MiroConsumer`
- API 路由瘦身：Flask 路由退化为薄编排壳，应用服务拥有请求到领域编排
- 仓库抽象层落地（ filesystem-backed ABCs）
- 任务执行器抽象（`TaskExecutor`，默认 `ThreadTaskExecutor`）
- 消费者边界上下文确立（`consumer_test` 作为真实 bounded context）
- 规范消费者路由（`/api/consumer/*`）+ legacy shim
- 证据门控：executive summary 风格输出阻止无支持的高风险 findings
- 全量测试稳定至 565 passed

### Phase 6 — 产品面确立 + 内核升级 + 架构债务清理（2026-04-23~24）

- **Phase 6A**：消费者唯一产品面 — 移除模式切换器，`consumer_test` 为唯一产品模式，`project_type=default` 降级为维护者专用；规范消费者前端 API（`consumer.js`）；产品面文档测试（`test_phase6a_product_surface.py`）；项目类型持久化契约测试（`test_phase6a_project_type_contract.py`）
- **Phase 6B**：前端模块化 — Step3/4/5 Vue 组件分解为子组件和 composables（BranchInterventionWorkspace、ComparisonWorkspace、ResearchAssetWorkspace、ConsumerReportHeader、ComparisonSnapshotWorkspace + 对应 composables）
- **Phase 6C**：保留优先的内核升级 — 引入 `SimulationKernelAdapter` ABC + `LegacySimulationKernel`（确定性回退）+ `HybridSimulationKernel`（跨轮次状态、画像特质、引用多样性、拓扑信号）；`PropagationState` 每 agent 轮次间可变状态；消费者 runner 和 branch runner 维护 `agent_states` dict；确定性种子 RNG
- **Phase 6D**：冒烟就绪门 — 仅文档和注释清理，为 whole-phase smoke 定义验收标准
- **Phase 6E**：架构与产品债务收尾 — ConsumerAppService 研究/持久化边界解耦；Step3 consumer 单流 UI 对齐；BranchInterventionWorkspace 持久化分支重载后状态轮询恢复；前端 API 行为契约测试（`consumerApi.behavior.test.js`）

### Phase 7 — 生产化（已规划，未开始）

Phase 7 目标：让 MiroConsumer 能够承受进程重启、超越单实例运行、在不接受本地文件系统耐久性和进程内守护线程的环境中部署。

**Phase 7A — 持久化 / 数据库**
- 仓库 ABC 契约强化（in-memory harness 测试）
- 关系型数据库 schema 设计（projects、simulations、branches、interventions、reports、benchmarks）
- SQLAlchemy 实现 + Alembic 迁移
- `DB_URL` 存在时自动切换数据库实现，不存在时回退文件系统（零回归）

**Phase 7B — 耐久工作进程 / 队列**
- `TaskExecutor` 扩展 `get_status(trace_id)`
- `QueueTaskExecutor` 实现（消息代理或 SQLite 队列零依赖回退）
- 工作进程启动时恢复 `PENDING` / `RUNNING` 任务
- prepare/run/report 的幂等性规则

**Phase 7C — 多实例安全**
- 乐观版本号 / 数据库 advisory locks
- 分支 fork 隔离（原子复制 pre-fork 状态）
- 报告生成隔离（单 simulation 锁）
- 文件系统回退模式使用文件锁（`fcntl` / `msvcrt`）

---

## 7. 重要文件地图

### 7.1 入口文件

| 路径 | 说明 |
|---|---|
| `backend/run.py` | Flask 后端启动入口 |
| `frontend/src/main.js` | Vue 前端入口 |
| `package.json` | 根级 npm scripts（setup、dev、build） |
| `frontend/package.json` | 前端依赖与 scripts |
| `backend/pyproject.toml` | Python 依赖（uv 管理） |

### 7.2 配置与契约

| 路径 | 说明 |
|---|---|
| `.env.example` | 环境变量模板 |
| `backend/app/config.py` | Flask 配置类 |
| `backend/app/contracts/consumer_contracts.py` | 消费者请求/响应 schema 契约 |
| `backend/app/contracts/errors.py` | 规范错误响应形状 |

### 7.3 核心后端模块

| 路径 | 说明 |
|---|---|
| `backend/app/__init__.py` | Flask 应用工厂（蓝图注册、CORS、请求日志中间件） |
| `backend/app/api/consumer.py` | **规范消费者路由** |
| `backend/app/api/simulation.py` | 模拟路由（legacy shim 含消费者端点） |
| `backend/app/api/report.py` | 报告路由（legacy shim 含消费者端点） |
| `backend/app/api/graph.py` | 图构建路由 |
| `backend/app/services/application/consumer_app_service.py` | 消费者端到端编排 |
| `backend/app/services/application/task_executor.py` | 任务执行器 ABC + ThreadTaskExecutor |
| `backend/app/services/consumer/hybrid_kernel.py` | 混合消费者模拟内核 |
| `backend/app/services/consumer/orchestrator.py` | 消费者模拟编排器 |
| `backend/app/services/consumer/scoring.py` | 消费者评分 |
| `backend/app/services/consumer/report_context.py` | 报告上下文 |
| `backend/app/services/consumer/evidence_validator.py` | 证据验证 |
| `backend/app/services/consumer/intervention_manager.py` | 干预管理 |
| `backend/app/services/simulation_runner.py` | 模拟运行器（consumer runner、branch runner） |
| `backend/app/services/simulation_manager.py` | 模拟生命周期管理 |
| `backend/app/repositories/__init__.py` | 仓库 ABC |
| `backend/app/repositories/filesystem.py` | 文件系统仓库实现 |
| `backend/app/utils/llm_client.py` | 统一 LLM 客户端 |

### 7.4 核心前端模块

| 路径 | 说明 |
|---|---|
| `frontend/src/views/Home.vue` | 消费者 brief 输入（唯一产品入口） |
| `frontend/src/components/Step3Simulation.vue` | Step 3 模拟运行 |
| `frontend/src/components/Step4Report.vue` | Step 4 报告 |
| `frontend/src/components/Step5Interaction.vue` | Step 5 交互追问 |
| `frontend/src/api/consumer.js` | **规范消费者 API 模块** |
| `frontend/src/api/ontologyFormData.js` | 表单数据构建器（默认 `consumer_test`） |
| `frontend/src/store/pendingUpload.js` | 待上传状态管理 |
| `frontend/src/utils/consumerBrief.js` | brief 构造工具 |
| `frontend/src/utils/consumerMode.js` | 消费者模式工具 |
| `frontend/src/router/index.js` | 路由配置（懒加载、手动 chunking） |
| `locales/en.json` / `locales/zh.json` | 国际化文案 |

### 7.5 测试文件

| 路径 | 说明 |
|---|---|
| `backend/tests/consumer/test_hybrid_kernel.py` | 混合内核测试 |
| `backend/tests/consumer/test_kernel_adapter.py` | 内核适配器契约测试 |
| `backend/tests/consumer/test_orchestrator.py` | 编排器测试 |
| `backend/tests/consumer/test_evidence_validator.py` | 证据验证测试 |
| `backend/tests/consumer/test_consumer_app_service.py` | 消费者应用服务测试 |
| `backend/tests/consumer/test_consumer_app_service_provider_boundary.py` | provider 边界测试 |
| `backend/tests/api/test_consumer_canonical_routes.py` | 规范消费者路由测试 |
| `backend/tests/api/test_consumer_routes.py` | 消费者路由测试 |
| `backend/tests/api/test_consumer_interventions.py` | 干预路由测试 |
| `backend/tests/api/test_phase6a_project_type_contract.py` | 项目类型持久化契约测试 |
| `backend/tests/test_phase6a_product_surface.py` | 产品面文档测试 |
| `backend/tests/contracts/test_consumer_contracts.py` | 消费者契约 schema 测试 |
| `backend/tests/services/application/test_task_executor_observability.py` | 任务执行器可观测性测试 |
| `frontend/tests/consumerApi.behavior.test.js` | 消费者 API 行为契约测试 |
| `frontend/tests/consumerApi.smoke.test.js` | 消费者 API 冒烟测试 |

### 7.6 文档

| 路径 | 说明 |
|---|---|
| `README.md` / `README-ZH.md` | 产品 README |
| `PRD.md` | 产品需求文档 |
| `docs/superpowers/handoffs/` | 阶段交接文档（Phase 1~6E） |
| `docs/superpowers/plans/` | 阶段计划文档 |
| `docs/superpowers/specs/` | 设计规格文档 |
| `docs/product/` | 产品方案概述 |

---

## 8. 本地运行方式与必需环境变量

### 8.1 前置条件

| 工具 | 版本 | 检查命令 |
|---|---|---|
| Node.js | 18+ | `node -v` |
| Python | 3.11+ 推荐 | `python --version` |
| uv | latest | `uv --version` |

### 8.2 环境变量配置

```bash
cp .env.example .env
```

必需变量：

```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=your_zep_api_key_here
```

可选加速变量（如不需要，env 文件中不要出现）：

```env
LLM_BOOST_API_KEY=your_api_key_here
LLM_BOOST_BASE_URL=your_base_url_here
LLM_BOOST_MODEL_NAME=your_model_name_here
```

### 8.3 安装依赖

```bash
npm run setup:all
```

或分步：

```bash
npm run setup          # 安装前端依赖
npm run setup:backend  # uv sync Python 依赖
```

### 8.4 启动开发服务器

```bash
npm run dev
```

- 前端：`http://localhost:3000`
- 后端 API：`http://localhost:5001`

分步启动（如需）：

```bash
npm run backend   # 仅启动后端
npm run frontend  # 仅启动前端
```

### 8.5 构建前端

```bash
cd frontend
npm run build
```

或从根目录：

```bash
npm run build
```

### 8.6 Docker（可选）

```bash
cp .env.example .env
docker compose up -d
```

默认端口：3000（前端）、5001（后端）。

---

## 9. 验证方式

### 9.1 后端全量 pytest

```bash
cd backend
python -m pytest tests/ --tb=short -q
```

预期：723 passed, 1 warning（`zep_cloud` / Python 3.14 兼容警告）。

### 9.2 前端 node 测试

```bash
cd frontend
node --test tests/*.test.js tests/composables/*.test.js
```

预期：172 passed。

> 在根目录执行：
> ```bash
> cd frontend && node --test tests/*.test.js tests/composables/*.test.js
> ```

### 9.3 前端构建

```bash
cd frontend
npm run build
```

预期：构建成功，无 chunk size warning，无 pendingUpload 混用 warning（已在 Phase 4C 解决）。

### 9.4 Git whitespace 检查

```bash
git diff --check
```

预期：clean（无输出）。

### 9.5 全链路冒烟测试（延期）

全链路手动冒烟（whole-phase smoke）尚未执行。该验收项在 Phase 6D 就绪门中定义，等待用户触发。冒烟流程应覆盖：

1. `POST /api/graph/build` — 消费者 brief 摄入与图构建
2. `POST /api/simulation/create` — 模拟创建
3. `POST /api/simulation/prepare` — prepare（profile 生成）
4. `POST /api/simulation/start` — 启动模拟（建议 `max_rounds=3`）
5. `GET /api/consumer/simulation/<simulation_id>/consumer-summary` — 消费者摘要
6. `POST /api/consumer/simulation/<simulation_id>/branches` — 分支 fork
7. `POST /api/consumer/simulation/<simulation_id>/branches/<branch_id>/interventions` — 干预注入
8. `POST /api/consumer/simulation/<simulation_id>/branches/<branch_id>/resume` — 分支恢复
9. `POST /api/report/compare` — 对比创建
10. `POST /api/report/benchmarks/register` — 基准注册
11. `POST /api/report/benchmarks/<benchmark_id>/replay` — 基准回放
12. `POST /api/report/research-assets/export` — 研究资产导出

---

## 10. 已知约束与风险

### 10.1 文件系统仓库（非数据库 / 非多实例）

- **现状**：所有 repository 具体实现均为 `FilesystemProjectRepository` 等，数据以 JSON/JSONL 保存在 `backend/uploads/` 和 `backend/data/` 下。
- **影响**：进程重启不会丢失数据（文件仍在），但无法在多实例间共享状态，无事务边界，无乐观锁。
- **缓解**：Phase 7A 将引入 SQLAlchemy 数据库实现，`DB_URL` 存在时自动切换。

### 10.2 ThreadTaskExecutor（非耐久队列）

- **现状**：`TaskExecutor` 默认实现为 `ThreadTaskExecutor`，后台任务以 `threading.Thread(daemon=True)` 运行。
- **影响**：进程重启时，所有在途后台任务（prepare/run/report）丢失，无恢复队列。
- **缓解**：Phase 7B 将引入 `QueueTaskExecutor`，支持消息代理或 SQLite 队列零依赖回退。

### 10.3 全链路冒烟延期

- **现状**：Phase 6D 就绪门中定义的全链路手动冒烟尚未执行。
- **影响**：未通过真实 API 端点验证的端到端路径可能存在未发现的问题。
- **缓解**：接手后应优先执行 whole-phase smoke（见第 9.5 节）。

### 10.4 zep_cloud / Python 3.14 警告

- **现状**：`zep_cloud` 库与 Python 3.14 存在 Pydantic v1 兼容性警告。
- **影响**：测试输出中出现 1 个 warning，不影响功能。
- **缓解**：属于上游依赖问题，当前不做修复。若升级 Python 版本或 zep_cloud 版本可自然解决。

### 10.5 消费者 runner 单流

- **现状**：Step 3 consumer 模式后端仅发射 Reddit-only actions，前端 timeline items 与单传播流对齐。
- **影响**：无多平台（Twitter + Reddit）并发传播。这是 Phase 6E 中故意对齐的结果，不是 bug。

### 10.6 历史命名/遗留痕迹

- 非主要产品面（日志、注释、旧文档）中仍有少量 `MiroFish` 历史引用；产品面已全部统一为 `MiroConsumer`。
- 大 logo 资源文件名仍为 `MiroFish_logo_left...`，仅文件名，不影响功能。
- `README-ZH.md` 和 `PRD.md` 在使用 UTF-8 编码读取时为有效的 UTF-8 文档。

### 10.7 auto_enrich 非真实外部研究

- **现状**：`auto_enrich` 模式使用 repo-owned 确定性合成逻辑生成研究 findings，不调用真实外部研究服务。
- **影响**：研究质量受限于内置合成规则，不能反映真实市场数据。
- **缓解**：这是已知产品限制，非工程债务。替换为真实外部 research / RAG provider 属于未来产品演进方向，不在 Phase 7 范围内。

### 10.8 Prepare 性能

- **现状**：Kimi For Coding 单 profile 生成约 3-5 分钟，4 profile 完整 prepare 约 21 分钟。
- **影响**：大规模运行（>10 profile）耗时会显著增加。
- **缓解**：已支持 `LLM_BOOST_*` 加速配置；Phase 7 后可通过队列执行器实现更稳定的长时间任务管理。

---

## 11. 下一步建议

1. **执行全链路冒烟测试（whole-phase smoke）**
   - 按照第 9.5 节的 12 步流程执行手动端到端验证。
   - 重点检查：quote 多样性、态度分布、分支 fork/恢复/干预、对比工作台、基准回放。

2. **修复冒烟发现的问题（如有）**
   - 仅修复冒烟中发现的阻断性问题，不做范围外改动。

3. **进入 Phase 7A 契约强化**
   - Phase 7 是严格的基础设施硬化阶段，不扩展消费者模拟内核、产品面或报告模型。
   - Phase 7A.1：运行现有 `tests/repositories/test_filesystem_repositories.py` 对抗新的 `InMemoryRepository` harness，证明 ABC 契约可独立于文件系统细节测试。
   - 然后按 Phase 7 主计划（`docs/superpowers/plans/2026-04-24-consumer-simulation-phase7-productionization.md`）的顺序推进。

---

## 12. 交接规则 / 不可破坏的规则

| 规则 | 说明 |
|---|---|
| **保留 `consumer_test` 作为唯一产品面模式** | 所有面向用户的入口默认 `project_type=consumer_test`。不要在 UI 中重新暴露 `project_type=default` 作为用户选项。 |
| **保留 `project_type=default` 为维护者专用** | `default` 模式仍在代码中运行（内部兼容模式），但仅用于维护者调试和 legacy 流程验证。不要在产品文档中将其描述为可见模式。产品面文档测试 `test_phase6a_product_surface.py` 会阻止这种回归。 |
| **保留 legacy shim 除非有意废弃** | `simulation.py`、`report.py` 中的消费者端点 shim 层、`graph.js` 的 re-export、`report.js` 的 re-export 均服务于向后兼容。不要在没有替代方案和迁移计划的情况下删除它们。 |
| **避免在 Phase 7 下扩展内核/API 范围** | Phase 7 严格限于基础设施硬化（数据库、队列、多实例安全）。任何改动 `HybridSimulationKernel`、`PropagationState`、Vue 组件、API schema 的 PR 都不应标记为 Phase 7。 |
| **保留文件系统回退作为本地开发默认** | Phase 7A 引入数据库实现时，`DB_URL` 不存在必须自动回退到文件系统实现，确保本地开发和测试零配置。 |
| **保留 ThreadTaskExecutor 作为本地开发默认** | Phase 7B 引入队列执行器时，无队列代理配置必须自动回退到 `ThreadTaskExecutor`。 |
| **不要迁移 legacy `project_type=default` 产物到新存储** | Phase 7A 不迁移已有文件系统产物到数据库。数据库持久化仅对新建项目生效。 |
| **所有 Phase 7 改动必须通过回滚检查** | 取消 `DB_URL` 和队列代理配置后，应用必须能在文件系统 + 线程模式下启动并通过完整回归套件。 |

---

*本文档由 2026-04-24 的 `fc7049d` 提交基线生成。如有后续改动，请以最新代码和测试为准。*
