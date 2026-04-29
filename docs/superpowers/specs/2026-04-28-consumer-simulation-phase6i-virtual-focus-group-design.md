# MiroConsumer Phase 6I 虚拟焦点小组执行规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-28 |
| 阶段 | Phase 6I |
| 阶段名称 | 虚拟焦点小组 |
| 目标工作区 | `D:\project\MiroFish\.worktrees\phase5a-identity` |
| 目标分支 | `codex/phase5-closure` |
| 文档状态 | 审核基线 |

## 阶段依赖图

```text
Phase 6F 消费者语义激活
  -> Phase 6G 大规模消费者社会桥接
  -> Phase 6H 多渠道消费者传播
  -> Phase 6I 虚拟焦点小组
  -> Phase 6J 校准与可信度验收
  -> Phase 7 生产化
```

依赖规则固定为：

- Phase 6I 必须依赖 Phase 6F 的 `interview_consumers` target context。
- Phase 6I 必须依赖 Phase 6F 的 consumer event ontology。
- Phase 6I 必须依赖 Phase 6G 的 unified role enum、society agent state、society metrics。
- Phase 6I 必须依赖 Phase 6H 的 channel context、channel metrics、propagation path。
- Phase 6J 必须依赖 Phase 6I 的 interview history schema 稳定版本。
- Phase 7 必须依赖 Phase 6J readiness gate 通过。

## 2. 阶段目标

Phase 6I 必须把 MiroConsumer 的深度交互能力产品化为“和消费者社会互动”。

本阶段必须让用户围绕报告结论、传播路径、误读、价格阻力、证据修复和分支差异，直接追问代表性消费者并组织虚拟焦点小组。

## 3. 阶段边界

### 3.1 必须交付

1. Representative consumer card。
2. Single consumer interview。
3. Role-based interview presets。
4. Virtual focus group session。
5. Moderator prompt engine。
6. Follow-up question engine。
7. Interview evidence binder。
8. Interview summary synthesizer。
9. Focus group disagreement detector。
10. Focus group consensus detector。
11. Frontend interview workspace。
12. Frontend focus group workspace。
13. Interview history retrieval。
14. Focus group tests。

### 3.2 禁止纳入

本阶段禁止纳入以下工作：

- 新增大社会 runtime。
- 新增渠道 runtime。
- 数据库仓库。
- 队列执行器。
- 多实例锁。
- 生产 Docker。
- 真实用户访谈采集。
- 真实用户身份系统。

## 4. 用户任务

系统必须支持以下用户任务：

- 采访拥护者。
- 采访质疑者。
- 采访误读者。
- 采访价格敏感者。
- 采访高传播影响者。
- 采访信任修复者。
- 组建虚拟焦点小组。
- 围绕某个 report finding 追问。
- 围绕某条 propagation path 追问。
- 围绕某个 branch delta 追问。
- 生成下一轮 What-if 实验问题。

## 5. 后端模块

必须新增目录：

```text
backend/app/services/consumer/interview/
```

目录必须包含：

```text
__init__.py
interview_models.py
representative_card_builder.py
single_interview_service.py
focus_group_service.py
moderator_prompt_engine.py
followup_question_engine.py
evidence_binder.py
summary_synthesizer.py
disagreement_detector.py
history_store.py
representative_sampler.py
```

## 6. 数据模型

### 6.1 RepresentativeConsumerCard

`interview_models.py` 必须定义：

```python
@dataclass
class RepresentativeConsumerCard:
    agent_id: str
    display_name: str
    role: str
    segment: str
    channel_id: str
    attitude_start: str
    attitude_latest: str
    purchase_intent_start: float
    purchase_intent_latest: float
    key_quote: str
    influence_score: float
    evidence_ids: list[str]
    event_ids: list[str]
```

`role` 必须使用 Phase 6G `ConsumerRole`。Phase 6I 禁止定义新的 role enum。

### 6.2 ConsumerInterviewRequest

必须定义：

```python
@dataclass
class ConsumerInterviewRequest:
    simulation_id: str
    topic: str
    questions: list[str]
    agent_ids: list[str]
    roles: list[str]
    mode: str
    max_agents: int
    target_context: dict
```

`mode` 取值固定为：

```text
snapshot
live
auto
```

### 6.3 ConsumerInterviewResult

必须定义：

```python
@dataclass
class ConsumerInterviewResult:
    interview_id: str
    simulation_id: str
    topic: str
    mode: str
    answers: list[dict]
    evidence_map: dict
    summary: str
    followup_questions: list[str]
```

### 6.4 FocusGroupSession

必须定义：

