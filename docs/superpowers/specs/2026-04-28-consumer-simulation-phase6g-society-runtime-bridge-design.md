# MiroConsumer Phase 6G 大规模消费者社会桥接执行规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-28 |
| 阶段 | Phase 6G |
| 阶段名称 | 大规模消费者社会桥接 |
| 目标工作区 | `D:\project\MiroFish\.worktrees\phase5a-identity` |
| 目标分支 | `codex/phase5-closure` |
| 文档状态 | 审核基线 |

## 阶段依赖图

```text
Phase 6F 消费者语义激活
  -> Phase 6G 大规模消费者社会桥接
  -> Phase 6H 多渠道消费者传播
  -> Phase 6I 虚拟焦点小组
  -> Phase 7 生产化
```

依赖规则固定为：

- Phase 6G 必须依赖 Phase 6F 的 consumer event ontology。
- Phase 6G 必须产出 unified role enum。
- Phase 6H 必须依赖 Phase 6G 的 society runtime。
- Phase 6I 必须依赖 Phase 6G 的 unified role enum。
- Phase 7 必须依赖 Phase 6G 的 society schema 稳定版本。

## 2. 阶段目标

Phase 6G 必须把 MiroFish 原生大规模 Agent 社会能力接入 MiroConsumer consumer 模式，并形成 `Consumer Society Runtime`。

本阶段必须完成从少量核心 persona 到分层消费者社会的执行桥接。系统必须在不让全部 agent 调用大模型的条件下，产出稳定的传播压力、态度迁移、误读扩散、信任修复和购买意愿变化信号。

## 3. 阶段边界

### 3.1 必须交付

1. Consumer society 数据模型。
2. Population factory。
3. Persona variation generator。
4. Persona quality checker。
5. Society runtime。
6. OASIS adapter。
7. Consumer event mapper。
8. Society metrics aggregator。
9. Society report adapter。
10. Society run 配置。
11. 成本控制与早停规则。
12. 大社会确定性测试。

### 3.2 禁止纳入

本阶段禁止纳入以下工作：

- 多渠道传播策略。
- Xiaohongshu / Douyin / WeChat / ecommerce review 渠道规则。
- 虚拟焦点小组 UI。
- 数据库仓库。
- 队列执行器。
- 多实例锁。
- 生产 Docker。
- 真实外部市场数据抓取。

## 4. Society 模式

系统必须支持三档 society mode。

| mode | core persona 数量 | expanded persona 数量 | shadow agent 数量 | 用途 |
|---|---:|---:|---:|---|
| `quick` | 8 | 0 | 0 | 快速演示 |
| `standard` | 12 至 20 | 40 至 80 | 200 | 日常业务测试 |
| `large_society` | 20 至 50 | 100 至 250 | 1000 | 重要上市前推演 |

默认 mode 固定为 `quick`。

`standard` 和 `large_society` 必须通过显式配置启用。配置键固定为：

```env
ENABLE_SOCIETY_MODE=true
MAX_SOCIETY_AGENTS=1000
DEFAULT_SOCIETY_MODE=quick
```

## 5. 推理分层

系统必须实现四层推理。

| 层级 | 名称 | 推理方式 | 产物 |
|---|---|---|---|
| L1 | core persona | LLM 深度推理 | VOC、访谈、解释 |
| L2 | expanded persona | 轻量 LLM 或模板增强 | 人群差异、稳定性信号 |
| L3 | shadow agents | 规则、概率、状态机 | 大规模扩散压力 |
| L4 | audit sample | LLM 二次复核 | 异常现象解释 |

硬性规则：

- L1 必须保留原有 persona pack 行为。
- L2 必须继承 L1 segment 特征并加入个体扰动。
- L3 禁止直接调用 LLM。
- L4 仅对聚合异常进行抽样复核。
- 单次运行的 LLM 调用数量必须由 budget manager 控制。

## 6. 新增目录

必须新增目录：

```text
backend/app/services/consumer/society/
```

目录必须包含：

