# MiroConsumer 最终评审整改落地审核报告

> 审核日期：2026-05-09  
> 审核对象：`D:\project\MiroFish` 当前工作区  
> 来源文档：`C:\Users\05537\Downloads\miroconsumer.agent.final.md`  
> 审核方式：逐项读取原评审第 21 章正式整改矩阵，并交叉核对代码、文档、测试和 CI 配置  
> 结论摘要：P0 已落地；本轮已补齐 CI 前端测试命令、dev worker 编排、后端全量测试阻断、生产 Gunicorn 默认 worker、StartSimulationRequest 契约、内置 tech persona pack、Redis 缓存覆盖、v1 auth/OpenAPI schema、evidence graph 前端组件、PostgreSQL JSONB GIN 索引声明、传播收敛补充指标、API versioning policy、VOC 覆盖度指标与 ReasoningTrace input/evidence/conclusion 三元组；P1-P3 仍存在少量“有代码落点但未满足原报告完整验收口径”的部分落地项，不能判定为“全部完成”

---

## 1. 审核范围与口径

本次以来源评审报告第 21 章“风险分级与整改路线图”为主清单，覆盖：

| 优先级 | 数量 | 原报告定位 |
|---|---:|---|
| P0 | 3 | 阻碍生产部署或直接安全风险，生产前必须关闭 |
| P1 | 6 | 短期核心工程短板，P0 后首个迭代应处理 |
| P2 | 5 | 中期代码质量和用户体验改进 |
| P3 | 4 | 长期工程成熟度优化 |
| **合计** | **18** | 正式整改矩阵 |

此外，原报告前文还有若干章节级建议未全部进入第 21 章正式矩阵，例如 `report.py` 拆分、后端报告可视化服务、健康检查增强、OpenTelemetry、SBOM、许可证自动化等。本报告将其作为“补充观察”，不混入 18 项主清单完成率。

状态定义：

| 状态 | 判定标准 |
|---|---|
| 已落地 | 代码/文档/配置具备明确实现，并有直接测试或可运行证据支撑，基本满足原报告验收目标 |
| 部分落地 | 有明显实现，但覆盖范围、接入路径、CI/前端/验收证据仍不满足原报告完整口径 |
| 未落地 | 未找到实质实现或仅有 TODO/文档声明 |
| 无法完全验证 | 实现存在，但本机环境或依赖条件不足以完成端到端验证 |

---

## 2. 总体结论

**不能确认“文档里的所有需要优化和修复都已落地”。**

当前最重要的好消息是：3 个 P0 项已经有实质落地，且定向测试通过。RQ 队列、bcrypt API Key、认证持久化都不再是原报告描述的空壳或安全硬伤。

本轮整改后，CI 前端测试命令、开发 compose worker 编排、全量后端测试中的 auth/400 冲突、生产 Gunicorn 默认 worker 偏低、`StartSimulationRequest` 丢弃 society/channel 字段、内置 `tech_early_adopters` 画像包缺失、Redis 缓存覆盖不足、evidence graph 缺前端可视化、传播收敛指标不足、API versioning 策略缺失、VOC 覆盖度指标缺失等问题已关闭。

但 P1-P3 中仍有至少 3 项应按“部分落地”处理：OpenAPI 仍是手工 curated 契约且未覆盖完整路由清单；数据库已声明 JSONB GIN 索引但仍缺 EXPLAIN 证据；分布式锁仍缺真实多实例 Redis 竞争 smoke。

综合判定：

| 类别 | 数量 | 项目 |
|---|---:|---|
| 已落地 | 15 | P0-1、P0-2、P0-3、P1-1、P1-2、P1-3、P1-4、P1-5、P2-1、P2-2、P2-4、P2-5、P3-1、P3-2、P3-4 |
| 部分落地 | 3 | P1-6、P2-3、P3-3 |
| 未落地 | 0 | 正式 18 项内未发现完全无实现项 |

Go/No-Go 判断：

- P0 已关闭，具备进入受控 staging 继续验证的基础。
- 不建议按“整改全部完成”对外宣称，也不建议直接进入真实生产负载。
- 下一步应优先补齐部分落地项中会影响契约完整性和核心可信度的项目：P2-3 OpenAPI 自动同步/覆盖率、P1-6 EXPLAIN 证据、P3-3 真实 Redis 竞争 smoke。

---

## 3. 正式整改矩阵逐项审核

### P0-1 RQ 队列真实接入 Redis/RQ

状态：已落地。

