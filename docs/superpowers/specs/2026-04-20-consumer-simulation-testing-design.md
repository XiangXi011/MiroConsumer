# MiroFish 消费者传播测试整合设计

## 1. 设计目标

本设计的目标是在不破坏原版 MiroFish 主链路的前提下，加入一个 `project_type=consumer_test` 分支，使系统能够围绕概念测试与文案测试执行消费者传播仿真，并输出消费者测试专用报告。

设计原则：

- MiroFish 为主骨架
- 消费者项目提供领域契约与研究逻辑
- 默认模式完全保持原版行为
- 只有显式传入 `consumer_test` 才触发新逻辑

## 2. Phase 1 设计边界

### 2.1 纳入范围

- `concept_test`
- `copy_feedback`
- BusinessBrief 标准化
- persona pack 映射
- consumer graph
- Round 0 / Round 1-N 传播仿真
- VOC 证据抽取
- 消费者传播测试报告
- 报告后追问交互

### 2.2 不纳入范围

- 包装 / A-B / 价格测试
- 自动全网抓取
- DingTalk 群聊工作流
- 数据库、认证、Celery 等外围系统迁移

## 3. 整体架构

系统继续沿用 MiroFish 现有主链路：

`/api/graph -> /api/simulation -> /api/report`

消费者测试能力以内部分支形式接入，不单独拆出一套平行 API。

## 4. 核心模块设计

### 4.1 Consumer Brief Adapter

职责：

- 将输入标准化为 `ConsumerBusinessBrief`
- 统一处理概念、文案、claims、目标人群、场景、研究目标、背景资料
- 输出可用于图谱、仿真与报告的统一上下文

状态：

- 已完成

### 4.2 Consumer Persona Pack

职责：

- 加载 repo-owned persona pack
- 映射传播相关特征：
  - `search_propensity`
  - `cognition_level`
  - `herd_tendency`
  - `influence_weight`
  - `attention_drivers`
  - `risk_sensitivities`

状态：

- 已完成

### 4.3 Consumer Graph Builder

职责：

- 基于 `BusinessBrief + 可选背景材料 + persona pack` 构建 consumer graph
- 生成消费者测试专用节点与关系
- 为节点附加可见性层级

可见性层级：

- `Initial`
  - Round 0 可见
  - 仅承载 BusinessBrief 中直接提供的信息
- `Propagation_Only`
  - 默认仅在 Round 1-N 开放
- `Restricted`
  - 仅对高搜索倾向 / 高认知角色开放

状态：

- 已完成

### 4.4 Consumer Simulation Orchestrator

职责：

- 执行 Round 0 初见反应
- 执行 Round 1-N 传播演化
- 每轮 Prompt 置顶 `Pinned BusinessBrief Summary`
- 按画像和可见性层级控制深层 graph 访问
- 持久化 consumer round 事件

关键约束：

- Round 0 禁止普通 Agent 提前看到深层风险点
- Round 1-N 才允许部分角色检索 `Propagation_Only / Restricted` 信息
- 每轮必须回到当前被测产品本身，避免讨论发散

状态：

- 已完成

### 4.5 Consumer Scoring & Evidence Layer

职责：

- 统计初始与传播后接受度
- 计算态度转向率
- 提取共鸣点、风险点、误读点
- 强制保留代表性 VOC 原声

输出包括：

- `ConsumerSimulationSummary`
- `ConsumerEvidenceBundle`

状态：

- 已完成

### 4.6 Consumer Report Context

职责：

- 将 summary / evidence 组装成报告上下文
- 将 VOC 与关键结论一起喂给报告代理
- 驱动消费者传播测试专用章节结构

状态：

- 已完成

## 5. API 设计

### 5.1 `/api/graph`

新增能力：

- `POST /api/graph/ontology/generate`
  - 支持 `project_type`
  - 支持 `consumer_brief`
- `POST /api/graph/build`
  - 在 `consumer_test` 模式下走 consumer graph path

兼容性要求：

- 不传 `project_type` 时，仍走原版默认逻辑

状态：

