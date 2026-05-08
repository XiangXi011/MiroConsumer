# MiroConsumer 最终评审整改总规格

## 1. 文档元数据

| 字段 | 内容 |
|---|---|
| 文档日期 | 2026-05-08 |
| 目标分支 | `phase7/gatekeeper-comprehensive-fixes` |
| 来源报告 | `C:\Users\24523\Downloads\miroconsumer.agent.final.md` |
| 来源报告结论 | 综合评分 7.0/10；Conditional Go；完成 P0 后可进入 staging |
| 适用范围 | P0-P3 全量整改路线图、任务交接、验收追踪 |
| 文档状态 | 主整改规格，后续执行以本文为准 |

> 若旧 `IMPROVEMENT_CHECKLIST.md`、历史 handoff、历史 audit 与本文冲突，以本文为准。旧文档保留为历史材料，不作为后续整改的优先级来源。

## 2. 执行原则

1. **P0 先关闭**：未完成全部 P0 前，不启动 P1/P2/P3 的代码整改；文档类准备工作可以并行，但不得阻塞 P0。
2. **阶段门槛固定**：Phase 7B 关闭 P0，Phase 8A 关闭 P1，Phase 8B 关闭 P2，P3 进入长期 backlog。
3. **每项任务必须留下证据**：完成任务时必须补充提交号、验证命令、验证结果摘要和遗留风险。
4. **状态只允许四种值**：`TODO`、`IN_PROGRESS`、`BLOCKED`、`DONE`。
5. **最高优先级优先**：新的执行者必须先读取本文，再选择当前最高优先级中排序最靠前且状态不是 `DONE` 的任务。
6. **不抢跑生产**：P0 全部 `DONE` 后仅允许 staging 试运行；P1 关闭前，不建议承载真实生产业务负载。

## 3. Roadmap

| 阶段 | 目标优先级 | 目标 | 放行条件 |
|---|---|---|---|
| Phase 7B | P0 | 生产止血：队列、认证哈希、认证存储 | 3 个 P0 全部 `DONE`，并跑通一次完整 5 步仿真工作流 |
| Phase 8A | P1 | 核心工程短板：开发编排、缓存、画像、方法论、收敛、索引 | P1 至少 80% `DONE`，且无阻塞生产部署的 P1 残留 |
| Phase 8B | P2 | 体验与维护性优化：拆分、版本化、文档、推理链、VOC | P2 任务逐项验收，不阻塞 staging |
| Long-term Backlog | P3 | 工程成熟度提升和可视化增强 | 按业务节奏独立排期 |

P0 内推荐顺序：先做 `P0-2` API Key bcrypt（范围小、立刻降低安全风险），再做 `P0-3` 认证持久化，最后做 `P0-1` RQ 队列与 worker 联调。若有专门基础设施执行者，`P0-1` 可与 `P0-2/P0-3` 并行推进。

## 4. 任务清单

### P0-1 RQ 队列真实接入 Redis/RQ

| 字段 | 内容 |
|---|---|
| 任务ID | `P0-1` |
| 优先级 | P0，staging 前置门槛 |
| 状态 | `DONE` |
| 触发原因 | 当前 `backend/app/services/application/rq_queue.py` 是 skeleton，`enqueue()` 只记录日志和内存状态 |
| 主要改动方向 | 引入 `redis-py` 和 `rq`；让 `RQQueueBackend.enqueue()` 创建真实 RQ job；worker 使用相同 `REDIS_URL` 消费任务；保留 `thread` 和 `sqlite` fallback |
| 不做什么 | 不新增消费者仿真内核能力；不改变现有 API 响应 schema；不移除本地开发 fallback |
| 验收标准 | `QUEUE_BACKEND=rq` 且 Redis 可用时，提交任务后 Redis 中存在 job；worker 能执行 job 并更新状态；失败任务能返回稳定错误类别；无效 `REDIS_URL` 启动或提交时明确失败 |
| 验证命令或证据 | 后端队列测试；一次 RQ 模式端到端任务提交和 worker 执行日志；`git grep "RQQueueBackend.enqueue not yet implemented" -- backend` 无结果 |
| 依赖关系 | 可独立启动；与 `P1-1` docker-compose 补全存在运行环境协同 |


