# MiroConsumer Phase 6J 校准与可信度验收执行规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 阶段 | Phase 6J |
| 阶段名称 | 校准与可信度验收 |
| 目标工作区 | `D:\project\MiroFish\.worktrees\phase5a-identity` |
| 目标分支 | `codex/phase5-closure` |
| 文档状态 | 审核基线 |

## 2. 阶段依赖图

```text
Phase 6F 消费者语义激活
  -> Phase 6G 大规模消费者社会桥接
  -> Phase 6H 多渠道消费者传播
  -> Phase 6I 虚拟焦点小组
  -> Phase 6J 校准与可信度验收
  -> Phase 7A 持久化基础
```

依赖规则固定为：

- Phase 6J 必须依赖 Phase 6F consumer research action response schema。
- Phase 6J 必须依赖 Phase 6F consumer event ontology。
- Phase 6J 必须依赖 Phase 6G unified role enum、society agent state、society metrics。
- Phase 6J 必须依赖 Phase 6H channel context、channel metrics、propagation path。
- Phase 6J 必须依赖 Phase 6I interview history schema、focus group turns schema、representative agent schema。
- Phase 7A 必须依赖 Phase 6J readiness gate 通过。

## 3. 阶段目标

Phase 6J 必须证明 Phase 6F 至 Phase 6I 形成的消费者传播预演系统具备稳定链路、证据约束、可审计推理和业务可解释性。

本阶段不是生产化阶段。本阶段完成前，Phase 7 禁止启动。

## 4. 阶段边界

### 4.1 必须交付

1. End-to-end golden flow。
2. Dynamic focus group what-if experiments。
3. Structured evidence digest for layered reasoning。
4. Evidence gatekeeping hard rules。
5. Explainability panel acceptance。
6. Calibration report。
7. Same-seed deterministic mode regression。
8. Fake LLM deterministic mode regression。
9. Branch isolation regression。
10. Report audit field coverage。

### 4.2 禁止纳入

本阶段禁止纳入以下工作：

- 数据库仓库。
- 队列执行器。
- 多实例锁。
- 生产 Docker。
- 新增消费者模拟内核。
- 新增消费者渠道规则。
- 修改 Phase 6F 至 Phase 6I 的稳定 schema。
- 修改 consumer API response schema。

## 5. P0 硬门禁

### 5.1 End-to-End Golden Flow

必须新增：

```text
backend/tests/e2e/test_consumer_concept_test_golden_flow.py
```

测试必须证明以下链路完整：

```text
BusinessBrief
  -> consumer simulation create
  -> prepare consumer mode
  -> quick mode run
  -> standard mode run
  -> consumer summary
  -> report
  -> focus group
  -> report finding follow-up
  -> evidence-backed recommendations
```

结构断言固定为：

- simulation 能 create。
- prepare 能识别 consumer mode。
- start 能在 quick mode 应用 `society_config`。
- start 能在 standard mode 应用 `society_config`。
- summary 至少包含 `event_counts`、`causal_voc_quotes`、`report_confidence`。
- focus group 至少包含 4 turns、consensus、disagreements、evidence_map。
- 每个 finding 必须具备 evidence trace，或者显式标记 `weak_support` / `insufficient_support`。
- evidence-backed recommendations 必须包含 `source_ids`，或者显式标记 `UNKNOWN`。

### 5.2 Dynamic Focus Group What-if Experiments

必须新增：

```text
backend/tests/consumer/interview/test_dynamic_what_if_experiments.py
```

`next_what_if_experiments` 必须从以下输入生成：

- target finding。
- disagreement。
- risk point。
- price task_type。
- copy task_type。
- concept task_type。
- evidence gap。

固定三条模板输出禁止出现：

```text
What if pricing were 20% lower?
What if clinical evidence were front and center?
What if packaging claims were simplified?
```

### 5.3 Structured Evidence Digest for Layered Reasoning

必须新增：

```text
backend/tests/consumer/society/test_reasoning_evidence_digest.py
```

`LayeredSocietyReasoningEngine` 输入必须包含 `evidence_digest`。

`evidence_digest` entry schema 固定为：

```json
{
  "finding_id": "string",
  "claim": "string",
  "supporting_evidence": ["string"],
  "contradicting_evidence": ["string"],
  "source_quality": "lane_a",
  "confidence": "high"
}
```

`source_quality` 取值固定为：

```text
lane_a
lane_b
simulation
unknown
```

`confidence` 取值固定为：

```text
high
medium
low
unknown
```

只传 `research_findings_count` 禁止通过验收。

### 5.4 Evidence Gatekeeping Hard Rules

必须新增：

```text
backend/tests/consumer/reporting/test_evidence_gatekeeping_hard_rules.py
```

硬门禁固定为：

```text
No Evidence = UNKNOWN = FAIL
```

