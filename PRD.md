# 产品需求文档（PRD）：MiroConsumer 消费者传播测试

## 1. 产品背景

MiroConsumer 已具备完整的 `图谱构建 -> 仿真准备 -> 仿真运行 -> 报告生成 -> 深度交互` 主链路，但当前能力仍偏通用仿真。消费者项目则沉淀了 `BusinessBrief`、消费者画像、评分逻辑和研究报告结构，但核心评估方式仍偏静态、单轮、并发评审。

本项目的目标不是新增一套平行产品，也不是替换 MiroConsumer 通用仿真底座，而是：

- 以 MiroConsumer 通用仿真底座为主骨架
- 将消费者项目中的领域能力迁入 MiroConsumer
- 先落地一个可执行的 Phase 1：`概念测试 + 文案测试 + 群体传播增强`

## 2. 当前版本定位

当前版本定位为：

> 一个由 MiroConsumer 驱动的、面向概念测试与文案测试的消费者传播仿真工作流。

它的价值不是再做一次静态打分，而是模拟消费者在“初见反应 -> 群体传播 -> 态度分化 -> 误读放大 -> 报告归因”中的连续变化。

## 3. Phase 1 范围

### 3.1 本轮纳入范围

- 测试类型：
  - `concept_test`
  - `copy_feedback`
- 输入契约：
  - `BusinessBrief`
  - 概念素材
  - 文案素材
  - claims
  - 目标人群
  - 使用场景
  - 研究目标
  - 可选背景材料
- 核心能力：
  - 消费者画像映射
  - visibility-aware consumer graph
  - Round 0 初见反应
  - Round 1-N 传播演化
  - VOC 保留与证据归因
  - 消费者传播测试报告
  - 报告后追问交互

### 3.2 本轮明确不做

- 全自动全网预研
- DingTalk 群聊工作流
- 包装测试
- A/B 测试
- 价格测试
- 认证、数据库、Celery 等外围系统迁移
- 品牌订阅化、行业脑资产化

## 4. 架构原则

### 4.1 MiroConsumer 通用底座为主

MiroConsumer 通用仿真底座继续保留并主导：

- `/api/graph -> /api/simulation -> /api/report` 主链路
- Graph / GraphRAG 结构
- Simulation Manager / Runner
- Report Agent 与深度交互 UI
- 现有 5 步工作台体验

### 4.2 消费者项目提供领域能力

从消费者项目迁入的核心能力包括：

- `BusinessBrief` 输入契约
- persona pack
- scoring / evidence / recommendation 结构
- 消费者测试报告 schema

### 4.3 向下兼容是硬约束

- `project_type` 可选
- 默认值为 `default`
- 当前端不显式传入 `consumer_test` 时，系统必须完全走原版通用仿真逻辑
- 只有显式传入 `project_type=consumer_test` 时，才进入消费者测试分支

## 5. Phase 1 目标工作流

1. 用户提交一份消费者测试版 `BusinessBrief`
2. 系统将输入标准化为 `BusinessBrief`
3. 加载消费者 persona pack
4. 构建 consumer graph
5. 执行 Round 0 初见反应
6. 执行 Round 1-N 传播演化
7. 提取 summary / evidence / VOC
8. 生成消费者传播测试报告
9. 在 Step 5 中支持继续追问报告代理或代表性消费者

### 5.1 关键仿真约束

- Round 0 只允许 Agent 访问 `BusinessBrief` 中的概念、文案与基础 claims
- consumer graph 节点带有可见性层级：
  - `Initial`
  - `Propagation_Only`
  - `Restricted`
- 只有在传播阶段，且 Agent 具备“高搜索倾向 / 高认知”等画像特征时，才允许检索深层风险信息
- 每轮传播 Prompt 都必须置顶 `Pinned BusinessBrief Summary`

## 6. 输出定义

Phase 1 的核心输出是《消费者传播测试报告》，至少回答：