证据：
- `backend/app/services/application/rq_queue.py` 已引入 `redis`、`rq`、`Job`、`FailedJobRegistry`，`RQQueueBackend.enqueue()` 调用 `self._queue.enqueue(..., job_id=trace_id, meta=meta)`，不再是只写日志的 skeleton。
- `backend/app/worker.py` 已在 RQ 模式下创建 `rq.Worker([queue_name], connection=conn)` 并调用 `worker.work(...)`。
- `QueueTaskExecutor` 对 `runs_externally=True` 的 RQ 后端不再本地起线程执行，符合外部 worker 消费模型。
- `backend/requirements.txt` 与 `backend/pyproject.toml` 均声明 `redis` 和 `rq` 依赖。

验证：
- `python -m pytest -o addopts= backend/tests/test_rq_queue.py -q`：13 passed。
- 整改相关后端定向套件：159 passed。

遗留风险：
- 本次未连接真实 Redis 跑端到端 worker 消费，只完成 mock/unit 级验证。
- dev `docker-compose.yml` 已补 worker 服务；仍建议补一条真实 Redis/RQ dev E2E smoke。

### P0-2 API Key 哈希迁移到 bcrypt

状态：已落地。

证据：
- `backend/app/auth/models.py` 使用 `bcrypt.gensalt()`、`bcrypt.hashpw()` 和 `bcrypt.checkpw()`。
- `generate_api_key()` 生成 `mk_keyid.secret` 形式，存储 bcrypt hash。
- `auth/middleware.py` 通过 `extract_api_key_id()` 先定位 key，再 `verify_api_key()` 校验 hash。
- `rg` 未在 `backend/app/auth` 中发现 `hashlib.sha256(api_key...)` 路径。

验证：
- 整改相关后端定向套件：159 passed。
- `backend/tests/test_auth.py` 中 bcrypt 长度、salt 差异、错误 key 拒绝均有覆盖。

遗留风险：
- 测试中仍出现 JWT secret 过短警告，虽不属于 P0-2，但属于安全配置质量问题。

### P0-3 认证信息迁移到共享持久存储

状态：已落地。

证据：
- `backend/app/auth/repository.py` 定义 `AuthRepository`、`MemoryAuthRepository`、`SqlAlchemyAuthRepository`。
- `auth_users`、`auth_api_keys` 表包含 user/key/tenant 等字段和索引。
- `create_auth_repository_from_config()` 基于 DB 配置创建 SQLAlchemy repository；无 DB 时才回落到内存实现。
- `backend/app/__init__.py` 在 `create_app()` 中调用 `create_auth_repository_from_config(config_class)`，并将 repository 注入 `init_auth()`。
- 认证中间件不再以模块级 `_api_keys = {}`、`_users = {}` 作为生产状态来源。

验证：
- 整改相关后端定向套件：159 passed。
- `backend/tests/test_auth_repository.py` 覆盖 repository 重启后读取、SQLAlchemy 实现和内存 fallback。

遗留风险：
- `auth_metadata.create_all(engine)` 仍是运行时自动建表路径；已有 Alembic 迁移可用，但生产迁移策略需要明确采用 Alembic，而非依赖应用启动建表。

### P1-1 补齐开发 docker-compose 基础设施

状态：已落地。

已落地证据：
- `docker-compose.yml` 已包含 `frontend`、`backend`、`postgres`、`redis`、`minio`。
- backend 环境变量包含 `DB_URL`、`QUEUE_BACKEND=rq`、`REDIS_URL`、`LOCK_BACKEND`、S3/MinIO 配置。
- Postgres 与 Redis 有 healthcheck，MinIO 有端口和 volume。
- 本轮已新增 dev `worker` 服务，复用 dev 镜像，命令为 `cd backend && uv run python -m app.worker`，并依赖 Postgres、Redis、MinIO。
- `docker compose config --quiet` 验证通过。

遗留风险：
- 本轮完成编排层闭环和配置解析验证；尚未启动真实 Redis/Postgres/worker 组合跑“提交后台任务 -> worker 消费”的 dev E2E smoke。

建议：
- 增加一条可选 smoke：`docker compose up redis postgres worker backend` 后提交 RQ job 并验证 worker 消费。

### P1-2 增加 Redis 缓存层

状态：已落地。

