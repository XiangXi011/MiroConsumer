# MiroConsumer Phase 6H 多渠道消费者传播执行规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-28 |
| 阶段 | Phase 6H |
| 阶段名称 | 多渠道消费者传播 |
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

- Phase 6H 必须依赖 Phase 6F 的 consumer event ontology。
- Phase 6H 必须依赖 Phase 6G 的 society runtime、population、unified role enum。
- Phase 6I 必须依赖 Phase 6H 的 channel context。
- Phase 7 必须依赖 Phase 6H 的 channel schema 稳定版本。

## 2. 阶段目标

Phase 6H 必须把 MiroFish 原生双平台运行思路升级为消费者渠道传播模型。

本阶段必须让同一 consumer brief 在多个消费者渠道中传播，并输出渠道适配、渠道误读、渠道证据需求、渠道价格阻力和渠道转化阻力指标。

## 3. 阶段边界

### 3.1 必须交付

1. Consumer channel 枚举。
2. Channel policy。
3. Channel runtime。
4. Channel event mapper。
5. Channel metrics aggregator。
6. Cross-channel migration 规则。
7. Channel fit scoring。
8. Channel report adapter。
9. Channel heatmap 前端组件。
10. Propagation timeline 前端组件。
11. Propagation path graph 前端组件。
12. 渠道测试矩阵。

### 3.2 禁止纳入

本阶段禁止纳入以下工作：

- 新增大社会 population 层级。
- 虚拟焦点小组。
- 数据库仓库。
- 队列执行器。
- 多实例锁。
- 生产 Docker。
- 真实平台抓取。
- 真实平台发布。
- 平台账号登录。

## 4. 渠道枚举

必须新增或扩展：

```text
backend/app/services/consumer/society/channel_models.py
```

渠道 ID 固定为：

```text
xiaohongshu
douyin
wechat_group
ecommerce_review
zhihu_qa
offline_word_of_mouth
livestream
sales_assistant
```

每个事件必须包含：

```json
{
  "channel_id": "xiaohongshu",
  "channel_label": "小红书"
}
```

禁止在 consumer-facing API 中继续使用 `twitter` 和 `reddit` 作为渠道标签。

## 5. 渠道语义

渠道语义固定如下：

| channel_id | 中文名 | 传播特征 | 高风险点 |
|---|---|---|---|
| `xiaohongshu` | 小红书 | 视觉、场景、生活方式、成分党质疑 | 包装误读、成分证据不足 |
| `douyin` | 抖音 | 强钩子、快速放大、短时误读 | 卖点过度简化、负面级联 |
| `wechat_group` | 微信群 | 熟人信任、经验提醒、群体阻断 | 安全顾虑、家庭经验反驳 |
| `ecommerce_review` | 电商评论区 | 价格、功效、真实体验、负面反馈 | 价格比较、体验不一致 |
| `zhihu_qa` | 知乎/问答社区 | 理性分析、证据要求、专家观点 | 证据链不足、概念夸大 |
| `offline_word_of_mouth` | 线下口碑 | 熟人传播、场景复述、低速扩散 | 信息缺失、口碑阻断 |
| `livestream` | 直播间 | 主播信任、限时优惠、冲动购买 | 价格锚定、承诺过强 |
| `sales_assistant` | 导购场景 | 即时解释、试用反馈、异议处理 | 话术不一致、证据缺口 |

## 6. Channel Policy

必须新增：

```text
backend/app/services/consumer/society/channel_policy.py
```

每个 channel policy 必须定义：

```python
@dataclass
class ConsumerChannelPolicy:
    channel_id: str
    amplification_factor: float
    misread_factor: float
    evidence_demand_factor: float
    price_sensitivity_factor: float
    trust_repair_factor: float
    purchase_intent_factor: float
    cross_channel_spread_factor: float
    allowed_event_types: list[str]
```

数值范围固定为 `0.0` 至 `1.0`。

`allowed_event_types` 必须只使用 Phase 6F consumer event ontology。

Policy 校验失败必须抛出 `ValueError`。

## 7. Channel Runtime

必须新增：

```text
backend/app/services/consumer/society/channel_runtime.py
```

职责固定为：

1. 接收 society population。
2. 接收 channel config。
3. 按渠道分配 agent。
4. 执行渠道内传播。
5. 执行跨渠道迁移。
6. 生成 channel event。
7. 更新 agent channel state。
8. 输出 channel metrics。

Agent 分配规则固定为：