- 已完成

### 5.2 `/api/simulation`

新增能力：

- `POST /api/simulation/create`
  - 将 `project_type` 复制进 simulation state
- `POST /api/simulation/prepare`
  - 生成 persona pack、consumer config 与 pinned brief
- `GET /api/simulation/<id>/consumer-summary`
  - 返回 summary / VOC / evidence
- `POST /api/simulation/start`
  - 走消费者仿真分支

兼容性要求：

- `project_type` 默认值为 `default`
- 默认模式不触发任何消费者域逻辑

状态：

- 已完成

### 5.3 `/api/report`

新增能力：

- `POST /api/report/generate`
  - 在 `consumer_test` 模式下生成消费者传播测试报告

状态：

- 已完成

## 6. 前端接入

### 6.1 首页输入

首页继续保留单一入口，但在 `consumer_test` 模式下新增：

- 测试类型
- 概念素材
- 文案素材
- claims
- 目标人群
- 使用场景
- 研究目标

### 6.2 Step 2-5 适配

- Step 2：
  - 展示消费者模式标识
  - 展示 persona pack 与 pinned brief
- Step 3：
  - 展示 Round 0 / Round 1-N 语义
  - 展示 consumer summary 与 VOC
- Step 4：
  - 展示消费者传播报告标签、指标与 VOC
- Step 5：
  - 展示推荐追问与 VOC highlights

### 6.3 i18n

消费者模式新增文案必须进入中英 locale，不允许绕过 `$t(...)` 写死英文。

状态：

- 已完成

## 7. 当前实现进度（2026-04-21）

### 7.1 已完成的实现批次

已完成的核心提交包括：

- `14ee662` `feat: persist consumer project metadata`
- `d56544d` `feat: add consumer brief contract`
- `3041c6d` `feat: add consumer persona pack`
- `85c2b2e` `feat: add consumer graph build path`
- `a915efe` `feat: branch simulation prep for consumer tests`
- `1e26c7b` `feat: add consumer simulation orchestration`
- `fbc5108` `feat: add consumer scoring and report context`
- `b5fcf90` `feat: add consumer test intake to home flow`
- `d848327` `feat: adapt step views for consumer simulation mode`

### 7.2 已验证结果

- 后端：
  - `backend/.venv/Scripts/python.exe -m pytest`
  - 结果：`45 passed`
- 前端：
  - `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`
  - 结果：`9 passed`
- 前端构建：
  - `npm run build`
  - 结果：成功

### 7.3 真实链路验收结果

使用新的 Zep API Key 对完整主链路进行了实际验收：

- 图谱构建（Zep）：通过，约 `15s`
- 模拟创建：通过，即时返回
- Prepare（`4` 个 profile）：通过，约 `21min`
- 最终状态：`ready`
- 生成产物：
  - `reddit_profiles.json`
  - `twitter_profiles.csv`
  - `simulation_config.json`
  - `state.json`

### 7.4 Phase 1 验收结论

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

结论：

- `consumer_test` Phase 1 已通过正式验收，可作为当前交付基线。

### 7.5 已修复的关键问题

- Step 2 读取 consumer metadata 时兼容 `prepare_info / config / 顶层字段`
- Step 3 rerun 时清理旧 `consumerSummary`，避免残留上一次结果
- Step 2-5 的新增消费者模式文案全部接入 i18n
- 快速追问 prompt 编码问题已修复

## 8. 当前剩余优化项

- 大规模 profile prepare 的耗时优化
- `response_format=json_object` 兼容性的进一步收敛
- 长轮次、真实业务素材和更大样本量下的压测基线
- 默认模式与 `consumer_test` 模式的长期回归记录沉淀

## 9. 后续建议

1. 固化一份正式验收记录模板，后续用于更多消费者测试用例
2. 基于真实业务素材补充更大样本量和更长轮次的性能验证
3. 评估更快模型或 prepare 并行策略，降低 profile 生成耗时
4. 根据 Phase 1 验收结果决定是否进入 Phase 2 的自动预研与更复杂传播建模
