# MiroConsumer Phase 6F 消费者语义激活执行规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-28 |
| 阶段 | Phase 6F |
| 阶段名称 | 消费者语义激活 |
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

- Phase 6F 是 Phase 6G、Phase 6H、Phase 6I、Phase 7 的 consumer action 与 event ontology 前置阶段。
- Phase 6G 必须依赖 Phase 6F 的 event ontology。
- Phase 6H 必须依赖 Phase 6G 的 society runtime 与 Phase 6F 的 event ontology。
- Phase 6I 必须依赖 Phase 6F 的 action target context、Phase 6G 的 unified role enum、Phase 6H 的 channel context。
- Phase 7 必须依赖 Phase 6F 至 Phase 6I 的稳定 schema。

## 2. 阶段目标

Phase 6F 必须把 MiroConsumer 从“AI 消费者调研工具”升级为“基于 MiroFish 社会沙盘的消费者传播预演系统”的产品表达层。

本阶段必须激活既有 MiroFish 能力，不得重写底层社会运行架构。

本阶段完成后，用户必须在报告页直接使用以下消费者研究 action 入口：

- 深挖消费者结论。
- 查看传播路径。
- 查看证据强度。
- 追问消费者。
- 对比干预分支差异。

## 3. 产品定义

MiroConsumer 的产品定义固定为：

> 使用消费者社会模拟概念、文案、价格、包装在传播场域中的扩散、误读、质疑、信任修复和转化变化。

产品表达必须遵守以下规则：

- 必须使用“消费者传播预演”“消费者研究总监”“传播路径”“证据强度”“消费者追问入口”“上市前 What-if 实验”。
- 禁止把 consumer 模式描述为“AI persona 打分”。
- 禁止把 consumer 报告描述为旧预测报告。
- 禁止在用户界面暴露 `project_type=default`。
- 禁止删除 legacy shim。

## 4. 阶段范围

### 4.1 必须交付

本阶段必须交付以下能力：

1. ReportAgent consumer 模式提示词重构。
2. ZepTools consumer 语义映射。
3. Consumer research action 后端服务。
4. Consumer research action 规范 API。
5. Consumer event ontology 派生层。
6. 报告页行动入口。
7. 追问消费者 target context 契约。
8. 报告审计工具标签语义替换。
9. 后端与前端契约测试。

### 4.2 禁止纳入

本阶段禁止纳入以下工作：

- 大规模 Society Runtime。
- 200 至 1000+ agent population factory。
- 多渠道传播 runtime。
- OASIS-to-Consumer runtime 桥接。
- 数据库仓库实现。
- 队列执行器。
- 多实例锁。
- 生产 Docker 拆分。
- 权限系统。
- 团队协作系统。
- 计费系统。
- Representative consumer 抽样服务。
- Consumer interview 执行服务。
- Virtual focus group 执行服务。

## 5. 现有能力复用边界

### 5.1 必须复用

以下模块必须复用：

| 既有模块 | Phase 6F 使用方式 |
|---|---|
| `backend/app/services/zep_tools.py` | 作为消费者研究工具底座 |
| `backend/app/services/report_agent.py` | 作为 Research Director Agent 承载体 |
| `backend/app/services/consumer/report_context.py` | 作为 consumer report context 来源 |
| `backend/app/api/consumer.py` | 作为新增规范 API 挂载点 |
| `frontend/src/components/Step4Report.vue` | 作为报告行动入口挂载点 |
| `frontend/src/components/Step5Interaction.vue` | 作为 Phase 6I target context 接收页面 |

### 5.2 禁止重命名

以下底层符号禁止重命名：

- `ZepToolsService`
- `insight_forge`
- `panorama_search`
- `quick_search`
- `interview_agents`
- `ReportAgent`
- `/api/simulation/interview`
- `/api/simulation/interview/batch`
- `/api/simulation/interview/all`
- `/api/simulation/interview/history`

## 6. 后端规格

### 6.1 消费者研究工具语义

必须新增文件：