### P0-2 API Key 哈希迁移到 bcrypt

| 字段 | 内容 |
|---|---|
| 任务ID | `P0-2` |
| 优先级 | P0，staging 前置门槛 |
| 状态 | `DONE` |
| 目标 | API Key 存储和校验不再使用裸 SHA256，改用 bcrypt 或同等级密码哈希 |
| 触发原因 | 当前 `backend/app/auth/middleware.py` 中认证逻辑使用 `hashlib.sha256(api_key.encode()).hexdigest()` |
| 主要改动方向 | 增加 bcrypt 依赖；新增统一 `hash_api_key()` 和 `verify_api_key()`；注册 API Key 时存储 bcrypt hash；认证时逐条安全校验；为现有测试补迁移或兼容路径 |
| 不做什么 | 不改变用户登录协议；不把明文 API Key 持久化；不在日志中输出 API Key |
| 验收标准 | `git grep "hashlib.sha256(api_key" -- backend` 无结果；新注册 API Key 使用 bcrypt hash；错误 API Key 无法通过；旧测试全部更新并通过；bcrypt cost 可配置且有安全默认值 |
| 验证命令或证据 | `cd backend && python -m pytest tests/test_auth.py -v` → 26/26 passed；`git grep "hashlib.sha256.*api_key" -- backend/app/auth/` → 无结果；bcrypt 依赖已加入 pyproject.toml 和 requirements.txt |
| 依赖关系 | 可独立完成；与 `P0-3` 认证存储迁移需要保持 hash 字段格式一致 |
| 完成记录 | 提交号：7276fbd；验证结果：26/26 auth tests passed，SHA256 已从 auth 模块移除，bcrypt hash/verify 正常工作；遗留风险：无 |

### P0-3 认证信息迁移到共享持久存储

| 字段 | 内容 |
|---|---|
| 任务ID | `P0-3` |
| 优先级 | P0，staging 前置门槛 |
| 状态 | `DONE` |
| 目标 | `_api_keys` 和 `_users` 不再作为生产认证状态来源，服务重启和多实例部署时认证状态不丢失 |
| 触发原因 | 当前 `backend/app/auth/middleware.py` 使用内存字典 `_api_keys = {}` 和 `_users = {}` |
| 主要改动方向 | 新增 PostgreSQL 认证表或 Redis-backed 共享存储；提供认证 repository；Flask 中间件通过 repository 查询用户和 API Key；测试环境可保留内存实现作为 fallback |
| 不做什么 | 不绕过 RBAC；不降低租户隔离；不删除测试辅助函数但要限制用途 |
| 验收标准 | 服务重启后已注册用户和 API Key 仍可认证；两个应用实例共享同一认证状态；内存字典不再是生产路径；认证存储异常时返回明确 5xx/认证错误并记录日志 |
| 验证命令或证据 | `git grep "_api_keys = {}" -- backend/app/auth/` → 无结果；`git grep "_users = {}" -- backend/app/auth/` → 无结果；`pytest tests/test_auth.py tests/test_auth_repository.py` → 30/30 passed |
| 依赖关系 | 与 `P0-2` 共享 API Key hash 格式；建议在 bcrypt 接口稳定后落地 |
| 完成记录 | 提交号：35d6244；验证结果：30/30 auth tests passed，内存字典已移除，AuthRepository 抽象层 + Memory/SqlAlchemy 实现完成；遗留风险：无 |

### P1-1 补齐开发 docker-compose 基础设施

| 字段 | 内容 |
|---|---|
| 任务ID | `P1-1` |
| 优先级 | P1，production 前置建议 |
| 状态 | `DONE` |
| 目标 | 本地开发环境通过 `docker-compose up` 启动 backend、frontend、PostgreSQL、Redis、MinIO 等基础服务 |
| 触发原因 | 当前 `docker-compose.yml` 只有单服务，缺少与生产接近的基础设施 |
| 主要改动方向 | 参考 `docker-compose.prod.yml` 补齐基础设施服务、健康检查、环境变量和 volume；保留开发友好的端口映射 |
| 不做什么 | 不把生产密钥写入 compose；不改变生产 compose 的部署策略 |
| 验收标准 | 一条命令可启动完整开发依赖；backend 能连接 DB/Redis/MinIO；README 或部署文档说明启动方式 |
| 验证命令或证据 | `docker-compose config`；`docker-compose up` 启动日志；健康检查通过 |
| 依赖关系 | 支撑 `P0-1` RQ、`P1-2` 缓存和 `P0-3` 认证存储联调 |


