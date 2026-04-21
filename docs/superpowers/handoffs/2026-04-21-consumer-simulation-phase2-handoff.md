# Consumer Simulation Phase 2 交接文档

## 1. 交接目标

本文档用于把当前 `consumer_test` Phase 2 的实现范围、代码位置、验证结果、已知限制和下一步建议说明清楚，确保下一位同事可以直接从当前 worktree 状态接手，而不需要重新梳理 Phase 1 之后的增量。

## 2. 当前范围

当前分支已经在 Phase 1 基线上完成了 Phase 2 的 realism 升级，重点不是扩更多测试品类，而是让这套消费者传播测试更接近真实市场：

- `research_mode / auto_enrich`
- research findings 进入 graph 与 simulation config
- persona-aware knowledge visibility
- typed propagation events
- causal summary / causal report context
- Step 2-5 前端承接

当前仍然不包含：

- 包装 / A-B / 价格测试
- 真实全网 research provider
- DingTalk 群聊工作流
- Tiered RAG
- 研究员实时干预

## 3. 当前代码位置

- 仓库根：
  - `D:\project\MiroFish`
- 实现 worktree：
  - `D:\project\MiroFish\.worktrees\consumer-simulation-phase1`
- 分支：
  - `codex/consumer-simulation-phase1`

## 4. Phase 2 代码落点

### 4.1 后端

Phase 2 新增或重点扩展的模块：

- `backend/app/services/consumer/research_ingest.py`
  - `build_research_findings()`
  - `resolve_research_findings()`
  - `default_auto_research_provider()`
- `backend/app/services/consumer/access_policy.py`
  - `resolve_visible_findings()`
  - `build_knowledge_view()`
- `backend/app/services/consumer/event_engine.py`
  - `classify_propagation_event()`
  - `build_propagation_event()`
  - `derive_trigger_from_findings()`
  - `derive_speech_act_from_bucket()`
- `backend/app/services/consumer/models.py`
  - `ResearchFinding`
  - `PropagationEvent`
  - `research_mode` 字段
- `backend/app/services/consumer/scoring.py`
  - `ConsumerPhase2Summary`
  - `build_consumer_summary()`
- `backend/app/services/consumer/report_context.py`
  - `build_consumer_report_context()`

同步扩展的主链路文件：

- `backend/app/api/graph.py`
  - graph build 走 `resolve_research_findings(...)`
- `backend/app/services/simulation_manager.py`
  - prepare 写入 `consumer_config.json` 中的 research fields
- `backend/app/services/simulation_runner.py`
  - runtime 加载 `research_findings`
  - snapshot 挂 `propagation_events`
- `backend/app/api/simulation.py`
  - `/consumer-summary` 返回 Phase 2 字段
- `backend/app/services/report_agent.py`
  - 报告上下文与渲染包含 event / causal fields

### 4.2 前端

Phase 2 对前端的主要改动位置：

- `frontend/src/utils/consumerBrief.js`
  - 构造 `research_mode`
  - 规范化 `optional_background_materials`
- `frontend/src/utils/consumerMode.js`
  - `getConsumerEventLabel()`
  - Step 5 因果追问 prompt
- `frontend/src/store/pendingUpload.js`
  - 持久化 `researchMode`
- `frontend/src/views/Home.vue`
  - research mode 选择
  - 背景材料输入
- `frontend/src/components/Step2EnvSetup.vue`
  - research findings / visibility 展示
- `frontend/src/components/Step3Simulation.vue`
  - event counts / causal VOC 展示
- `frontend/src/components/Step4Report.vue`
  - risk findings / clarification opportunities / causal chains
- `frontend/src/components/Step5Interaction.vue`
  - 因果问题导向的 quick prompts
- `locales/en.json`
- `locales/zh.json`

## 5. 当前行为基线

### 5.1 Research 模式

- `manual_only`
  - 仅从 `optional_background_materials` 生成 `ResearchFinding`
- `auto_enrich`
  - 通过 `default_auto_research_provider()` 基于 brief 内容做确定性合成
  - 当前是 repo-owned 合成逻辑，不调用外部真实 research 服务

### 5.2 可见性规则

- Round 0：
  - 仅 `Initial`
- Round 1+：
  - `Propagation_Only` 对所有消费者可见
  - `Restricted` 仅对高搜索 + 高认知画像可见

### 5.3 事件与报告

- snapshot 里包含 `propagation_events`
- consumer summary 返回：
  - `event_counts`
  - `top_risk_findings`
  - `top_clarification_opportunities`
  - `causal_voc_quotes`
  - `causal_chains`
  - `event_led_reversals`
  - `persona_group_signals`

## 6. 已验证结果

### 6.1 后端测试

命令：

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend
.\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/integration
```

结果：

- `70 passed`

### 6.2 前端测试

命令：

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1
node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js
```

结果：

- `18 passed`

### 6.3 前端构建

命令：

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend
npm run build
```

结果：

- 构建成功

### 6.4 关键验收结论

- `auto_enrich` graph build 在无手工背景时也能产出 findings
- prepare 会把 findings 持久化到 `consumer_config.json`
- runtime 会把 findings 传入 orchestrator
- Round 0 仍然隐藏深层 findings
- 后续轮次仅高搜索 / 高认知画像能看到 `Restricted`
- propagation events 已成为 typed first-class evidence
- report context 已保留 `trigger_finding_ids` + `event_ids`
- Step 2-5 已能展示 Phase 2 的 research / event / causal 信息
- 默认模式兼容测试仍是绿的

## 7. 当前已知限制

- `auto_enrich` 当前是 deterministic repo-owned synthesis，不是真实外部 research provider
- Kimi For Coding 当前 prepare 耗时较长，`4` 个 profile 约 `21` 分钟
- `response_format=json_object` 兼容性仍依赖 proxy 缓解
- 前端仍有两个非阻断 warning：
  - `pendingUpload.js` 动静态导入混用
  - chunk size warning

## 8. 当前工作区状态说明

- 当前 worktree 已包含 Phase 2 代码与文档更新
- 本轮文档补齐由当前会话直接完成
- 当前分支里同时存在尚未统一提交的实现改动与文档改动；在正式合并前，建议先统一做一次 review，再按“代码实现 + 文档同步”一起提交

## 9. 下一步建议

1. 将 `default_auto_research_provider()` 替换为真实外部 research / RAG provider。
2. 增加真实业务素材下的长轮次和大样本量压测。
3. 评估 profile 生成并行化或更快模型，降低 prepare 耗时。
4. 在 Phase 3 再考虑：
   - Tiered RAG
   - 更完整的社会化演化
   - 研究员实时干预
   - DingTalk / 外部焦点小组接口

## 10. 启动与验证参考

### 10.1 后端

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend
.\.venv\Scripts\python.exe run.py
```

### 10.2 前端

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

### 10.3 回归命令

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend
.\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/integration

Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1
node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js

Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend
npm run build
```