```text
__init__.py
population_models.py
population_factory.py
persona_variation_generator.py
persona_quality_checker.py
society_runtime.py
oasis_adapter.py
event_mapper.py
metrics_aggregator.py
report_adapter.py
budget_manager.py
state_store.py
consumer_roles.py
```

## 6.1 Unified Role Enum

Phase 6G 是 consumer role enum 的唯一归属阶段。

必须新增：

```text
backend/app/services/consumer/society/consumer_roles.py
```

必须定义：

```python
class ConsumerRole(str, Enum):
    Advocate = "advocate"
    Skeptic = "skeptic"
    Misreader = "misreader"
    Amplifier = "amplifier"
    Lurker = "lurker"
    PriceSensitive = "price_sensitive"
    TrustRepairable = "trust_repairable"
    Blocker = "blocker"
```

Phase 6F 禁止定义 role enum。Phase 6I 必须导入 `ConsumerRole`。Phase 6H 只能在 channel metrics 中引用 `ConsumerRole`。

## 7. 数据模型

### 7.1 ConsumerSocietyAgent

`population_models.py` 必须定义：

```python
@dataclass
class ConsumerSocietyAgent:
    agent_id: str
    parent_persona_id: str
    layer: str
    segment: str
    role: str
    traits: dict
    channel_affinity: dict
    evidence_sensitivity: float
    price_sensitivity: float
    trust_baseline: float
    share_propensity: float
    skepticism: float
    state: dict
```

`layer` 取值固定为：

```text
core
expanded
shadow
audit_sample
```

`role` 必须使用 `consumer_roles.ConsumerRole`。

### 7.2 ConsumerSocietyRunConfig

必须定义：

```python
@dataclass
class ConsumerSocietyRunConfig:
    mode: str
    core_persona_count: int
    expanded_persona_count: int
    shadow_agent_count: int
    max_rounds: int
    random_seed: int
    llm_budget_limit: int
    audit_sample_size: int
```

### 7.3 ConsumerSocietySnapshot

必须定义：

```python
@dataclass
class ConsumerSocietySnapshot:
    simulation_id: str
    run_id: str
    round_index: int
    agents_count: int
    events: list[dict]
    metrics: dict
    representative_agent_ids: list[str]
```

## 8. Population Factory

必须新增：

```text
backend/app/services/consumer/society/population_factory.py
```

职责固定为：

1. 从 persona pack 读取 core persona。
2. 生成 expanded persona。
3. 生成 shadow agents。
4. 分配 role。
5. 分配初始 state。
6. 分配传播倾向。
7. 输出完整 population。

Population factory 必须满足：

- 同一 `random_seed` 生成完全一致 population。
- 不同 `random_seed` 生成不同 agent id 与扰动值。
- 每个 expanded persona 必须保留 parent persona segment。
- 每个 shadow agent 必须关联 parent persona。
- 每个 role 至少占 population 的 5%，`quick` 模式除外。
- `large_society` 模式 population 总数必须达到配置值。

## 9. Persona Variation Generator

必须新增：

```text
backend/app/services/consumer/society/persona_variation_generator.py
```

必须生成以下扰动：

- evidence_sensitivity
- price_sensitivity
- trust_baseline
- share_propensity
- skepticism
- category_familiarity
- risk_memory
- social_influence_weight

扰动范围固定为 `0.0` 至 `1.0`。

同一 parent persona 的 expanded persona 必须满足：

- segment 不变。
- attention drivers 继承。
- risk sensitivities 继承。
- 数值特征发生扰动。
- role 发生分布变化。

## 10. Persona Quality Checker

必须新增：

```text
backend/app/services/consumer/society/persona_quality_checker.py
```

校验规则固定为：

- population 总数等于配置目标。
- agent_id 全局唯一。
- parent_persona_id 非空。
- layer 取值合法。
- role 取值合法。
- 每个数值特征在 `0.0` 至 `1.0`。
- segment 分布不能全部集中在一个 segment。
- `standard` 和 `large_society` 模式必须存在 shadow agents。

校验失败必须抛出 `ValueError`。

## 11. Society Runtime

必须新增：

```text
backend/app/services/consumer/society/society_runtime.py
```

职责固定为：