- 初始接受度如何
- 传播后接受度如何变化
- 哪些点形成高共鸣
- 哪些点形成争议或误读
- 哪类消费者成为扩散者、放大者、阻断者、观望者
- 概念和文案各自应如何调整

报告中必须保留代表性 VOC 原声，不能只输出抽象比例。

## 7. 当前项目状态（2026-04-21）

### 7.1 Phase 1 已完成（基线）

- 后端消费者域能力已落地：
  - `Project` 增加 `project_type / consumer_brief / consumer_context`
  - `backend/app/services/consumer/` 已包含：
    - `models.py`
    - `brief_adapter.py`
    - `persona_pack.py`
    - `graph_builder.py`
    - `orchestrator.py`
    - `scoring.py`
    - `report_context.py`
  - `/api/graph` 已支持 `consumer_test` 项目创建与 graph build 分支
  - `/api/simulation` 已支持 `consumer_test` 的 create / prepare / consumer-summary / start 分支
  - `/api/report` 已支持消费者报告上下文与报告分支
- 前端消费者入口与工作台适配已完成：
  - 首页已支持 `consumer_test` 输入
  - Step 2-5 已增加消费者模式展示
  - Step 3 已支持 consumer summary / VOC
  - Step 4/5 已支持消费者报告标签、推荐追问、VOC 展示
  - 中英文 locale 已补齐消费者模式文案

### 7.2 Phase 2 已完成（realism 升级）

Phase 2 在 Phase 1 基线上增加了以下能力：

- **自动预研与背景材料挂载（`research_mode / auto_enrich`）**
  - `ConsumerBusinessBrief` 新增 `research_mode` 字段（`manual_only` / `auto_enrich`）
  - `research_ingest.py`：将手动背景材料与 `auto_enrich` 产出统一转换为 `ResearchFinding`
  - `default_auto_research_provider`：基于 brief 内容做确定性合成，产出带 `source_label='auto_enrich'` 的发现
  - 自动预研结果写入 graph（`ResearchFinding` 节点）和 simulation config（`consumer_config.json`）

- **信息分层与画像感知可见性（persona-aware knowledge visibility）**
  - `access_policy.py`：`resolve_visible_findings()` 按 round 和画像特征（`search_propensity` + `cognition_level`）过滤发现
  - 规则：Round 0 仅 `Initial`；Round 1+ `Propagation_Only` 对所有消费者可见；`Restricted` 仅对高搜索+高认知画像可见
  - `build_knowledge_view()` 统一封装可见节点 + 可见发现

- **传播事件建模（propagation events as typed evidence）**
  - `event_engine.py`：五类传播事件（`positive_relay`, `skeptical_challenge`, `misread_amplification`, `risk_discovery`, `clarification_recovery`）
  - `classify_propagation_event()` 按态度变化 + 触发类型 + 言语行为自动归类
  - `build_propagation_event()` 生成带 `trigger_finding_ids` 和 `supporting_quote` 的 typed event
  - `orchestrator.py` 在 round snapshot 中附加 `propagation_events`

- **Phase 2 评分与报告因果字段**
  - `scoring.py` 新增 `ConsumerPhase2Summary`：含 `event_counts`、`top_risk_findings`、`top_clarification_opportunities`、`causal_voc_quotes`
  - `report_context.py` 新增 `build_consumer_report_context()`：输出 `causal_chains`、`event_led_reversals`、`persona_group_signals`
  - `simulation.py` consumer-summary 路由返回 Phase 2 字段；`report_agent.py` 渲染消费者报告时保留因果引用

- **前端 Step 2-5 Phase 2 展示**
  - `Home.vue` 与 `consumerBrief.js`：支持 `research_mode` 选择（手动 / 自动增强）
  - `Step2EnvSetup.vue`：展示研究模式、发现数量
  - `Step3Simulation.vue`：展示传播事件类型
  - `Step4Report.vue`：展示事件统计、风险发现、澄清机会、因果分析
  - `Step5Interaction.vue`：因果追问模板（触发原因、信号扩散、澄清恢复）
  - `locales/en.json` 与 `locales/zh.json`：Phase 2 标签与文案完整中英对齐