规则固定为：

- 无 evidence 的 finding 禁止进入 Top Finding。
- `weak_support` 只能进入低置信风险提示。
- `insufficient_support` 必须进入需要补充资料。
- LLM 禁止把 weak evidence 写成 strong conclusion。
- high-stakes finding 必须具备 source trace。
- report section 必须保留 evidence gatekeeping result。

### 5.5 Explainability Panel Acceptance

必须新增：

```text
frontend/tests/consumerExplainabilityPanel.test.js
```

前端必须透明展示：

- 结论对应的 source 与 evidence。
- 结论来自真实材料、模拟推断或混合来源。
- `llm_invoked`。
- `reasoning_backend`。
- `reasoning_error`。
- template fallback 标记。
- confidence。
- evidence validation result。
- evidence gatekeeping result。

## 6. P1 验收增强

### 6.1 Calibration Report

必须新增 Phase 6J calibration report 输出。

报告必须包含：

- golden flow 结果。
- evidence gatekeeping 结果。
- reasoning backend 覆盖率。
- template fallback 覆盖率。
- weak_support finding 数量。
- insufficient_support finding 数量。
- UNKNOWN recommendation 数量。
- Phase 7 entry decision。

`Phase 7 entry decision` 取值固定为：

```text
PASS
BLOCKED
```

### 6.2 Deterministic Regression

必须覆盖：

- same seed deterministic mode 输出稳定。
- fake LLM deterministic mode 输出稳定。
- branch run 禁止污染 base run。
- report audit field coverage 完整。

## 7. 后端测试规格

必须新增或扩展：

```text
backend/tests/e2e/test_consumer_concept_test_golden_flow.py
backend/tests/consumer/interview/test_dynamic_what_if_experiments.py
backend/tests/consumer/society/test_reasoning_evidence_digest.py
backend/tests/consumer/reporting/test_evidence_gatekeeping_hard_rules.py
backend/tests/consumer/reporting/test_phase6j_calibration_report.py
backend/tests/consumer/society/test_simulation_consistency.py
```

## 8. 前端测试规格

必须新增或扩展：

```text
frontend/tests/consumerExplainabilityPanel.test.js
```

测试必须验证：

- evidence/source 可见。
- simulation vs material 来源标记可见。
- LLM invocation metadata 可见。
- fallback metadata 可见。
- confidence 可见。
- gatekeeping result 可见。

## 9. 验收命令

后端验收必须运行：

```bash
cd backend
python -m pytest tests/e2e/test_consumer_concept_test_golden_flow.py -q
python -m pytest tests/consumer/interview/test_dynamic_what_if_experiments.py -q
python -m pytest tests/consumer/society/test_reasoning_evidence_digest.py -q
python -m pytest tests/consumer/reporting/test_evidence_gatekeeping_hard_rules.py -q
python -m pytest tests/consumer/reporting/test_phase6j_calibration_report.py -q
python -m pytest tests/consumer/society/test_simulation_consistency.py -q
python -m pytest tests/consumer/ -q
```

前端验收必须运行：

```bash
cd frontend
node --test tests/consumerExplainabilityPanel.test.js
node --test tests/*.test.js tests/composables/*.test.js
npm run build
```

仓库验收必须运行：

```bash
git diff --check
```

## 10. 退出条件

Phase 6J 退出必须同时满足：

1. End-to-end golden flow 测试通过。
2. quick mode 与 standard mode 均应用 `society_config`。
3. consumer summary 包含 `event_counts`、`causal_voc_quotes`、`report_confidence`。
4. focus group 包含 4 turns、consensus、disagreements、evidence_map。
5. report finding follow-up 输出 evidence-backed recommendations。
6. `next_what_if_experiments` 由 target finding、disagreement、risk point、task_type 动态生成。
7. 固定三条 what-if 模板禁止出现在输出中。
8. `LayeredSocietyReasoningEngine` 接收 structured `evidence_digest`。
9. 只传 `research_findings_count` 的 reasoning path 被测试阻断。
10. No Evidence = UNKNOWN = FAIL 门禁生效。
11. 无 evidence finding 禁止进入 Top Finding。
12. `weak_support` 只能进入低置信风险提示。
13. `insufficient_support` 必须进入需要补充资料。
14. LLM 禁止把 weak evidence 写成 strong conclusion。
15. 前端 explainability panel 展示 evidence/source、source type、LLM metadata、fallback、confidence、gatekeeping result。
16. Calibration report 输出 `PASS` 或 `BLOCKED`。
17. same-seed deterministic mode 测试通过。
18. fake LLM deterministic mode 测试通过。
19. branch 不污染 base 测试通过。
20. report audit field coverage 测试通过。
21. 后端 Phase 6J 验收命令通过。
22. 前端 Phase 6J 验收命令通过。
23. `git diff --check` 无输出。