1. 加载 simulation。
2. 加载 consumer brief。
3. 加载 persona pack。
4. 构建 population。
5. 执行 round。
6. 生成 consumer events。
7. 更新 agent state。
8. 聚合 society metrics。
9. 写入 snapshots。
10. 输出 report adapter context。

Runtime 必须实现 mock deterministic mode：

- `SOCIETY_DETERMINISTIC_MODE=mock` 时，同一输入、同一 seed、同一 mode，输出 snapshots 完全一致。
- 生产 LLM 模式不要求 byte-for-byte 一致。
- 生产 LLM 模式必须保证结构字段、数值范围、事件类型集合、schema 版本一致。
- 所有随机数必须来自统一 RNG。
- 禁止使用全局随机状态。

## 12. OASIS Adapter

必须新增：

```text
backend/app/services/consumer/society/oasis_adapter.py
```

映射规则固定为：

| OASIS 概念 | Consumer 概念 |
|---|---|
| Agent Profile | Consumer Persona / Segment |
| Platform | Consumer Society Context |
| Action | Consumer Event |
| Memory | Category / Brand Memory Signal |
| Simulation Result | Consumer Research Metrics |

本阶段 OASIS adapter 必须作为转换层存在。Society runtime 不得直接依赖 OASIS 原始 action schema。

## 13. Event Mapper

必须新增：

```text
backend/app/services/consumer/society/event_mapper.py
```

输入：

- agent state
- round index
- visible claims
- previous events
- brief context
- research findings

输出必须符合 Phase 6F `consumer_event_type`。Event mapper 必须导入 Phase 6F `event_ontology.py`，禁止重新定义 consumer event type。

Event mapper 必须覆盖：

- FIRST_IMPRESSION
- ASK_PROOF
- AMPLIFY_CLAIM
- MISREAD_CLAIM
- PRICE_RESISTANCE
- TRUST_DECAY
- TRUST_RECOVERY
- PURCHASE_INTENT_UP
- PURCHASE_INTENT_DOWN
- NEGATIVE_CASCADE

## 14. Metrics Aggregator

必须新增：

```text
backend/app/services/consumer/society/metrics_aggregator.py
```

必须输出：

```json
{
  "reach_rate": 0.0,
  "cascade_depth": 0,
  "cross_segment_spread": 0.0,
  "amplifier_ratio": 0.0,
  "skeptic_ratio": 0.0,
  "lurker_ratio": 0.0,
  "misread_rate": 0.0,
  "negative_cascade_probability": 0.0,
  "trust_decay_rate": 0.0,
  "trust_recovery_rate": 0.0,
  "evidence_demand_rate": 0.0,
  "price_resistance_index": 0.0,
  "purchase_intent_delta": 0.0
}
```

所有比例指标取值范围固定为 `0.0` 至 `1.0`。

## 15. Report Adapter

必须新增：

```text
backend/app/services/consumer/society/report_adapter.py
```

必须把 society snapshots 转成 report context 字段：

```json
{
  "society_mode": "standard",
  "society_agents_count": 200,
  "society_metrics": {},
  "representative_agents": [],
  "society_event_summary": {},
  "society_risk_summary": {},
  "society_purchase_intent_summary": {}
}
```

ReportAgent 必须在 consumer mode 报告中读取上述字段。

## 16. Budget Manager

必须新增：

```text
backend/app/services/consumer/society/budget_manager.py
```

必须控制：

- max LLM calls
- max core persona calls
- max expanded persona calls
- audit sample size
- early stop round

硬性限制：

- `quick` 模式 LLM calls 不得超过 core persona 数量乘以 round 数。
- `standard` 模式 L3 shadow agents 不得调用 LLM。
- `large_society` 模式 LLM calls 必须小于 agent 总数的 10%。

预算超限必须终止 LLM 调用并继续执行规则层传播。

## 17. State Store

必须新增：

```text
backend/app/services/consumer/society/state_store.py
```

本阶段使用文件系统存储。

存储路径固定为：

```text
backend/uploads/simulations/<simulation_id>/society/
```

必须写入：

```text
population.json
society_config.json
society_rounds.jsonl
society_metrics.json
```