### 7.3 已验证与验收通过

- 后端测试：
  - `backend/.venv/Scripts/python.exe -m pytest`
  - 结果：`70 passed`
- 前端测试：
  - `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`
  - 结果：`18 passed`
- 前端构建：
  - `npm run build`
  - 结果：成功

- 真实链路验收（新 Zep API Key）：
  - 图谱构建（Zep）：通过，约 `15s`
  - 模拟创建：通过，即时返回
  - Prepare（`4` 个 profile）：通过，约 `21min`
  - 最终状态：`ready`
  - 产物确认：
    - `reddit_profiles.json`
    - `twitter_profiles.csv`
    - `simulation_config.json`
    - `state.json`

- `consumer_test` Phase 1 模块验收：
  - Persona Pack：`8` 个默认 persona 加载通过
  - Brief Adapter：`from_payload` 规范化通过
  - Graph Builder：`21 nodes / 20 edges / 三级 visibility` 通过
  - Orchestrator：Round 0 隐藏 `Restricted / Propagation_Only` 通过
  - Orchestrator：Round 2+ 高搜索画像可见全部节点通过
  - Orchestrator：Round 2+ 低搜索画像仅可见 `Propagation_Only` 通过
  - Scoring：`attitude shift + evidence bundle` 通过
  - Report Context：事件加载与 summary 生成通过
  - VOC 保留：`resonance / risk / misread quotes` 通过
  - API：project list/detail、simulation list/history、`GET /{sim_id}/consumer-summary` 通过
  - 向下兼容：默认 `project_type` 不受影响
  - Zep 集成：图谱构建与模拟准备通过

- `consumer_test` Phase 2 模块验收：
  - Research Ingest：手动背景材料转 typed findings 通过；`auto_enrich` provider 调用通过
  - Access Policy：Round 0 仅 `Initial` 通过；Round 2+ 高搜索可见 `Restricted` 通过；低搜索不可见通过
  - Event Engine：`misread_amplification` / `risk_discovery` / `clarification_recovery` 分类通过；event chain metadata 通过
  - Graph Builder：`ResearchFinding` 节点带 provenance 和 visibility 通过
  - Scoring Phase 2：`event_counts` / `top_risk_findings` / `causal_voc_quotes` 通过
  - Report Context Phase 2：`causal_chains` 含 `trigger_finding_ids` + `event_ids` 通过
  - API：`auto_enrich` graph build 产出 findings 通过；consumer-summary 返回 Phase 2 字段通过
  - 向下兼容：不传 `research_mode` 时默认 `manual_only`，不影响 Phase 1 行为

- `consumer_test` Phase 3 模块验收：
  - Phase 3A：双源 Tiered RAG 研究底座已落地，`Lane A` 支持上传资料与 URL 入库，`Lane B` 支持 public-web supplement，并保留 `source_catalog / enriched_findings / enriched_traces / retrieval trace`
  - Phase 3B：研究员干预与 branch rerun 已落地，支持 `clarification_injection / revised_claim_injection / evidence_reveal / fork from round N / branch resume / branch comparison`
  - Phase 3C：社会化沙盘升级已落地，支持 `community topology / bridge-amplifier-skeptic-lurker roles / cascade_metrics / social sandbox prompts`
  - Phase 3D：研究资产化与对比工作台已落地，支持 `research pack export / run_vs_run / branch_vs_base / project_vs_project / saved comparisons`
  - 后端总回归：`backend/.venv/Scripts/python.exe -m pytest tests -q --ignore=tests/integration`，结果：`270 passed`
  - 前端总回归：`node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`，结果：`61 passed`
  - 前端构建：`npm run build` 成功
  - 向下兼容：`project_type=default` 回归仍为绿灯，未被 Phase 3 改动破坏