```python
@dataclass
class FocusGroupSession:
    focus_group_id: str
    simulation_id: str
    topic: str
    moderator_goal: str
    participant_cards: list[dict]
    turns: list[dict]
    consensus: list[str]
    disagreements: list[str]
    next_what_if_experiments: list[str]
    evidence_map: dict
```

## 7. Representative Card Builder

必须新增：

```text
backend/app/services/consumer/interview/representative_card_builder.py
```

职责固定为：

1. 加载 Phase 6I representative sampler 输出。
2. 合并 channel metrics。
3. 合并 society metrics。
4. 合并 attitude history。
5. 合并 purchase intent history。
6. 输出 card。

每张 card 必须包含：

- 角色。
- 人群。
- 渠道。
- 关键 quote。
- 态度变化。
- 购买意愿变化。
- 影响分数。
- 证据引用。

## 7.1 Representative Sampler

必须新增：

```text
backend/app/services/consumer/interview/representative_sampler.py
```

职责固定为：

1. 加载 Phase 6G society agent state。
2. 加载 Phase 6H channel metrics。
3. 加载 Phase 6F consumer event ontology 输出。
4. 按 `ConsumerRole` 抽样消费者。
5. 输出 RepresentativeConsumerCard 输入数据。

抽样角色必须使用 Phase 6G `ConsumerRole`。

## 8. Single Interview Service

必须新增：

```text
backend/app/services/consumer/interview/single_interview_service.py
```

职责固定为：

1. 校验 simulation 为 consumer_test。
2. 选择 agent。
3. 构造消费者身份上下文。
4. 构造问题列表。
5. 执行 snapshot 或 live interview。
6. 绑定 evidence。
7. 生成 follow-up questions。
8. 写入 history。

Snapshot interview prompt 必须包含：

- persona segment。
- role。
- key quote。
- attitude history。
- consumer events。
- evidence context。
- target question。

Snapshot interview prompt 禁止包含：

- 系统内部路径。
- raw JSONL 文件名。
- `twitter`。
- `reddit`。
- `OASIS`。

## 9. Focus Group Service

必须新增：

```text
backend/app/services/consumer/interview/focus_group_service.py
```

职责固定为：

1. 选择参与者。
2. 构造 moderator prompt。
3. 执行每轮发言。
4. 记录 turns。
5. 检测共识。
6. 检测分歧。
7. 生成下一轮 What-if 实验。
8. 绑定 evidence。
9. 写入 history。

焦点小组轮次固定为：

| turn | 内容 |
|---:|---|
| 1 | 每位消费者回答主题问题 |
| 2 | 消费者回应彼此分歧 |
| 3 | moderator 追问证据、价格、信任、误读 |
| 4 | 每位消费者给出最终态度变化 |

`max_agents` 上限固定为 8。

## 10. Moderator Prompt Engine

必须新增：

```text
backend/app/services/consumer/interview/moderator_prompt_engine.py
```

Moderator prompt 必须包含：

- 研究目标。
- 被测 claim。
- 分支上下文。
- 渠道上下文。
- 证据上下文。
- 参与者角色。
- 禁止编造来源规则。

Moderator prompt 必须输出：

- 主问题。
- 追问问题。
- 冲突点。
- 证据检查点。
- What-if 实验方向。

## 11. Follow-up Question Engine

必须新增：

```text
backend/app/services/consumer/interview/followup_question_engine.py
```

必须生成固定类型追问：

- trust repair follow-up
- misread clarification follow-up
- price resistance follow-up
- evidence demand follow-up
- competitor comparison follow-up
- purchase intent follow-up
- share intent follow-up

输出固定为：

```json
{
  "followup_questions": [
    {
      "type": "trust_repair",
      "question": "...",
      "target_role": "skeptic"
    }
  ]
}
```

## 12. Evidence Binder

必须新增：

```text
backend/app/services/consumer/interview/evidence_binder.py
```

每个回答必须绑定：

- agent_id
- event_ids
- finding_ids
- source_ids
- quote_ids
- support_level

`support_level` 取值与 Phase 6F 一致。

## 13. Summary Synthesizer

必须新增：

```text
backend/app/services/consumer/interview/summary_synthesizer.py
```

访谈摘要必须包含：

- 核心结论。
- 最强支持 quote。
- 最强反对 quote。
- 误读点。
- 证据需求。
- 价格阻力。
- 信任修复条件。
- 下一轮 What-if 实验。

## 14. History Store

必须新增：

```text
backend/app/services/consumer/interview/history_store.py
```

本阶段使用文件系统存储。

路径固定为：

```text
backend/uploads/simulations/<simulation_id>/consumer_interviews/
```

必须写入：

```text
interviews.jsonl
focus_groups.jsonl
```

禁止引入数据库。

## 15. API 规格

必须扩展：

```text
backend/app/api/consumer.py
```

