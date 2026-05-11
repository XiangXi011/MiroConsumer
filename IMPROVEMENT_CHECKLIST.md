# MiroConsumer 改进清单

> 来源：2026-05-07 综合审计（架构 / 代码 / AI 治理 / 安全 / 业务真实感 / 商业化 / 可信度）
> 执行方式：Claude Code 逐任务执行，Hermes 审计验收

---

## P0 — 止血（Day 1）

### 任务 1：Production Safety Gate
**目标**：所有安全、限流、日志、环境变量校验在 app 启动时集中拦截

**验收标准**：
- [ ] CORS 严格限定 `CORS_ALLOWED_ORIGINS`，不含 `*`
- [ ] 安全头全量注入：X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS, CSP
- [ ] SECRET_KEY 启动时校验，缺失直接退出
- [ ] 健康检查不泄露版本/模型/平台信息
- [ ] 全局 API 限流中间件（可配置）
- [ ] 结构化日志输出（JSON 格式）
- [ ] 请求体大小限制

### 任务 2：Methodology Disclaimers
**目标**：所有输出强制附带方法论声明，防止用户误读

**验收标准**：
- [ ] ConsumerReportHeader 增加方法论声明
- [ ] society_run_summary 强制返回 disclaimer 字段
- [ ] 社会仿真输出前端增加"模拟 VOC"声明
- [ ] 前端不可被关闭或隐藏声明

### 任务 3：API Contract Hardening
**目标**：补齐缺失参数校验、统一错误码、补全 API 文档

**验收标准**：
- [ ] 创建仿真必填参数缺失返回 400（非 500）
- [ ] 仿真不存在返回 404（非 500）
- [ ] 枚举值无效返回 400
- [ ] 接口幂等（重复调用不出错）
- [ ] 错误码统一枚举
- [ ] API 文档可用（Swagger/ReDoc）
- [ ] openapi.json 可访问
- [ ] 错误响应包含 request_id / timestamp

### 任务 4：LLM Governance
**目标**：所有 LLM 调用透明、可审计、成本可控

**验收标准**：
- [ ] 每次 LLM 调用记录模型名、token 用量、耗时
- [ ] 输出长度超限、JSON 不合法时返回 422
- [ ] LLM 预算耗尽时有明确日志
- [ ] 每次调用记录 prompt hash
- [ ] LLM 调用失败自动降级到规则引擎
- [ ] 思维链字段在生产环境关闭
- [ ] 调用日志持久化

### 任务 5：Test & CI Baseline
**目标**：没有测试不允许合代码

**验收标准**：
- [ ] pytest + coverage 基础框架
- [ ] API 层测试覆盖
- [ ] CI 流水线自动跑测试 + lint
- [ ] 覆盖率报告输出

---

## P1 — 可信研究内核（Week 1–2）

### 任务 6：Consumer Agent v1
**目标**：建立三层认知架构（感知→决策→表达），解决人格同质化

**验收标准**：
- [ ] 感知层：环境信号输入
- [ ] 决策层：推理判断
- [ ] 表达层：输出 quote
- [ ] 人格多样性：不同 Agent 有不同反应
- [ ] 输出包含 reasoning_trace
- [ ] 维度对齐评分

### 任务 7：Population Model v1
**目标**：从固定 8 人到 50-1000 人可配人群

**验收标准**：
- [ ] 核心 persona 自动生成（基于 Brief）
- [ ] 扩展 persona 参数化生成
- [ ] shadow agent 概率行为
- [ ] 分层抽样（年龄/收入/城市/消费观）
- [ ] 人群配置可调
- [ ] 人群统计报表

### 任务 8：Monte Carlo Control Layer
**目标**：仿真结果可复现、可比、可校准

**验收标准**：
- [ ] seed 控制可复现
- [ ] 30-100 次重复运行
- [ ] 置信区间计算
- [ ] 运行历史可查询
- [ ] A/B 方案对比
- [ ] 真实基准校准

### 任务 9：Social Graph Realism
**目标**：从完全图到真实社交网络结构

**验收标准**：
- [ ] 小世界网络（Watts-Strogatz）
- [ ] 跨社群桥接节点
- [ ] 话题激活阈值
- [ ] 社群结构可视化
- [ ] 影响力节点识别

---

## P2 — 工程生产化（Week 2–3）

### 任务 10：Database & API Integration
**目标**：从文件存储到数据库持久化

**验收标准**：
- [ ] SQLAlchemy ORM 定义
- [ ] Alembic 迁移脚本
- [ ] CRUD API 接口
- [ ] 事务管理
- [ ] 分页查询
- [ ] 索引优化

---

## 验证优先级（v2 新增）

| 验证层 | 频率 | 责任 |
|--------|------|------|
| L1 模块测试 | 每次提交 | Codex |
| L2 集成测试 | 每个任务完成 | Hermes |
| L3 业务验证 | 每周 | 用户 |
| L4 真实校准 | 每月 | 用户 |

---

**当前状态**：任务 1 待执行
**最后更新**：2026-05-07