证据：
- `backend/app/services/application/redis_cache.py` 提供 `RedisCache`，支持 `get/set/delete/exists/get_or_set`、TTL 和 Redis 不可用降级。
- `ConsumerAppService.get_consumer_summary()` 在 `REDIS_URL` 配置存在时使用 cache-aside 缓存消费者摘要。
- 本轮新增 `RedisCache.metrics()`，输出本地 hits、misses、sets、errors、available 指标。
- `ConsumerAppService.get_channel_summary()` 已增加 Redis cache-aside，覆盖 channel report context 热点读取。
- `SimulationManager.get_simulation_config()` 已增加 Redis cache-aside，并在保存 simulation config 后删除对应缓存。
- `PersonaPackRegistry.load_pack()` 对内置 persona pack 增加 Redis cache-aside，缓存 key 为 `persona_pack:v1:{pack_id}`。
- `backend/tests/test_redis_cache.py`、`backend/tests/consumer/test_consumer_app_service.py`、`backend/tests/consumer/test_persona_pack_registry.py`、`backend/tests/services/application/test_simulation_manager_repo.py` 覆盖缓存行为。

遗留观察：
- 当前指标为进程内本地计数，尚未暴露到 `/metrics`；如需运维看板，可继续接入 Prometheus 计数器。

### P1-3 默认消费者画像扩充到 15-20 个

状态：已落地。

证据：
- `backend/app/services/consumer/data/default_personas.json` 当前包含 16 个画像，ID 为 M01-M16。
- 新增覆盖银发、Z 世代、下沉市场、高端生活方式、小镇青年、健康意识、直播购物等类型。
- 定向测试通过。

验证：
- 画像统计：count = 16。
- 整改相关后端定向套件：159 passed。

遗留风险：
- M01-M08 没有显式 `community` 字段；若后续严格按“每社区至少 3 个画像”做质量门禁，还需要补齐社区归属与数量均衡。

### P1-4 PRD 补充传播学理论依据

状态：已落地。

证据：
- `PRD.md` 已加入 Rogers 创新扩散理论、Katz & Lazarsfeld 两级传播理论、Granovetter 弱连接理论。
- 每个理论下有与传播事件、bridge/amplifier 角色、Propagation_Only 层级等设计点的对应说明。
- 文中有工程近似声明，未把仿真误称为真实社会测量。

验证：
- `rg "Rogers|Katz|Lazarsfeld|Granovetter|创新扩散|两级传播|弱连接" PRD.md` 可定位到相关段落。

### P1-5 增加传播演化收敛检测

状态：已落地。

证据：
- `backend/app/services/consumer/convergence_detector.py` 定义 `ConvergenceDetector`，支持 attitude distribution difference、active agent ratio、min_rounds、stop reason。
- 本轮新增 `event_distribution_change_threshold` 与 `community_coverage_threshold`，并输出 `event_type_distribution_change_rate`、`current_event_type_distribution`、`previous_event_type_distribution`、`community_coverage_ratio`、`active_community_count`、`total_community_count`。
- `SimulationRunner` 的 quick consumer path 会读取 `convergence_config`，并在收敛时写入 `state.society_metrics["convergence"]`。
- quick path 的 `convergence_config` 白名单已允许新阈值从配置进入 detector。
- standard/large society runtime 会在最终 `society_metrics["convergence"]` 中写入 `stopped`、`round_index`、`reason`、`metrics`，不再只停留在日志/内部控制。

验证：
- `backend/tests/consumer/test_convergence_detector.py::test_convergence_metrics_include_event_distribution_and_community_saturation` 覆盖事件类型分布稳定性与社区覆盖度饱和。
- `backend/tests/consumer/society/test_society_runtime.py::test_society_runtime_production_mode_schema_ranges` 验证 standard runtime 最终 report context 暴露 `convergence` 字段。

### P1-6 增加数据库外键和高频查询索引

状态：部分落地。

已落地证据：
- `backend/alembic/versions/20260508_0003_add_performance_indexes.py` 增加 projects、simulations、simulation_runs、branches、reports、tasks、task_attempts 的 B-tree 索引。
- `backend/alembic/versions/20260508_0001_auth_persistence.py` 增加 auth_users/auth_api_keys 的 tenant/user/hash 索引。
- 本轮在 `20260508_0003_add_performance_indexes.py` 中新增 PostgreSQL 专用 `POSTGRES_GIN_INDEXES`，覆盖 `projects.data`、`simulations.data`、`reports.data`、`consumer_events.payload`、`research_assets.payload`、`tasks.payload`。
- `backend/tests/test_migration_indexes.py` 验证 upgrade/downgrade。

缺口：
- JSONB GIN 索引声明已补齐，但本机 SQLite migration smoke 不会实际创建 PostgreSQL GIN。
- 未见真实 PostgreSQL 数据量下关键查询 `EXPLAIN` 证据。

建议：
- 在 PostgreSQL staging 数据库运行 migration smoke 和关键查询 EXPLAIN，证明高频查询不再全表扫描。