结论：

- `consumer_test` Phase 1、Phase 2 与 Phase 3 均已完成并通过当前正式验收。

### 7.4 Phase 4A 已完成（可信度升级）

Phase 4A 在 Phase 3 基线上增加了可信决策层，使系统不仅能回答“发生了什么”，还能回答“证据有多可靠、结论有多强”。

- **源质量评分（Source Quality Scoring）**
  - `source_quality.py`：为 Lane A 和 Lane B 的每个 research source 计算 `trust_tier`、`freshness_score`、`source_confidence`、`coverage_tags` 和 `quality_reasons`
  - 用户上传材料默认高于匿名公开网络结果的信任层级
  - 质量评分对同一输入快照是确定性的

- **Lane B 治理强化（Lane B Governance Upgrade）**
  - `lane_b_provider.py` 增加最低片段质量检查、重复结果抑制、弱来源降级规则
  - `retrieval.py` 将治理决策（接受/拒绝）记录到检索追踪中
  - `finding_distiller.py` 仅使用通过治理的证据进行提炼

- **证据验证与置信度评分（Evidence Validation & Confidence Scoring）**
  - `evidence_validator.py`：为每个发现附加机器可读验证状态：`supported` / `weak_support` / `insufficient_support`
  - `confidence_scoring.py`：综合源质量、证据充分性、信号一致性计算发现级和报告级置信度
  - `scoring.py`、`report_context.py`、`comparison_engine.py` 分别将置信度附加到运行摘要、报告上下文和对比快照

- **报告与 UI 置信度展示（Report & UI Confidence Exposure）**
  - Step 2：展示研究源质量摘要（接受来源数、主导信任层级、证据充足度）
  - Step 4：展示发现置信度标签、证据充分性、对比差异的支持强度
  - Step 5：生成针对弱证据、低置信度结论和回放漂移的追问提示

- **基准回放与校准（Benchmark Replay & Calibration）**
  - `benchmark_registry.py` + `benchmark_replay.py`：支持注册基准案例、执行回放、将当前输出与已知基线对比
  - 回放产物持久化到 `backend/uploads/benchmarks/`，包括 manifest、expected signals、replay result
  - 使用稳定衍生信号（`acceptance_band`、`top_resonance_labels`、`cascade_band` 等）进行对齐比较，而非脆弱的原始文本匹配
  - 新增 API 路由：`POST /api/report/benchmarks/register`、`GET /api/report/benchmarks`、`POST /api/report/benchmarks/<id>/replay`、`GET /api/report/benchmark-replays/<id>`

- **Phase 4A 模块验收：**
  - Source Quality：`trust_tier` / `freshness_score` / `coverage_tags` 计算与持久化通过
  - Lane B Governance：重复过滤、弱片段拒绝、治理原因持久化通过
  - Evidence Validator：`supported` / `weak_support` / `insufficient_support` 状态附加通过
  - Confidence Scoring：发现级、报告级、对比级置信度计算通过
  - Benchmark Registry：注册、列表、读取通过
  - Benchmark Replay：回放执行、对齐比较、产物持久化通过
  - API：benchmark 路由 consumer_test 门控通过；非 consumer 项目正确拒绝通过
  - 向后兼容：`project_type=default` 不受影响；无 Phase 4A 产物的旧 consumer 项目以 `unknown` / `not_scored` 回退加载

- **Phase 4A 回归结果（2026-04-22）：**
  - 后端 benchmark 模块测试：`17 passed`
  - 后端 benchmark 路由测试：`7 passed`
  - 后端完整非集成回归：`347 passed`
  - 前端定向回归：`73 passed`
  - 前端构建：成功
  - 手工 route-level smoke：`graph/build -> simulation/create -> prepare -> start(max_rounds=3) -> consumer-summary -> research-assets/export -> benchmark register/replay` 全链路通过
  - 手工 smoke 关键结果：
    - `source_quality_summary`：`source_count=2`、`lane_a_count=1`、`lane_b_count=1`、`average_source_confidence=0.725`
    - 运行结果：`profiles=8`、`runner_status=completed`、`current_round=3`、`total_actions_count=24`
    - 报告级可信度：`confidence_label=medium`、`confidence_score=0.5696`
    - 证据验证摘要：`weak_support=8`、`insufficient_support=7`
    - Benchmark replay：`alignment_status=aligned`