```text
backend/app/services/consumer/research_tool_semantics.py
```

该文件必须定义唯一的 consumer 工具语义表：

| Raw tool | Consumer label | 中文标签 | 固定用途 |
|---|---|---|---|
| `insight_forge` | `Consumer Insight Deep Dive` | `消费者洞察深挖` | 解释结论形成原因 |
| `panorama_search` | `Propagation Path Explainer` | `传播路径解释器` | 解释扩散、阻断、误读、修复路径 |
| `quick_search` | `Evidence Verifier` | `报告结论证据校验` | 校验结论证据支撑 |
| `interview_agents` | `Virtual Consumer Interview` | `虚拟消费者深访` | Phase 6I 访谈执行能力 |
| `get_all_nodes` | `Consumer Cognition Graph Nodes` | `消费者认知图谱节点` | 展示消费者认知图谱节点 |
| `get_all_edges` | `Consumer Cognition Graph Edges` | `消费者认知图谱关系` | 展示消费者认知图谱关系 |

该文件必须导出：

```python
CONSUMER_TOOL_SEMANTICS
get_consumer_tool_label(tool_name: str, locale: str = "zh") -> str
get_consumer_tool_purpose(tool_name: str) -> str
```

所有未知 tool 名必须原样返回，不得抛出异常。

### 6.2 Research Director Agent

必须修改：

```text
backend/app/services/report_agent.py
```

必须新增 consumer 专用提示词常量：

```python
CONSUMER_PLAN_SYSTEM_PROMPT
CONSUMER_PLAN_USER_PROMPT_TEMPLATE
CONSUMER_SECTION_SYSTEM_PROMPT_TEMPLATE
CONSUMER_SECTION_USER_PROMPT_TEMPLATE
CONSUMER_CHAT_SYSTEM_PROMPT_TEMPLATE
```

Consumer 模式提示词必须满足以下要求：

- Agent 身份必须是 `Consumer Research Director Agent` 或 `消费者研究总监 Agent`。
- 报告必须解释消费者反应原因。
- 报告必须解释卖点传播。
- 报告必须解释质疑扩散。
- 报告必须解释误读扩散。
- 报告必须解释信任衰减。
- 报告必须解释信任修复。
- 报告必须解释证据对态度变化的作用。
- 报告必须提出下一轮上市前 What-if 实验。
- 每个章节必须调用 consumer 语义工具。
- 工具调用 payload 必须继续使用 raw tool 名。

Consumer 模式提示词禁止出现旧预测报告提示词中的中英文关键句。

测试文件必须把既有中英文关键句保存为测试常量，并断言 consumer prompt 不包含这些常量。

Prompt 选择规则固定为：

```python
consumer_mode = self.project_type == "consumer_test" or report_context contains consumer fields
```

`consumer_mode=True` 必须使用 consumer 提示词。`consumer_mode=False` 必须使用既有提示词。

### 6.3 Research Action 服务

必须新增文件：

```text
backend/app/services/application/consumer_research_action_service.py
```

该服务必须定义：

```python
class ConsumerResearchActionType(str, Enum):
    DeepDiveConclusion = "deep_dive_conclusion"
    ExplainPropagationPath = "explain_propagation_path"
    VerifyEvidence = "verify_evidence"
    InterviewConsumers = "interview_consumers"
    CompareBranchDelta = "compare_branch_delta"
```

该服务必须暴露：

```python
ConsumerResearchActionService.run_action(simulation_id: str, payload: dict) -> dict
```

服务必须执行以下步骤：

1. 加载 simulation。
2. 校验 simulation 为 `consumer_test`。
3. 解析 `action_type`。
4. 解析 target。
5. 加载 consumer summary。
6. 加载 report context。
7. 按 action 调用既有能力。
8. 返回统一响应。

Action 与工具映射固定为：