### P2-1 拆分过大的 consumer API 模块

状态：已落地。

证据：
- `backend/app/api/consumer.py` 当前约 22 行，作为 registrar。
- 业务拆到 `consumer_summary.py`、`consumer_branches.py`、`consumer_comparisons.py`、`consumer_assets.py`、`consumer_research.py`、`consumer_operations.py`、`consumer_utils.py` 等包内模块。
- 各模块行数约 45-174 行，低于原报告建议的 200 行级别。

验证：
- `backend/tests/api/test_consumer_api_modularization.py` 包含在 159 passed 定向套件中。

补充观察：
- 原报告章节级建议还要求同步拆分 `report.py`。`backend/app/api/report.py` 当前仍约 1152 行，该项未进入第 21 章 P2-1 主矩阵，但作为报告章节建议仍未落地。

### P2-2 增加 API v1 版本前缀

状态：已落地。

证据：
- `backend/app/__init__.py` 同时注册旧路径和 `/api/v1/graph`、`/api/v1/simulation`、`/api/v1/report`、`/api/v1/consumer`、`/api/v1/auth`。
- `backend/app/auth/middleware.py` 已把 `/api/v1/auth/register`、`/api/v1/auth/login` 纳入公开路径。
- 新增 `docs/API_VERSIONING_POLICY.md`，明确 `/api/v1/` 为 canonical public API，旧 `/api/*` 路由保留至少 two minor releases 作为兼容窗口，并定义 Deprecation/Sunset/Link header 建议。
- `backend/tests/test_openapi_spec.py::test_v1_auth_register_and_login_routes_are_public` 验证 auth v1 register/login 可在关闭测试 auth bypass 时正常使用。
- `backend/tests/test_openapi_spec.py::test_api_versioning_policy_documents_legacy_deprecation_window` 验证版本策略文档包含 v1、Legacy `/api/*`、two minor releases 与 Deprecation 关键约束。

遗留观察：
- 旧 `/api/*` 路由仍完整保留；这是当前兼容策略的一部分，后续移除需要按版本策略执行。

### P2-3 完善 OpenAPI 文档

状态：部分落地。

已落地证据：
- `/api/openapi.json` 不再是空 `paths`，`backend/app/__init__.py` 手工返回若干 v1 paths。
- `backend/tests/test_openapi_spec.py` 验证关键路径非空且旧 consumer path 未进入 spec。
- 本轮已补齐 `StartSimulationRequest` 中 `society_mode`、`society_seed`、`society_max_agents`、`society_audit_sample_size`、`advanced_society_mode`、`enabled_channels`、`channel_seed`、`llm_budget_limit` 字段，避免 Flask 路由层校验时丢弃 society/channel 参数。
- `backend/tests/api/test_consumer_channel_routes.py::test_start_simulation_rejects_illegal_consumer_channel_id` 已验证非法 channel 能进入业务校验并返回 400。
- 本轮新增 OpenAPI `components.schemas`，覆盖 `RegisterUserRequest`、`LoginRequest`、`CreateApiKeyRequest`、`GenerateReportRequest`、`GenerateReportStatusRequest`、`DeadLetterListResponse`、`EvidenceGraphResponse`、`StartSimulationRequest`。
- OpenAPI paths 已补 auth v1、health、queue dead letters、report generate/status、simulation start、evidence graph 等核心路径。
- `backend/tests/test_openapi_spec.py::test_openapi_spec_exposes_core_request_and_response_schemas` 验证核心 schema 存在。
- 本轮新增 `backend/tests/test_openapi_spec.py::test_openapi_v1_paths_match_registered_flask_routes`，保证已写入 OpenAPI 的 v1 paths 都能映射到真实 Flask route；并修正项目列表路径为实际存在的 `/api/v1/graph/project/list`。

缺口：
- OpenAPI 是手工 curated，不是从 Flask 路由或契约模型自动生成。
- 仍只覆盖主要 consumer/report/simulation/graph/auth/queue 路径；很多 report/consumer 子路径的 request/response schema 尚未完整纳入。
- 原报告建议“API 文档与代码同步”，当前已增加“已记录路径必须匹配真实 route”的护栏，但仍未形成完整自动生成/覆盖率机制。

建议：
- 生成完整路由清单并对 OpenAPI paths 做覆盖率门禁。
- 为核心 POST/GET 添加 request/response schema，而不只是 summary/description。

### P2-4 结构化 ReasoningTrace

状态：已落地。