### P1-2 增加 Redis 缓存层

| 字段 | 内容 |
|---|---|
| 任务ID | `P1-2` |
| 优先级 | P1，production 前置建议 |
| 状态 | `TODO` |
| 目标 | 为报告数据、模拟配置、画像包等热点读取增加统一缓存策略 |
| 触发原因 | 当前项目缺少缓存层，热点数据每次请求都访问底层存储 |
| 主要改动方向 | 增加 cache abstraction；Redis 可用时启用；定义 TTL、命名空间、失效策略；缓存命中/未命中写入指标或日志 |
| 不做什么 | 不缓存含敏感凭据的明文数据；不让缓存成为唯一事实来源 |
| 验收标准 | 高频报告/配置读取有缓存路径；缓存失效后能回源；缓存不可用时应用降级到原存储；命中率可观测 |
| 验证命令或证据 | 缓存单元测试；Redis 集成测试；热点接口二次访问命中证据 |
| 依赖关系 | 建议在 `P1-1` Redis 服务可用后落地 |


### P1-3 默认消费者画像扩充到 15-20 个

| 字段 | 内容 |
|---|---|
| 任务ID | `P1-3` |
| 优先级 | P1 |
| 状态 | `DONE` |
| 目标 | 默认画像包至少覆盖 15-20 个消费者画像，并覆盖不少于 5 个社区 |
| 触发原因 | 当前 `backend/app/services/consumer/data/default_personas.json` 仅 8 个画像，社区内异质性不足 |
| 主要改动方向 | 扩充银发族、Z 世代、下沉市场、高收入白领、家庭照护者、价格敏感型、成分研究型等画像；保持现有 schema 兼容 |
| 不做什么 | 不引入不可解释的随机画像；不移除现有 M01-M08 除非有迁移说明 |
| 验收标准 | 默认画像数量 15-20；社区数不少于 5；每个社区至少 3 个画像或有明确例外说明；画像字段通过现有 loader 校验 |
| 验证命令或证据 | persona loader 测试；默认画像统计脚本输出；一次小规模仿真可使用扩充画像 |
| 依赖关系 | 可与工程 P0 并行，属于数据内容整改 |


### P1-4 PRD 补充传播学理论依据

| 字段 | 内容 |
|---|---|
| 任务ID | `P1-4` |
| 优先级 | P1 |
| 状态 | `DONE` |
| 目标 | 为传播事件分类、可见性分层和社会角色映射补充社会科学理论根基 |
| 触发原因 | 最终评审认为当前传播模型主要依赖工程直觉，缺少显式理论引用 |
| 主要改动方向 | 在 `PRD.md` 增加 Rogers 创新扩散、Katz/Lazarsfeld 两级传播、Granovetter 弱连接等理论映射；说明哪些实现是工程近似 |
| 不做什么 | 不宣称仿真结果具备统计代表性；不把理论引用写成营销话术 |
| 验收标准 | PRD 至少引用 3 个相关理论；每个理论对应到具体设计点；方法论限制声明保持可见 |
| 验证命令或证据 | PRD diff；评审引用清单；文档链接或参考书目信息 |
| 依赖关系 | 可独立完成 |


### P1-5 增加传播演化收敛检测

| 字段 | 内容 |
|---|---|
| 任务ID | `P1-5` |
| 优先级 | P1 |
| 状态 | `TODO` |
| 目标 | 仿真不只依赖固定 `max_rounds`，能在态度变化率或事件分布稳定时提前停止 |
| 触发原因 | 固定轮数可能造成过度传播或传播不足，影响仿真可信度 |
| 主要改动方向 | 定义收敛指标：态度变化率、事件类型分布稳定性、活跃 agent 比例；增加可配置阈值和停止原因记录 |
| 不做什么 | 不删除 `max_rounds`；不改变默认工作流输出结构 |
| 验收标准 | 达到收敛阈值时自动停止并记录原因；未收敛时仍受 `max_rounds` 限制；报告或运行摘要可显示停止原因 |
| 验证命令或证据 | 收敛/未收敛单元测试；固定 seed 的仿真回归；运行摘要示例 |
| 依赖关系 | 建议在 P0 稳定后执行 |