路由固定为：

```http
GET  /api/consumer/simulations/<simulation_id>/representative-agents
POST /api/consumer/simulations/<simulation_id>/interviews
POST /api/consumer/simulations/<simulation_id>/focus-groups
GET  /api/consumer/simulations/<simulation_id>/interviews/history
GET  /api/consumer/simulations/<simulation_id>/focus-groups/history
```

响应结构固定为：

```json
{
  "success": true,
  "data": {}
}
```

错误结构固定为：

```json
{
  "success": false,
  "error": "..."
}
```

HTTP 状态码固定为：

| 状态码 | 条件 |
|---|---|
| 200 | 成功 |
| 400 | 参数错误、非 consumer_test |
| 404 | simulation、agent、history 不存在 |
| 409 | live mode 环境未运行 |
| 500 | 服务异常 |

## 16. 前端组件

### 16.1 RepresentativeConsumerCard

必须新增：

```text
frontend/src/components/consumer/RepresentativeConsumerCard.vue
```

必须展示：

- 角色。
- 人群。
- 渠道。
- key quote。
- 态度变化。
- 购买意愿变化。
- 影响范围。
- 追问按钮。

### 16.2 RepresentativeConsumerInterview

必须新增或扩展：

```text
frontend/src/components/consumer/RepresentativeConsumerInterview.vue
```

必须支持：

- role filter。
- agent selection。
- topic input。
- question list。
- fixed prompt buttons。
- interview result view。
- follow-up question buttons。

### 16.3 VirtualFocusGroupPanel

必须新增或扩展：

```text
frontend/src/components/consumer/VirtualFocusGroupPanel.vue
```

必须支持：

- participant role selection。
- moderator goal input。
- run focus group。
- turn-by-turn view。
- consensus view。
- disagreement view。
- evidence map view。
- What-if experiment output。

### 16.4 InterviewHistoryPanel

必须新增：

```text
frontend/src/components/consumer/InterviewHistoryPanel.vue
```

必须展示：

- interview history。
- focus group history。
- topic。
- roles。
- created time。
- summary。
- reopen result。

## 17. 挂载点

必须修改：

```text
frontend/src/components/Step5Interaction.vue
frontend/src/components/Step4Report.vue
frontend/src/api/consumerFactory.js
frontend/src/api/consumer.js
frontend/src/utils/consumerMode.js
locales/en.json
locales/zh.json
```

挂载规则固定为：

- Step5 是访谈与焦点小组主入口。
- Step4 report action 的“追问消费者”必须打开 interview panel。
- Report finding 上下文必须传入 interview request 的 `target_context`。

## 18. 测试规格

必须新增后端测试：

```text
backend/tests/consumer/interview/test_representative_card_builder.py
backend/tests/consumer/interview/test_representative_sampler.py
backend/tests/consumer/interview/test_single_interview_service.py
backend/tests/consumer/interview/test_focus_group_service.py
backend/tests/consumer/interview/test_followup_question_engine.py
backend/tests/consumer/interview/test_evidence_binder.py
backend/tests/consumer/interview/test_summary_synthesizer.py
backend/tests/api/test_consumer_focus_group_routes.py
backend/tests/api/test_consumer_interview_history_routes.py
```

必须新增前端测试：

```text
frontend/tests/representativeConsumerCard.test.js
frontend/tests/representativeConsumerInterview.test.js
frontend/tests/virtualFocusGroupPanel.test.js
frontend/tests/interviewHistoryPanel.test.js
```

测试必须覆盖：

- card 字段完整。
- snapshot interview 不调用 live API。
- live mode 环境缺失返回 409。
- auto mode 执行 fallback。
- focus group 固定 4 turn。
- evidence binder 输出固定字段。
- summary synthesizer 输出固定章节。
- history store 写入 jsonl。
- 前端组件提交固定请求体。

## 19. 验收命令

后端验收必须运行：

```bash
cd backend
python -m pytest tests/consumer/interview/ -q
python -m pytest tests/api/test_consumer_focus_group_routes.py tests/api/test_consumer_interview_history_routes.py -q
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

## 20. 退出条件

Phase 6I 退出必须同时满足：

1. Representative consumer card 后端结构存在。
2. Single interview 服务存在。
3. Focus group 服务存在。
4. Follow-up question engine 存在。
5. Evidence binder 存在。
6. History store 写入固定路径。
7. 五个 consumer interview API 存在。
8. Step5 展示访谈主入口。
9. Step4 的追问入口打开访谈面板。
10. 前端展示访谈历史。
11. 新增后端测试通过。
12. 新增前端测试通过。
13. 全量后端测试通过。
14. 前端 node 测试通过。
15. 前端 build 通过。
16. `git diff --check` 无输出。