证据：
- `backend/app/services/consumer/reasoning_trace.py` 在 `ReasoningTrace` 中加入 `perception_reasoning`、`decision_reasoning`、`expression_reasoning`、`related_finding_id`、`related_event_id`、`agent_id`、`round_index`。
- 本轮新增 `reasoning_triplets`，以结构化列表保存 `input`、`evidence`、`conclusion` 三元组。
- `to_dict()`、`from_dict()`、JSONL read/write 均支持新字段和 `reasoning_triplets`；读取旧 trace 时也会从 perception/decision/expression 字段归一化生成 triplet。
- `backend/tests/consumer/reporting/test_reasoning_trace.py` 覆盖 trace 持久化、读取和 legacy normalization。
- 本轮 `AgentStepExecutor._trace_from_event()` 会从主 society runtime event 填充 `perception_reasoning`、`decision_reasoning`、`expression_reasoning`、`related_event_id`、`related_finding_id`、`agent_id`、`round_index`。
- shadow batch trace 也会记录 round_index、输入摘要、输出事件数和对应 triplet，避免只剩 `reasoning_summary`。
- legacy `ConsumerSocietyRuntime._trace_from_event()` 也同步填充 reasoning triplet，避免旧路径落后。
- `backend/tests/consumer/reporting/test_reasoning_trace.py::TestReasoningTraceSchema::test_trace_preserves_reasoning_triplets` 验证三元组序列化/反序列化。
- `backend/tests/consumer/reporting/test_reasoning_trace.py::TestSocietyRuntimeTraceMapping::test_agent_step_trace_populates_reasoning_sections_and_linkage` 验证主流程 trace linkage 与 input/evidence/conclusion 三元组。

遗留观察：
- 报告端可以通过 event/finding/agent/round 字段回溯主链路；如需独立图谱查询 API，可作为后续 report UX 增强项处理，但不再阻断 P2-4 主矩阵落地。

### P2-5 改进 VOC 选择算法

状态：已落地。

证据：
- `ConsumerScoringService._top_quotes()` 已加入语义去重和 agent 多样性偏好。
- engagement 仍作为基础排序因子，但不再是唯一因素。
- 本轮 `ConsumerEvidenceBundle.to_dict()` 新增 `voc_diversity_metrics`，包含 total/selected quote count、unique/selected agent count、agent coverage ratio、segment coverage ratio、bucket coverage ratio、bucket distribution、minority segment retention。
- `_normalize_quote_event()` 会保留 agent/persona/segment/role/community 元数据，用于 VOC 覆盖度计算。
- `backend/tests/consumer/test_scoring.py::test_voc_bundle_reports_diversity_and_coverage_metrics` 验证 coverage/diversity metric 输出。
- `backend/tests/consumer/test_scoring.py::test_voc_selection_keeps_minority_quote_when_high_engagement_quotes_repeat` 验证高 engagement 同质 quote 不会挤出少数 segment quote。

遗留观察：
- `_top_quotes()` 的相似度仍是分词重叠式近似去重，不是 embedding 语义去重；如后续要提升精度，可单独升级 similarity backend。

### P3-1 完整定义 Content Security Policy

状态：已落地。

证据：
- `backend/app/utils/security_headers.py` 定义 `DEFAULT_CSP_DIRECTIVES`，包含 default-src、script-src、style-src、img-src、font-src、connect-src、object-src、base-uri、frame-ancestors、form-action、upgrade-insecure-requests。
- `apply_security_headers()` 写入 `Content-Security-Policy`。
- 支持 `CSP_POLICY` override。

验证：
- `backend/tests/test_security_headers.py` 包含在 159 passed 定向套件中。

### P3-2 前端测试框架升级

状态：已落地。

已落地证据：
- `frontend/package.json` 已定义 `test: vitest run`、`test:coverage: vitest run --coverage`。
- `frontend/vitest.config.js` 使用 v8 coverage，设置 statements/lines/functions 70%、branches 60%。
- `npm test`：最新结果 24 test files passed，286 tests passed。
- `npm run test:coverage`：历史结果 23 test files passed，280 tests passed；Statements 90.18%、Branches 77.03%、Functions 97.5%、Lines 90.38%。
- `.github/workflows/ci.yml` 的 frontend job 已从旧的 `node --test tests/*.test.js tests/composables/*.test.js` 改为 `npm test`。
- `npm run build`：Vite production build passed。

历史失败：
- 本轮整改前，`node --test tests/*.test.js tests/composables/*.test.js` 为 23/23 test files failed，错误为 Vitest failed to find the current suite。