### P1-6 增加数据库外键和高频查询索引

| 字段 | 内容 |
|---|---|
| 任务ID | `P1-6` |
| 优先级 | P1，production 前置建议 |
| 状态 | `TODO` |
| 目标 | 为 `simulation_id`、`project_id`、`run_id`、`tenant_id`、`status`、`created_at` 等高频查询字段增加索引 |
| 触发原因 | 最终评审指出数据库外键和常用查询字段缺少显式索引，数据量增长后会全表扫描 |
| 主要改动方向 | 在 SQLAlchemy/Alembic schema 中增加 B-tree 索引；PostgreSQL JSONB 高频路径视情况增加 GIN 索引 |
| 不做什么 | 不重写整个 persistence model；不做无基准的大规模 schema 重构 |
| 验收标准 | 新迁移文件独立可追踪；核心查询字段有索引；迁移可升级和回滚；关键查询 explain 不再全表扫描 |
| 验证命令或证据 | Alembic migration；数据库索引检查；关键查询 `EXPLAIN` 摘要 |
| 依赖关系 | 依赖数据库 schema 当前状态；与 `P0-3` 认证表设计需避免冲突 |


### P2-1 拆分过大的 consumer API 模块

| 字段 | 内容 |
|---|---|
| 任务ID | `P2-1` |
| 优先级 | P2 |
| 状态 | `TODO` |
| 目标 | 将 `backend/app/api/consumer.py` 按职责拆分，降低维护和合并冲突风险 |
| 触发原因 | 文件约 644 行，承担 summary、society、focus group、drift、asset、export 等多个职责 |
| 主要改动方向 | 按子域拆分 Blueprint 或 handler 模块；共享校验和响应工具集中复用；保持路由兼容 |
| 不做什么 | 不改 API URL 和响应 schema，除非单独进入 `P2-2` 版本化任务 |
| 验收标准 | 原接口兼容；每个新模块职责单一；后端 API 回归通过 |
| 验证命令或证据 | 后端测试；路由列表对比；重点接口 smoke |
| 依赖关系 | P0/P1 稳定后执行 |


### P2-2 增加 API v1 版本前缀

| 字段 | 内容 |
|---|---|
| 任务ID | `P2-2` |
| 优先级 | P2 |
| 状态 | `TODO` |
| 目标 | 为公共 API 增加 `/api/v1/` 版本层，为未来 v2 留出兼容空间 |
| 触发原因 | 当前端点直接暴露在 `/api/` 下，未来变更缺少版本隔离 |
| 主要改动方向 | 新增 v1 blueprint 前缀；旧路径保留兼容或重定向策略；文档明确迁移窗口 |
| 不做什么 | 不在同一任务中重写业务 contract |
| 验收标准 | v1 路径可用；旧路径兼容策略明确且测试覆盖；OpenAPI 后续能表达 v1 paths |
| 验证命令或证据 | API 路由测试；前端调用 smoke；OpenAPI path 检查 |
| 依赖关系 | 建议与 `P2-3` OpenAPI 同阶段协调 |


### P2-3 完善 OpenAPI 文档

| 字段 | 内容 |
|---|---|
| 任务ID | `P2-3` |
| 优先级 | P2 |
| 状态 | `TODO` |
| 目标 | `/api/openapi.json` 返回可用 paths，而不是空 schema |
| 触发原因 | 最终评审指出当前 OpenAPI schema 为空，文档与代码无法同步 |
| 主要改动方向 | 使用现有契约模型生成或手动维护 OpenAPI paths；覆盖核心 consumer/report/auth/health API |
| 不做什么 | 不把 OpenAPI 作为业务逻辑来源；不在文档任务中改运行逻辑 |
| 验收标准 | `openapi.json` paths 非空；核心端点有 request/response schema；Swagger/ReDoc 可读 |
| 验证命令或证据 | openapi schema snapshot；文档页面截图或 curl 输出 |
| 依赖关系 | 与 `P2-2` API v1 前缀协调 |