| action_type | 执行能力 |
|---|---|
| `deep_dive_conclusion` | `ZepToolsService.insight_forge` |
| `explain_propagation_path` | `ZepToolsService.panorama_search` |
| `verify_evidence` | report context evidence lookup + `ZepToolsService.quick_search` |
| `interview_consumers` | 返回 Phase 6I target context，不执行访谈 |
| `compare_branch_delta` | `BranchAppService.get_branch_comparison` |

统一响应必须包含：

```json
{
  "action_type": "deep_dive_conclusion",
  "simulation_id": "sim_xxx",
  "target": {
    "kind": "finding",
    "id": "finding_xxx",
    "text": "..."
  },
  "title": "...",
  "summary": "...",
  "details_markdown": "...",
  "evidence": {
    "support_level": "strong",
    "source_count": 0,
    "simulation_quote_count": 0,
    "gatekeeping_status": "supported"
  },
  "tool_trace": {
    "tool_name": "insight_forge",
    "consumer_tool_label": "消费者洞察深挖",
    "query": "..."
  },
  "handoff": {
    "handoff_type": "",
    "target_context": {}
  }
}
```

`support_level` 取值固定为：

```text
strong
medium
weak
insufficient
simulation_only
```

### 6.4 Research Action API

必须修改：

```text
backend/app/api/consumer.py
```

必须新增路由：

```http
POST /api/consumer/simulations/<simulation_id>/research-actions
```

请求体固定为：

```json
{
  "action_type": "deep_dive_conclusion",
  "target": {
    "kind": "finding",
    "id": "finding_xxx",
    "text": "..."
  },
  "context": {
    "report_id": "report_xxx",
    "section_index": 1,
    "branch_id": "branch_xxx",
    "claim": "..."
  }
}
```

HTTP 状态码固定为：

| 状态码 | 条件 |
|---|---|
| 200 | action 执行成功 |
| 400 | 参数缺失、action 不存在、simulation 不是 consumer_test |
| 404 | simulation、report、branch 不存在 |
| 409 | branch 对比请求遇到运行中分支 |
| 500 | 工具执行异常 |

### 6.5 追问消费者 Handoff 契约

Phase 6F 必须只定义追问消费者入口与 target context，不得执行 interview，不得抽样 representative consumer，不得创建 focus group。

`interview_consumers` action 响应固定为：

```json
{
  "action_type": "interview_consumers",
  "simulation_id": "sim_xxx",
  "target": {
    "kind": "finding",
    "id": "finding_xxx",
    "text": "..."
  },
  "title": "追问消费者",
  "summary": "已生成 Phase 6I 访谈上下文",
  "details_markdown": "",
  "evidence": {
    "support_level": "simulation_only",
    "source_count": 0,
    "simulation_quote_count": 0,
    "gatekeeping_status": "handoff"
  },
  "tool_trace": {
    "tool_name": "",
    "consumer_tool_label": "",
    "query": ""
  },
  "handoff": {
    "handoff_type": "phase6i_interview",
    "target_context": {
      "report_id": "report_xxx",
      "section_index": 1,
      "finding_id": "finding_xxx",
      "claim": "...",
      "branch_id": "branch_xxx"
    }
  }
}
```

### 6.6 Consumer Event Ontology

必须新增文件：

```text
backend/app/services/consumer/event_ontology.py
```

必须定义以下事件类型：

```text
VIEW_CLAIM
FIRST_IMPRESSION
ASK_PROOF
AMPLIFY_CLAIM
MISREAD_CLAIM
COMPARE_COMPETITOR
PRICE_RESISTANCE
TRUST_DECAY
TRUST_RECOVERY
SHARE_TO_CHANNEL
BLOCK_PROPAGATION
PURCHASE_INTENT_UP
PURCHASE_INTENT_DOWN
NEGATIVE_CASCADE
```

必须保留既有 `PropagationEvent.event_type`。

必须新增派生字段：

```json
{
  "consumer_event_type": "ASK_PROOF"
}
```

兼容映射固定为：

