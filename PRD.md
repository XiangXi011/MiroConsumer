# 产品需求文档（PRD）：MiroFish 驱动的消费者传播测试

## 1. 产品背景

MiroFish 已具备完整的 `图谱构建 -> 仿真准备 -> 仿真运行 -> 报告生成 -> 深度交互` 主链路，但当前能力仍偏通用仿真。消费者项目则沉淀了 `BusinessBrief`、消费者画像、评分逻辑和研究报告结构，但核心评估方式仍偏静态、单轮、并发评审。

本项目的目标不是新增一套平行产品，也不是用消费者项目替换 MiroFish，而是：

- 以 MiroFish 为主骨架
- 将消费者项目中的领域能力迁入 MiroFish
- 先落地一个可执行的 Phase 1：`概念测试 + 文案测试 + 群体传播增强`

## 2. 当前版本定位

当前版本定位为：

> 一个由 MiroFish 驱动的、面向概念测试与文案测试的消费者传播仿真工作流。

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

### 4.1 MiroFish 为主

MiroFish 继续保留并主导：

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
- 当前端不显式传入 `consumer_test` 时，系统必须完全走原版 MiroFish 逻辑
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

### 7.1 已完成

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

### 7.2 已验证与验收通过

- 后端测试：
  - `backend/.venv/Scripts/python.exe -m pytest`
  - 结果：`45 passed`
- 前端测试：
  - `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`
  - 结果：`9 passed`
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

结论：

- `consumer_test` Phase 1 已完成并通过正式验收。

### 7.3 当前已知限制

- Kimi For Coding 响应较慢，单个 profile 约 `3-5` 分钟，`4` 个 profile 的完整 prepare 约 `21` 分钟
- `response_format=json_object` 的兼容性仍不稳定，当前已通过 proxy 做兼容缓解
- 小规模 profile（如 `4` 个）可稳定运行；更大规模场景建议切换更快的模型

## 8. 风险与依赖

### 8.1 关键依赖

- 根目录 `.env` 中的 LLM / Zep 配置
- OASIS 运行环境
- 本地 Python 虚拟环境与前端依赖

### 8.2 当前主要风险

- 大规模 prepare 的耗时与模型成本仍偏高
- `json_object` 兼容性在不同模型或代理配置下仍可能波动
- `pendingUpload.js` 动静态导入混用和前端 chunk size warning 仍存在，但不是本轮阻断问题

## 9. 后续阶段与终局愿景

### Phase 2

- 自动预研与背景材料挂载
- 更强的群体讨论与传播事件设计
- 更接近真实市场的信息分层与认知差异

### Phase 3

- 完整 OASIS 消费者社会化演化沙盘
- Tiered RAG
- 研究员实时干预
- DingTalk / 外部焦点小组接口
- 从工具型能力升级为咨询型与资产型平台