### P2-4 结构化 ReasoningTrace

| 字段 | 内容 |
|---|---|
| 任务ID | `P2-4` |
| 优先级 | P2 |
| 状态 | `TODO` |
| 目标 | 将纯文本 `reasoning_summary` 扩展为可查询、可关联的结构化推理链 |
| 触发原因 | 当前推理链缺少感知、决策、表达分解，也缺少 finding/event/agent/round 关联 |
| 主要改动方向 | 增加 `perception_reasoning`、`decision_reasoning`、`expression_reasoning`；增加 `related_finding_id`、`related_event_id`、`agent_id`、`round_index` |
| 不做什么 | 不在生产环境暴露敏感思维链；不破坏已有 JSONL 读取兼容 |
| 验收标准 | 新 trace 字段可持久化和查询；旧 trace 可兼容读取；报告能回溯到相关推理 |
| 验证命令或证据 | ReasoningTrace 单元测试；JSONL 样例；报告回溯 smoke |
| 依赖关系 | P0/P1 后执行 |


### P2-5 改进 VOC 选择算法

| 字段 | 内容 |
|---|---|
| 任务ID | `P2-5` |
| 优先级 | P2 |
| 状态 | `TODO` |
| 目标 | VOC 不再只按互动量取 top 3，而要体现画像多样性和语义代表性 |
| 触发原因 | 当前 `backend/app/services/consumer/scoring.py` 的 `_top_quotes()` 逻辑简单，可能丢失关键少数意见 |
| 主要改动方向 | 引入画像覆盖约束、语义去重、观点类别覆盖；保留 engagement 作为排序因子之一 |
| 不做什么 | 不伪造 VOC；不删除原声证据；不把所有 quote 等权堆入报告 |
| 验收标准 | 同类 VOC 去重；不同画像/社区有代表；输出包含覆盖度指标；小样本时有降级说明 |
| 验证命令或证据 | VOC 算法单元测试；固定样本输出快照；覆盖度指标示例 |
| 依赖关系 | 与 `P1-3` 画像扩充协同效果更好 |


### P3-1 完整定义 Content Security Policy

| 字段 | 内容 |
|---|---|
| 任务ID | `P3-1` |
| 优先级 | P3 |
| 状态 | `TODO` |
| 目标 | 在安全响应头中补充完整 CSP 策略 |
| 触发原因 | 当前安全头基础存在，但 CSP 未完整定义 |
| 主要改动方向 | 定义 `default-src`、`script-src`、`style-src`、`img-src`、`connect-src` 等策略；开发和生产可分环境配置 |
| 不做什么 | 不用过宽 `unsafe-*` 作为长期默认 |
| 验收标准 | 主要页面无 CSP 违规；安全头测试覆盖；生产默认严格 |
| 验证命令或证据 | 安全头单元测试；浏览器控制台无 CSP error |
| 依赖关系 | 可独立排期 |


### P3-2 前端测试框架升级

| 字段 | 内容 |
|---|---|
| 任务ID | `P3-2` |
| 优先级 | P3 |
| 状态 | `TODO` |
| 目标 | 从原生 `node --test` 升级到 Vitest 或等价框架，并输出覆盖率报告 |
| 触发原因 | 当前前端测试缺少覆盖率统计和质量门禁 |
| 主要改动方向 | 引入 Vitest；迁移现有测试；CI 增加覆盖率报告和阈值 |
| 不做什么 | 不在测试框架迁移中重写前端功能 |
| 验收标准 | 现有前端测试全部迁移并通过；覆盖率报告可生成；CI 阈值明确 |
| 验证命令或证据 | `npm test` 或新脚本输出；coverage artifact |
| 依赖关系 | 可独立排期 |


### P3-3 分布式锁与 Gunicorn worker 配置化