| 既有 bucket | consumer_event_type |
|---|---|
| `positive_relay` | `AMPLIFY_CLAIM` |
| `skeptical_challenge` | `ASK_PROOF` |
| `misread_amplification` | `MISREAD_CLAIM` |
| `risk_discovery` | `TRUST_DECAY` |
| `clarification_recovery` | `TRUST_RECOVERY` |

## 7. 前端规格

### 7.1 Consumer API

必须修改：

```text
frontend/src/api/consumerFactory.js
frontend/src/api/consumer.js
```

必须新增函数：

```javascript
runConsumerResearchAction(simulationId, data)
```

所有新增函数必须调用 `/api/consumer/*`。

### 7.2 Report Action Bar

必须新增：

```text
frontend/src/components/consumer/ConsumerResearchActionBar.vue
```

必须展示按钮：

- 深挖结论
- 查看传播路径
- 查看证据
- 追问消费者
- 比较分支差异

按钮必须传出固定 action payload。

### 7.3 Insight Drawer

必须新增：

```text
frontend/src/components/consumer/ConsumerInsightDrawer.vue
```

必须展示：

- 标题
- 摘要
- markdown 详情
- 证据等级
- 来源数量
- 模拟 quote 数量
- gatekeeping 状态
- 工具追踪

### 7.4 Interview Handoff 前端契约

Phase 6F 必须在 `ConsumerInsightDrawer.vue` 中识别 `handoff.handoff_type="phase6i_interview"`。

识别后必须执行以下行为：

- 显示“进入消费者追问工作台”按钮。
- 点击后跳转到 Step5。
- 跳转时必须保存 `handoff.target_context`。
- 不得渲染 interview 结果。
- 不得渲染 focus group 结果。

### 7.5 挂载点

必须修改：

```text
frontend/src/components/Step4Report.vue
frontend/src/components/Step5Interaction.vue
frontend/src/utils/consumerMode.js
locales/en.json
locales/zh.json
```

挂载规则固定为：

- `Step4Report.vue` 挂载 action bar 和 insight drawer。
- `Step5Interaction.vue` 接收并保存 Phase 6I target context。
- consumer mode 工具日志必须显示 consumer label。
- non-consumer mode 工具日志保持原显示。

## 8. 测试规格

### 8.1 后端测试

必须新增：

```text
backend/tests/consumer/test_event_ontology.py
backend/tests/services/application/test_consumer_research_action_service.py
backend/tests/api/test_consumer_research_actions.py
backend/tests/consumer/test_report_agent_consumer_prompts.py
```

测试必须覆盖：

- event bucket 到 consumer event type 的映射。
- research action 服务 action 映射。
- evidence action 查找顺序。
- interview handoff response shape。
- API 成功响应。
- API 错误响应。
- consumer prompt 禁止词。
- default prompt 不回归。

### 8.2 前端测试

必须新增：

```text
frontend/tests/consumerResearchActions.test.js
```

必须扩展：

```text
frontend/tests/consumerApi.behavior.test.js
```

测试必须覆盖：

- consumer API 路径。
- action bar payload。
- drawer evidence 渲染。
- interview handoff 跳转 payload。
- consumer tool label 渲染。

## 9. 验收命令

后端验收必须运行：

```bash
cd backend
python -m pytest tests/consumer/test_event_ontology.py -q
python -m pytest tests/services/application/test_consumer_research_action_service.py -q
python -m pytest tests/api/test_consumer_research_actions.py -q
python -m pytest tests/consumer/test_report_agent_consumer_prompts.py -q
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

## 10. 退出条件

Phase 6F 退出必须同时满足：

1. Consumer report 不再使用旧预测语义。
2. Default report 保持既有语义。
3. Consumer report 展示五个行动入口。
4. Research action API 返回统一响应。
5. `interview_consumers` action 返回 Phase 6I handoff。
6. Consumer event ontology 进入 summary context。
7. Report audit 显示 consumer 工具标签。
8. 所有新增测试通过。
9. 全量后端测试通过。
10. 前端 node 测试通过。
11. 前端 build 通过。
12. `git diff --check` 无输出。