- 每个 core persona 至少进入一个渠道。
- `standard` 模式至少启用 3 个渠道。
- `large_society` 模式至少启用 6 个渠道。
- 每个启用渠道至少包含 5% population。

## 8. Channel Event

Channel event 必须包含：

```json
{
  "event_id": "event_xxx",
  "consumer_event_type": "MISREAD_CLAIM",
  "channel_id": "douyin",
  "round_index": 4,
  "actor_id": "agent_xxx",
  "target_ids": [],
  "claim_id": "claim_xxx",
  "finding_ids": [],
  "quote": "...",
  "strength": 0.72,
  "cross_channel": false,
  "source_channel_id": "",
  "target_channel_id": ""
}
```

`strength` 范围固定为 `0.0` 至 `1.0`。

## 9. Cross-Channel Migration

跨渠道迁移规则固定为：

| source | target | 条件 |
|---|---|---|
| `douyin` | `wechat_group` | 负面级联强度大于 `0.6` |
| `xiaohongshu` | `ecommerce_review` | 购买意愿提升大于 `0.4` |
| `zhihu_qa` | `wechat_group` | 证据需求率大于 `0.5` |
| `livestream` | `ecommerce_review` | 价格阻力大于 `0.5` |
| `offline_word_of_mouth` | `wechat_group` | 信任衰减大于 `0.4` |
| `sales_assistant` | `ecommerce_review` | 试用异议强度大于 `0.4` |

迁移事件必须标记：

```json
{
  "cross_channel": true,
  "source_channel_id": "douyin",
  "target_channel_id": "wechat_group"
}
```

## 10. Channel Metrics

必须新增：

```text
backend/app/services/consumer/society/channel_metrics.py
```

必须输出：

```json
{
  "channels": {
    "xiaohongshu": {
      "fit_score": 0.0,
      "resonance": 0.0,
      "misread_risk": 0.0,
      "evidence_demand": 0.0,
      "price_resistance": 0.0,
      "trust_objection": 0.0,
      "purchase_intent_delta": 0.0,
      "negative_cascade_probability": 0.0
    }
  },
  "cross_channel_spread": 0.0,
  "best_launch_channel": "xiaohongshu",
  "highest_misread_channel": "douyin",
  "highest_evidence_demand_channel": "zhihu_qa",
  "highest_price_resistance_channel": "ecommerce_review"
}
```

所有分数字段范围固定为 `0.0` 至 `1.0`。

## 11. Channel Fit Scoring

必须新增配置文件：

```text
backend/app/services/consumer/society/channel_fit_weights.json
```

配置内容固定为：

```json
{
  "resonance": 0.30,
  "purchase_intent_delta": 0.25,
  "trust_repair_factor": 0.15,
  "misread_risk": -0.15,
  "price_resistance": -0.10,
  "evidence_demand": -0.05
}
```

配置校验规则固定为：

- 所有 key 必须存在。
- 所有 value 必须为数字。
- 正向权重总和必须等于 `0.70`。
- 负向权重绝对值总和必须等于 `0.30`。
- 校验失败必须抛出 `ValueError`。

`fit_score` 公式固定为配置驱动：

```text
fit_score =
  resonance * weights.resonance
  + purchase_intent_delta * weights.purchase_intent_delta
  + trust_repair_factor * weights.trust_repair_factor
  + misread_risk * weights.misread_risk
  + price_resistance * weights.price_resistance
  + evidence_demand * weights.evidence_demand
```

计算后必须 clamp 到 `0.0` 至 `1.0`。

LLM 禁止直接生成 `fit_score`。

## 12. Channel Report Adapter

必须新增：

```text
backend/app/services/consumer/society/channel_report_adapter.py
```

Report context 必须新增：

```json
{
  "channel_metrics": {},
  "channel_fit_scores": {},
  "channel_misread_summary": {},
  "channel_evidence_summary": {},
  "channel_price_summary": {},
  "cross_channel_paths": []
}
```

ReportAgent consumer prompt 必须要求输出：

- 首发渠道。
- 误读高风险渠道。
- 证据补强渠道。
- 价格阻力高渠道。
- KOL 种草渠道。
- 专家背书渠道。

## 13. API 集成

Simulation start payload 必须新增：

```json
{
  "enabled_channels": [
    "xiaohongshu",
    "douyin",
    "wechat_group",
    "ecommerce_review"
  ],
  "channel_seed": 12345
}
```

规则固定为：