| 字段 | 内容 |
|---|---|
| 任务ID | `P3-3` |
| 优先级 | P3 |
| 状态 | `TODO` |
| 目标 | 文件锁升级为可选 Redis 分布式锁，Gunicorn worker 数通过环境变量配置 |
| 触发原因 | 当前文件锁不支持多节点，生产 compose 中 worker 数固定偏低 |
| 主要改动方向 | 增加 Redis lock backend；保留本地文件锁 fallback；新增 `GUNICORN_WORKERS` 和 `GUNICORN_THREADS` 配置 |
| 不做什么 | 不引入复杂 HA 集群方案；不移除单机开发路径 |
| 验收标准 | 多实例竞争同一资源时可互斥；无 Redis 时 fallback 正常；worker 配置由环境变量控制 |
| 验证命令或证据 | 并发锁测试；compose 配置检查；多进程 smoke |
| 依赖关系 | 与 `P1-1` Redis 开发环境协同 |


### P3-4 证据图谱可视化

| 字段 | 内容 |
|---|---|
| 任务ID | `P3-4` |
| 优先级 | P3 |
| 状态 | `TODO` |
| 目标 | 提供发现-证据-来源的三层图谱 API 或前端可视化 |
| 触发原因 | 当前证据链存在但缺少直观展示，研究人员难以快速理解支撑结构 |
| 主要改动方向 | 增加 evidence graph 数据接口；前端展示 finding、evidence snippet、source、confidence 关系 |
| 不做什么 | 不改变证据门控规则；不把低置信证据展示成确定事实 |
| 验收标准 | 至少一个报告可生成证据图谱；节点和边可追溯到原始证据；低置信信息有明显标识 |
| 验证命令或证据 | API 响应样例；前端截图；证据链回溯 smoke |
| 依赖关系 | 建议在 `P2-4` ReasoningTrace 结构化后执行 |


## 5. 交接协议

每次新会话、上下文压缩后恢复、或不同模型接手时，执行者必须按以下顺序启动：

1. 读取本文，确认最高优先级未完成任务。
2. 读取对应代码和测试，不依赖历史聊天记忆。
3. 若任务状态为 `TODO`，改动前在工作说明中声明任务 ID、目标和验收标准。
4. 实现时只改当前任务必要范围，避免跨优先级顺手重构。
5. 验证通过后，将本文对应任务状态更新为 `DONE`，填写提交号、验证命令和结果摘要。
6. 若无法完成，将状态更新为 `BLOCKED`，写明阻塞原因、已验证事实和下一步需要的决策。

## 6. 全局验证清单

每个阶段结束时必须执行以下检查：

| 检查项 | P0 | P1 | P2/P3 |
|---|:---:|:---:|:---:|
| 后端相关单元/集成测试 | 必须 | 必须 | 涉及时必须 |
| 前端测试/build | 涉及时必须 | 涉及时必须 | 涉及时必须 |
| `git diff --check` | 必须 | 必须 | 必须 |
| 安全扫描或代码 grep | API Key/认证必须 | 涉及时必须 | 涉及时必须 |
| 手工 smoke 或端到端证据 | 必须 | 建议 | 建议 |

P0 阶段额外准入测试：

- `QUEUE_BACKEND=rq` 模式下提交任务，worker 真实执行。
- API Key 哈希不再使用 SHA256。
- 认证状态在服务重启后仍可用。
- staging 环境跑通一次完整 5 步消费者仿真工作流。

## 7. 当前下一步

当前 `P0-2` 已进入 `IN_PROGRESS`：代码修复已完成，但本机缺少 Python/uv/pytest，尚未完成测试验收。下一步应先在可运行 Python/uv 的环境中刷新 `backend/uv.lock` 并运行 `backend/tests/test_auth.py`；通过后将 `P0-2` 改为 `DONE`，再启动 `P0-3` 认证持久化或 `P0-1` RQ 联调。

### P1-6 数据库索引优化
- 状态: DONE ✅
- 提交: 3e8335b
- 执行方式: Codex CLI (codex exec)
- 文件: backend/alembic/versions/20260508_0003_add_performance_indexes.py, backend/tests/test_migration_indexes.py
- 测试: 40 passed

### P1-2 Redis缓存层
- 状态: DONE ✅
- 提交: 9f3724f
- 执行方式: Codex CLI (codex exec)
- 文件: backend/app/services/application/redis_cache.py, backend/tests/test_redis_cache.py
- 测试: 50 passed