结论：

- `consumer_test` Phase 1、Phase 2、Phase 3 与 Phase 4A 均已完成并通过当前正式验收。

### 7.6 Phase 4C 已完成（效率与工程化升级）

Phase 4C 在 Phase 4A 的可信度基线上，补齐了效率、兼容性和工程可维护性三条线，使系统不仅“可解释”，也更“可重复、可复用、可稳定运行”。

- **Prepare Manifest 与复用可观测性**
  - 新增 `backend/app/services/prepare_manifest.py`
  - prepare 成功后会在 simulation workspace 写入 `prepare_manifest.json`
  - `POST /api/simulation/prepare` 与 `POST /api/simulation/prepare/status` 会暴露 `prepare_manifest`
  - 重复 prepare 会累加 `reuse_count` 并记录 `last_reused_at`

- **LLM JSON 兼容层**
  - `backend/app/utils/llm_client.py` 新增统一 JSON 兼容路径：
    - `chat_with_finish_reason()`
    - `clean_llm_text()`
    - `extract_json()`
    - `chat_json_with_meta()`
  - `oasis_profile_generator.py` 与 `simulation_config_generator.py` 不再各自维护重复的 `json_object` 解析逻辑
  - 当 provider / proxy 对 `response_format=json_object` 兼容性波动时，系统会回退到 plain-text JSON-only 路径

- **前端 warning 清理与分包**
  - `Home.vue` 改为统一静态导入 `pendingUpload`
  - 非首页路由改为 lazy import
  - `frontend/vite.config.js` 增加 manual chunking
  - 原有 `pendingUpload.js` mixed import warning 已清除
  - 原有 Vite chunk size warning 已清除

- **Phase 4C 回归结果（2026-04-22）：**
  - 后端定向回归：`57 passed`
  - 后端完整非集成回归：`373 passed`
  - 前端定向回归：`73 passed`
  - 前端 build：成功

结论：

- `consumer_test` Phase 1、Phase 2、Phase 3、Phase 4A 与 Phase 4C 均已完成并通过当前正式验收。

### 7.7 Phase 4B 已完成（测试类型扩展）

Phase 4B 在既有 `consumer_test` 主链路上扩展了 3 类新的消费者测试任务，使系统从“概念/文案传播测试”升级为更完整的消费者测试工作台。

- **新增任务类型**
  - `packaging_test`
  - `ab_test`
  - `price_test`

- **Brief / Schema 扩展**
  - `ConsumerTaskType` 与 `ConsumerBusinessBrief` 已支持：
    - `packaging_assets`
    - `test_variants`
    - `price_points`
    - `price_context`
  - 旧的 `concept_test` / `copy_feedback` 保持向后兼容
  - 旧式 `variants: ["A", "B"]` 输入会自动规范化到 `test_variants`

- **图谱与仿真扩展**
  - 图谱层新增 `PackagingCue`、`Variant`、`PricePoint` 节点支持
  - `simulation_runner` 与 `orchestrator` 已支持 task-aware prompt focus：
    - 包装测试强调包装线索、货架吸引力与信任感
    - A/B 测试强调变体比较
    - 价格测试强调价格感知、价值权衡与购买意向

- **报告与交互扩展**
  - `consumer-summary` / `report_context` 已暴露 `task_type`
  - `packaging_test` 输出：
    - `top_packaging_hooks`
    - `top_trust_objections`
    - `top_confusion_triggers`
  - `ab_test` 输出：
    - `winning_variant`
    - `top_variant_deltas`
    - `top_persona_divergences`
  - `price_test` 输出：
    - `acceptable_price_points`
    - `resisted_price_points`
    - `top_price_objections`
    - `price_context`
  - Step 4 / Step 5 已可基于这些字段展示任务化结果与推荐追问