- 缺少 `enabled_channels` 时使用 `["xiaohongshu", "wechat_group", "ecommerce_review"]`。
- 非法 channel id 返回 400。
- `quick` mode 最多启用 3 个渠道。
- `standard` mode 最多启用 5 个渠道。
- `large_society` mode 最多启用 8 个渠道。

必须新增查询 API：

```http
GET /api/consumer/simulations/<simulation_id>/channel-summary
GET /api/consumer/simulations/<simulation_id>/channel-events
GET /api/consumer/simulations/<simulation_id>/propagation-paths
```

## 14. 前端组件

### 14.1 Channel Heatmap

必须新增：

```text
frontend/src/components/consumer/ChannelHeatmap.vue
```

必须展示矩阵：

- channel × claim
- channel × persona segment
- channel × risk type
- channel × purchase intent

### 14.2 Propagation Timeline

必须新增：

```text
frontend/src/components/consumer/PropagationTimeline.vue
```

时间线必须展示：

- round 0 初见反应
- round 1 至 round 3 卖点放大
- round 4 至 round 6 质疑出现
- round 7 至 round 9 误读扩散
- round 10 证据修复

当运行 round 数小于 10 时，时间线必须按实际 round 截断。

### 14.3 Propagation Path Graph

必须新增：

```text
frontend/src/components/consumer/PropagationPathGraph.vue
```

必须展示：

- 首个误读消费者。
- 传播目标。
- 跨圈层次数。
- 跨渠道次数。
- 最终受影响人群。
- 阻断节点。
- 修复节点。

### 14.4 Channel Fit Panel

必须新增：

```text
frontend/src/components/consumer/ChannelFitPanel.vue
```

必须展示：

- best_launch_channel
- highest_misread_channel
- highest_evidence_demand_channel
- highest_price_resistance_channel
- 每个渠道 fit_score
- 每个渠道主要风险

## 15. 挂载点

必须修改：

```text
frontend/src/components/Step3Simulation.vue
frontend/src/components/Step4Report.vue
frontend/src/components/Step5Interaction.vue
frontend/src/api/consumerFactory.js
frontend/src/api/consumer.js
frontend/src/utils/consumerMode.js
locales/en.json
locales/zh.json
```

挂载规则固定为：

- Step3 显示 channel runtime 状态。
- Step4 显示 ChannelFitPanel、ChannelHeatmap、PropagationTimeline。
- Step5 显示 PropagationPathGraph。

## 16. 测试规格

必须新增后端测试：

```text
backend/tests/consumer/society/test_channel_policy.py
backend/tests/consumer/society/test_channel_runtime.py
backend/tests/consumer/society/test_channel_metrics.py
backend/tests/consumer/society/test_channel_report_adapter.py
backend/tests/api/test_consumer_channel_routes.py
```

必须新增前端测试：

```text
frontend/tests/channelHeatmap.test.js
frontend/tests/propagationTimeline.test.js
frontend/tests/propagationPathGraph.test.js
frontend/tests/channelFitPanel.test.js
```

测试必须覆盖：

- 非法 channel id 返回 400。
- policy 数值范围校验。
- agent 渠道分配达标。
- cross-channel migration 条件触发。
- fit_score 使用配置权重。
- channel fit weights 校验失败抛出 `ValueError`。
- channel report context 字段齐全。
- API 返回 channel summary。
- 前端组件渲染固定指标。

## 17. 验收命令

后端验收必须运行：

```bash
cd backend
python -m pytest tests/consumer/society/test_channel_policy.py tests/consumer/society/test_channel_runtime.py tests/consumer/society/test_channel_metrics.py tests/consumer/society/test_channel_report_adapter.py -q
python -m pytest tests/api/test_consumer_channel_routes.py -q
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

## 18. 退出条件

Phase 6H 退出必须同时满足：

1. 八个 consumer channel 全部定义。
2. Channel policy 校验存在。
3. Channel runtime 生成 channel event。
4. Cross-channel migration 生成迁移事件。
5. Channel metrics 输出固定字段。
6. Channel fit score 使用配置权重。
7. Report context 包含 channel 字段。
8. API 返回 channel summary、channel events、propagation paths。
9. 前端展示渠道热力图、传播时间线、传播路径图、渠道适配面板。
10. 新增后端测试通过。
11. 新增前端测试通过。
12. 全量后端测试通过。
13. 前端 node 测试通过。
14. 前端 build 通过。
15. `git diff --check` 无输出。