建议：
- 如需把覆盖率作为 CI 门禁，可在现有 `npm test` 后追加 `npm run test:coverage`。

### P3-3 分布式锁与 Gunicorn worker 配置化

状态：部分落地。

已落地证据：
- `backend/app/services/application/concurrency.py` 增加 `RedisLockManager`，使用 Redis `SET NX EX` 和 token-checked Lua release。
- `LOCK_BACKEND=auto|redis|file|db`，auto 在有 `REDIS_URL` 时优先 Redis。
- `Dockerfile.backend`、`docker-compose.prod.yml` 支持 `GUNICORN_WORKERS`、`GUNICORN_THREADS`、`GUNICORN_TIMEOUT`。
- 并发锁相关测试包含在 159 passed 定向套件中。

已补齐：
- `docker-compose.prod.yml` 默认 worker 已从 `${GUNICORN_WORKERS:-2}` 调整为 `${GUNICORN_WORKERS:-4}`，满足原报告 4-8 的下限建议。

仍有缺口：
- 本次仍未做真实多实例 Redis 竞争 smoke，仅有 fake Redis/unit 验证。

建议：
- 增加真实 Redis 集成测试或 docker compose smoke。

### P3-4 证据图谱可视化

状态：已落地。

证据：
- `AuditChainService.build_evidence_graph()` 可从 `report_context.enriched_findings`、`source_catalog`、confidence summary 构建 finding/evidence/source 三层节点和 supported_by/sourced_from 边。
- `GET /api/consumer/reports/<report_id>/evidence-graph` 已加入。
- `/api/openapi.json` 记录了 `/api/v1/consumer/reports/{report_id}/evidence-graph`。
- 本轮新增 `frontend/src/api/consumerFactory.js#getReportEvidenceGraph()` 与 `frontend/src/api/consumer.js` 导出。
- 本轮新增 `frontend/src/components/consumer/EvidenceGraphPanel.vue`，在 `Step4Report.vue` 消费 evidence graph API 并以 SVG 展示 finding -> evidence -> source 图，低置信节点有视觉区分。
- `backend/tests/services/application/test_audit_chain_service.py` 覆盖低置信标记、evidence snippet fallback、traceable_fields。
- `frontend/tests/consumerEvidenceGraphPanel.test.js`、`frontend/tests/consumerApi.behavior.test.js`、`frontend/tests/consumerApi.smoke.test.js` 覆盖前端 API 与组件挂载。

---

## 4. 补充章节级建议核对

这些建议来自原报告前文各维度，但未全部进入第 21 章正式矩阵。它们不计入 18 项主清单完成率，但如果按“文档里的所有优化建议”理解，仍有大量未落地或仅部分落地内容。

| 建议/问题 | 当前状态 | 说明 |
|---|---|---|
| `report.py` 拆分为多个 Blueprint 模块 | 未落地 | `backend/app/api/report.py` 仍约 1152 行 |
| 后端报告可视化服务，支持 PDF/PNG 图表导出 | 未见完整落地 | 未发现 matplotlib/plotly 报告图表服务接入 |
| propagation timeline REST/WebSocket 实时推送 | 部分相关 | 有 `propagation_paths` 读取接口和前端 timeline 组件，但未见原建议的 `/api/simulation/{id}/propagation-timeline` 或 WebSocket 实时推送 |
| RunController 全部 Agent 未激活、图谱断连、多轮无事件友好报错 | 部分相关 | 有 quality checker/early stop，但未见三种边界条件的显式友好错误全覆盖 |
| confidence_scoring 关键决策结构化审计日志 | 未系统确认 | 未纳入正式矩阵；需要单独审计 |
| drift_detector KL/PSI 实现 | 未系统确认 | 有 `drift_detector.py`，但本次未按章节级建议展开算法验收 |
| 健康检查增强为 DB/Redis/MinIO readiness | 未见完整落地 | 原 `/health` 仍需进一步确认是否做依赖探测 |
| OpenTelemetry/AlertManager/SBOM/许可证自动化 | 未见完整落地 | 未进入正式 18 项矩阵 |
| API URL 单复数命名统一 | 部分相关 | 当前仍保留旧路径兼容；OpenAPI 已校正项目列表真实 v1 route，但未见全局命名迁移 |
| API v1 auth 路由 | 已落地 | auth 已同时注册 `/api/auth` 与 `/api/v1/auth`，且 register/login 公开路径有测试覆盖 |

---

## 5. 验证命令与结果

### 后端