- **Phase 4B 回归结果（2026-04-22）：**
  - 后端定向回归：`115 passed`
  - 后端完整非集成回归：`411 passed`
  - 前端定向回归：`89 passed`
  - 前端 build：成功

结论：

- `consumer_test` Phase 1、Phase 2、Phase 3、Phase 4A、Phase 4B 与 Phase 4C 均已完成并通过当前正式验收。

### 7.5 当前已知限制

- `auto_enrich` 已升级为双源 research 底座的一部分：当前包含 `Lane B` 外部检索 provider 与 deterministic fallback；若需更强的真实全网预研能力，后续仍建议替换为更稳定的外部 provider
- Kimi For Coding 响应较慢，单个 profile 约 `3-5` 分钟，`4` 个 profile 的完整 prepare 约 `21` 分钟
- 小规模 profile（如 `4` 个）可稳定运行；更大规模场景建议切换更快的模型
- `project_vs_project` 对比当前优先基于项目 research artifacts 与发现差异；若项目没有完整 run-level 结果，其接受度字段会保守显示

## 8. 风险与依赖

### 8.1 关键依赖

- 根目录 `.env` 中的 LLM / Zep 配置
- OASIS 运行环境
- 本地 Python 虚拟环境与前端依赖

### 8.2 当前主要风险

- 大规模 prepare 的耗时与模型成本仍偏高
- `json_object` 兼容性在不同模型或代理配置下仍可能波动
- `packaging_test` 当前仍是基于文本/描述符的包装测试，不包含真实视觉理解
- `price_test` 当前仍是价格感知与阈值测试，不是销量预测或外部定价数据建模
- 全局产品身份已统一为 `MiroConsumer`，Phase 5 Closeout 已完成品牌清理
- 当前 Flask route 层仍偏厚，随着功能继续增加，维护成本会上升
- 文件系统持久化尚未被 repository 接口完全包裹，后续替换存储介质的成本偏高
- persona pack 当前仍偏默认写死，不利于行业、品类、地域和客户自定义扩展
- evidence validation 目前虽已有评分与校验，但还没有完全升级为 executive summary / comparison / replay 的强门禁
- `consumer_test` 已形成主链路，但 bounded context 仍未彻底独立，和 legacy flow 仍有较多共居区域

### 8.3 Phase 5 收口更新（2026-04-23）——已完成

Phase 5 已完成，本轮的”产品化与架构收口”不再是待办，而是当前基线能力的一部分。

按批次交付的收口结果：

- **Batch 1**：完整 `MiroConsumer` 产品身份清理。消费者产品主表面统一为 `MiroConsumer`，补齐了首页/流程页/运行页/报告页/交互页等可见品牌位，以及包名与仓库展示口径。
- **Batch 2**：simulation/report 路由瘦身与新的 app service 落地。Flask route 进一步收敛到 application service，`graph / simulation / report / branch / benchmark` 的编排边界更加清晰；route 层回归 `parse -> validate -> call service -> return response` 的薄壳模式。
- **Batch 3**：task executor 抽象 + simulation artifacts 的 repository-first 推进。`task_executor` 统一封装了 prepare、run、report 等异步/同步任务的执行与重试语义；repository 层新增 `ProjectRepository / ConsumerStateRepository / SimulationRepository / BranchRepository / ReportRepository / BenchmarkRepository` 的 filesystem-backed 实现，文件系统持久化不再直接散落在 service 中。
- **Batch 4**：consumer bounded-context 扩展 + canonical consumer 路由 + typed contracts。新增 `app/api/consumer`、`consumer_app_service`、`api_guard`、`simulation_state_accessor` 等 consumer 自有边界模块；旧 `/api/simulation/.../consumer-summary` 路由保留为 compatibility shim；canonical consumer routes 与 typed request/response contracts 已落地。
- **Batch 5**：全套件稳定化 + canonical errors + observability/smoke gate。task executor observability 测试通过；canonical error response  shape 统一；smoke gate 确认 consumer blueprint 在 Flask 应用工厂中正确注册；全量回归达到 565 passed。