禁止引入数据库。

## 18. API 集成

### 18.1 `start_simulation` 集成点

必须修改：

```text
backend/app/services/application/simulation_app_service.py
backend/app/services/simulation_runner.py
backend/app/api/simulation.py
```

集成规则固定为：

- `SimulationAppService.start_simulation()` 必须读取 `society_mode`、`society_seed`、`society_max_agents`、`society_audit_sample_size`。
- `project_type != "consumer_test"` 时禁止启动 society runtime。
- `society_mode="quick"` 时必须继续走现有 consumer runner，并额外输出 society summary 空壳字段。
- `society_mode in ("standard", "large_society")` 时必须调用 `ConsumerSocietyRuntime.run()`.
- `SimulationRunner._start_consumer_simulation()` 必须接收 society config。
- Branch resume 必须复制 base run 的 society config。
- Branch resume 必须写入独立 `run_id`。
- Report context 必须通过 `society/report_adapter.py` 合并 society 字段。

### 18.2 API payload

必须扩展既有 simulation start payload。

新增字段：

```json
{
  "society_mode": "quick",
  "society_seed": 12345,
  "society_max_agents": 200,
  "society_audit_sample_size": 12
}
```

规则：

- 缺少 `society_mode` 时固定使用 `quick`。
- `ENABLE_SOCIETY_MODE=false` 时禁止启动 `standard` 和 `large_society`。
- `society_max_agents` 超过 `MAX_SOCIETY_AGENTS` 时返回 400。
- branch resume payload 缺少 society 字段时必须继承 base run society config。

## 19. 前端集成

本阶段前端只显示 society runtime 状态，不做多渠道界面。

必须新增：

```text
frontend/src/components/consumer/SocietyRunSummary.vue
```

必须展示：

- society mode
- agents count
- rounds completed
- LLM budget used
- reach rate
- misread rate
- trust recovery rate
- purchase intent delta

必须挂载到：

```text
frontend/src/components/Step3Simulation.vue
frontend/src/components/Step4Report.vue
```

## 20. 测试规格

必须新增后端测试：

```text
backend/tests/consumer/society/test_population_factory.py
backend/tests/consumer/society/test_persona_variation_generator.py
backend/tests/consumer/society/test_persona_quality_checker.py
backend/tests/consumer/society/test_event_mapper.py
backend/tests/consumer/society/test_metrics_aggregator.py
backend/tests/consumer/society/test_budget_manager.py
backend/tests/consumer/society/test_society_runtime.py
backend/tests/api/test_consumer_society_runtime.py
```

必须新增前端测试：

```text
frontend/tests/societyRunSummary.test.js
```

测试必须覆盖：

- 同 seed population 一致。
- 不同 seed population 不一致。
- mock deterministic mode snapshots 一致。
- production LLM mode 只校验 schema 与数值范围。
- role 分布达标。
- shadow agents 不调用 LLM。
- budget 超限后规则层继续执行。
- society metrics 范围合法。
- snapshots 写入路径正确。
- report context 包含 society 字段。
- API 对超限 agent 数返回 400。

## 21. 验收命令

后端验收必须运行：

```bash
cd backend
python -m pytest tests/consumer/society/ -q
python -m pytest tests/api/test_consumer_society_runtime.py -q
python -m pytest tests/ --tb=short -q
```

前端验收必须运行：

```bash
cd frontend
node --test tests/*.test.js tests/composables/*.test.js
npm run build
```

仓库验收必须运行：

```bash
git diff --check
```

## 22. 退出条件

Phase 6G 退出必须同时满足：

1. `quick`、`standard`、`large_society` 三档配置存在。
2. Population factory 生成分层消费者社会。
3. Shadow agents 不调用 LLM。
4. Society runtime 输出 snapshots。
5. Society metrics 输出固定字段。
6. Report context 包含 society 字段。
7. API 启动 society runtime 并执行限制校验。
8. 前端展示 society run summary。
9. 新增后端测试通过。
10. 新增前端测试通过。
11. 全量后端测试通过。
12. 前端 node 测试通过。
13. 前端 build 通过。
14. `git diff --check` 无输出。