1. `python -m pytest backend/tests/ -x -q`
   - 本轮整改前结果：未开始测试，pytest 参数失败。
   - 原因：当前解释器缺少 `pytest-cov`，而 `backend/pyproject.toml` 默认 addopts 包含 `--cov=app --cov-report=term-missing`。
   - 本轮处理：安装 `pytest-cov 7.1.0` 与 `coverage 7.13.5` 后重跑默认命令。
   - 最新结果：1878 passed，1 skipped，204 warnings；coverage TOTAL 73%。

2. `python -m pytest -o addopts= backend/tests/ -x -q`
   - 本轮整改前结果：20 passed 后失败。
   - 失败用例：`backend/tests/api/test_consumer_channel_routes.py::test_start_simulation_rejects_illegal_consumer_channel_id`
   - 失败原因：测试期望非法 channel 返回 400，实际先被认证中间件拦截为 401。
   - 本轮处理：新增测试认证绕过开关 `AUTH_BYPASS_IN_TESTING`，普通 `create_app()` 路由测试默认绕过 auth；`test_auth.py` 与 `test_tenant_isolation.py` 显式关闭绕过，继续覆盖真实认证路径。同步补齐 `StartSimulationRequest` 的 society/channel 字段，避免 `enabled_channels` 被 Pydantic extra 丢弃。
   - 历史结果：`python -m pytest -o addopts= backend/tests/ -q` 通过，1865 passed，1 skipped，57 warnings；最新默认全量命令见上方第 1 项。

3. `uv run --directory backend python -m pytest -o addopts= tests/test_rq_queue.py -q`
   - 结果：失败于环境构建。
   - 原因：Python 3.14 下 `tiktoken==0.7.0` 构建依赖 Rust/MinGW `dlltool.exe`，当前机器缺失。

4. `python -m pip install "rq>=1.16.0"`
   - 结果：成功安装 `rq 2.8.0` 和 `croniter 6.2.2`。
   - 说明：这是项目已声明依赖，用于补齐当前解释器缺包。

5. `python -m pytest -o addopts= backend/tests/test_rq_queue.py -q`
   - 结果：13 passed，1 warning。

6. 整改相关后端定向套件：
   - 命令覆盖 RQ、认证、认证 repository、Redis cache、persona pack、convergence、migration indexes、OpenAPI、security headers、concurrency locks、deployment、audit chain/evidence graph、consumer API modularization、canonical routes、consumer app service、scoring、ReasoningTrace。
   - 历史结果：159 passed，25 warnings。

7. 本轮新增/回归专项：
   - `python -m pytest -o addopts= backend/tests/api/test_consumer_channel_routes.py -q`：3 passed。
   - `python -m pytest -o addopts= backend/tests/consumer/test_persona_pack_registry.py -q`：25 passed。
   - `python -m pytest -o addopts= backend/tests/deployment/test_phase7e_deployment.py -q`：5 passed。
   - `python -m pytest -o addopts= backend/tests/test_auth.py backend/tests/test_tenant_isolation.py -q`：30 passed，1 skipped。
    - `python -m pytest -o addopts= backend/tests/services/application/test_app_services_use_repositories.py::TestSimulationAppServiceUsesRepositories::test_create_simulation_calls_project_repo backend/tests/services/application/test_app_services_use_repositories.py::TestPhase7CServiceLocks::test_generate_report_worker_acquires_report_generation_lock -q`：2 passed。
    - `python -m pytest -o addopts= backend/tests/test_openapi_spec.py -q`：3 passed。
    - `python -m pytest -o addopts= backend/tests/test_redis_cache.py backend/tests/consumer/test_consumer_app_service.py::test_get_consumer_summary_uses_redis_cache_when_configured backend/tests/consumer/test_consumer_app_service.py::test_get_channel_summary_uses_redis_cache_when_configured backend/tests/consumer/test_persona_pack_registry.py::test_registry_load_builtin_pack_uses_redis_cache backend/tests/services/application/test_simulation_manager_repo.py -q`：20 passed。
    - `python -m pytest -o addopts= backend/tests/test_migration_indexes.py -q`：2 passed。
    - `python -m pytest -o addopts= backend/tests/consumer/test_convergence_detector.py backend/tests/consumer/test_scoring.py backend/tests/consumer/reporting/test_reasoning_trace.py backend/tests/consumer/society/test_society_runtime.py backend/tests/test_openapi_spec.py -q`：49 passed，2 warnings。

### 前端

1. `npm test`
   - 最新结果：24 test files passed，286 tests passed。

2. `npm run test:coverage`
   - 历史结果：23 test files passed，280 tests passed。
   - 覆盖率：Statements 90.18%、Branches 77.03%、Functions 97.5%、Lines 90.38%。