Phase 5 完成后，前面列出的几项 Phase 4 末尾残留问题已被实质收口：

- 全局产品身份残留问题已明显收敛，默认产品表面以 `MiroConsumer` 为主
- Flask route 厚度已继续下降，consumer-specific 编排不再主要散落在 route 中
- 文件系统持久化已通过 repository 接口包裹到更清晰的边界
- persona pack 不再是隐藏代码默认值，而是显式可选资产
- evidence validation 已从”评分”升级为”门禁”
- `consumer_test` 已拥有更清晰的 bounded context 入口与状态访问边界

Phase 5 最终验证结果（2026-04-23）：

- task executor observability：`python -m pytest tests/services/application/test_task_executor_observability.py -q` -> `9 passed, 1 warning`
- 后端核心子套件：`python -m pytest tests/api/ tests/consumer/ tests/services/application/ -q` -> `565 passed, 1 warning`
- 唯一剩余 warning 为预存的 `zep_cloud` / Python 3.14 兼容性警告，不影响功能
- 前端构建：`npm run build` 成功
- Flask app smoke：`/api/consumer/simulation/<simulation_id>/consumer-summary` 已在应用工厂中成功注册

## 9. 后续阶段与终局愿景

### Phase 4（已完成）

- `Phase 4A`：完成可信度升级，包括 source quality、evidence validation、confidence scoring 与 benchmark replay
- `Phase 4B`：完成测试覆盖面扩展，新增 `packaging_test`、`ab_test`、`price_test`
- `Phase 4C`：完成效率与工程化升级，强化 prepare/runtime 路径、缓存、回退和稳定性

### Phase 5（已完成，2026-04-23）

Phase 5 六项目标已全部完成，按批次交付如下：

- **Batch 1 — 产品身份收口**：全局消费者产品表面统一为 `MiroConsumer`，包括包名、日志名、首页品牌名、GitHub 链接、README、截图与 docker/service 命名
- **Batch 2 — Route 拆薄与 App Service 落地**：API route 层收敛为薄壳，新增 `graph_app_service`、`simulation_app_service`、`report_app_service`、`branch_app_service`、`benchmark_app_service`、`consumer_app_service`，route 只负责 parse / validate / call service / return response
- **Batch 3 — Task Executor 与 Repository 抽象**：`task_executor` 统一封装 prepare/run/report 执行与重试语义；文件持久化抽象为 `ProjectRepository`、`ConsumerStateRepository`、`SimulationRepository`、`BranchRepository`、`ReportRepository`、`BenchmarkRepository`，由文件系统实现承接
- **Batch 4 — Consumer Bounded Context 与 Canonical Routes**：`consumer_test` 主线进一步独立为 bounded context，新增 `app/api/consumer`、`ConsumerAppService`、`ConsumerApiGuard`、`ConsumerSimulationStateAccessor`；canonical consumer 路由与 typed contracts 已落地
- **Batch 5 — 全套件稳定化与 Observability**：canonical error shape 统一；task executor observability 验证通过；smoke gate 确认 consumer blueprint 注册正确；全量回归 565 passed，仅剩预存 `zep_cloud` / Python 3.14 兼容性警告

Phase 5 收口完成后，下一阶段（Phase 6 或等效新路线图）可安全推进：

- 多模态包装测试与创意 stimulus
- 更大规模 runtime 优化与模型路由改进
- category memory、benchmark library 扩充与 research operating system 特性

### 明确不纳入当前路线

- DingTalk / 外部焦点小组接口