3. `node --test tests/*.test.js tests/composables/*.test.js`
   - 本轮整改前结果：23/23 test files failed。
   - 原因：测试已迁移到 Vitest，Node 原生 runner 会报错 `Vitest failed to find the current suite`。
   - 本轮处理：CI frontend job 已改为 `npm test`。

4. `npm run build`
   - 最新结果：Vite production build passed。

5. 本轮 evidence graph 前端专项：
   - `npm test -- consumerApi.behavior.test.js consumerApi.smoke.test.js consumerEvidenceGraphPanel.test.js`：3 test files passed，49 tests passed。

### 工作区

1. `git diff --check`
   - 最新结果：passed，仅有 Git 行尾 CRLF 提示。

2. `docker compose config --quiet`
   - 结果：passed。

3. `docker compose -f docker-compose.prod.yml config --quiet`
   - 结果：passed。

4. `git status --short`
   - 结果：存在本轮整改修改；报告文档本身与 `tech_early_adopters.json` 为未跟踪/新增内容，尚未提交。

---

## 6. 主要风险排序

### 高风险

1. **OpenAPI 仍是手工 curated，不是自动同步契约**
   - 影响：API 文档可用性提升了，但不能作为完整客户端生成或契约测试依据。
   - 修复：继续补齐剩余 report/consumer 子路径 schema，并建立路由清单到 OpenAPI 的覆盖率测试。

2. **分布式锁仍缺真实多实例 Redis 竞争 smoke**
   - 影响：已有 RedisLockManager 和单元测试，但尚未证明多 worker/多实例竞争下的行为。
   - 修复：增加 docker compose 或集成测试级别的真实 Redis lock smoke。

### 中风险

3. **JSONB/GIN 索引与 EXPLAIN 证据不足**
   - 影响：B-tree 和 PostgreSQL GIN 索引声明已补，但尚未用 staging 数据量证明关键查询计划。
   - 修复：在 PostgreSQL staging 上跑 migration smoke 和 EXPLAIN。

### 中低风险

4. **章节级技术债尚未纳入本轮**
   - 影响：`report.py` 拆分、readiness 健康检查、SBOM/许可证自动化、运维手册等仍未完整闭环。
   - 修复：作为后续工程成熟度批次单独拆分验收。

---

## 7. 推荐下一步整改顺序

1. 补 OpenAPI 覆盖率门禁，至少覆盖剩余主要 consumer/report 子路径 request/response schema，并减少手工不同步风险。
2. 增加真实 Redis 多实例/多 worker 分布式锁 smoke。
3. 在 PostgreSQL staging 上运行 JSONB GIN migration smoke 与关键查询 EXPLAIN。
4. 处理章节级技术债：`report.py` 拆分、健康检查 readiness、SBOM/许可证自动化、运维手册。

---

## 8. 最终审核结论

来源评审文档中的正式 P0 阻断项已经落地，项目当前不再处于原报告描述的 P0 No-Go 状态。

本轮整改又关闭了多项会直接影响落地可信度的问题：CI 前端测试命令已改为 Vitest 入口，后端全量测试中的 auth/400 冲突已修复，dev compose 已补 worker，生产 Gunicorn 默认 worker 已调到 4，`StartSimulationRequest` 已接收 society/channel 相关字段，内置 `tech_early_adopters` 画像包已加入并解除 `.gitignore` 拦截，缓存覆盖扩展到 consumer summary/channel summary/simulation config/persona pack，evidence graph 已有前端组件，OpenAPI 已补 v1 auth/queue/schema 且新增真实 route 匹配测试，PostgreSQL JSONB GIN 索引声明已加入，传播收敛指标、API versioning policy、VOC 覆盖度指标与 ReasoningTrace input/evidence/conclusion 三元组已补齐。

但是，P1-P3 并未全部按原报告完整口径关闭。当前更准确的表述应是：

> P0 已关闭；CI、全量测试阻断、dev worker、生产 worker 默认值、simulation 契约字段、内置 persona pack、缓存覆盖、v1 auth/OpenAPI schema、证据图谱前端可视化、JSONB GIN 索引声明、传播收敛补充指标、API versioning policy、VOC 覆盖度指标与 ReasoningTrace input/evidence/conclusion 三元组等本轮问题已关闭。项目可进入受控 staging 继续验证，但不应宣称最终评审所有优化和修复均已完成；在 OpenAPI 自动同步/覆盖率、真实 Redis 竞争 smoke 和 PostgreSQL EXPLAIN 证据补齐前，不建议进入真实生产负载。
