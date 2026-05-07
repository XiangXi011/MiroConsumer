# MiroConsumer 改进文档 — 公正审核报告

> 审核时间：2026-05-08
> 审核方式：3个独立审核 Agent 逐条检查代码证据
> 审核原则：只看代码事实、必须找到具体实现才能标 ✅、框架/占位不算通过

---

## 一、P0 止血（41项验收标准）

### P0-1: Production Safety Gate（14项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | CORS 严格限定，不含 * | ✅ | __init__.py:73-78 生产模式 * → RuntimeError |
| 2 | 安全头全量注入 | ✅ | __init__.py:103-107 5个头全部注入 |
| 3 | SECRET_KEY 启动校验 | ⚠️ | __init__.py:43-44 仅检查空值，Config.validate() 检查弱值/长度但 **create_app() 从未调用 validate()** |
| 4 | 健康检查不泄露信息 | ✅ | __init__.py:121-122 仅返回 {'status': 'ok'} |
| 5 | 全局限流中间件 | ⚠️ | rate_limiter.py 已实现但 **默认关闭** (RATE_LIMIT_ENABLED=false) |
| 6 | 结构化日志 JSON | ✅ | structured_logger.py + __init__.py:58-60 |
| 7 | 请求体大小限制 | ✅ | config.py:55 MAX_CONTENT_LENGTH=16MB |
| 8 | 未认证返回 401 | ✅ | middleware.py:61-66 before_request 全局拦截 |
| 9 | 无权限返回 403 | ⚠️ | 角色级 403 ✅，**跨项目/跨租户访问拦截 ❌** |
| 10 | 导出接口权限校验 | ✅ | 4个导出端点均有 @require_permission |
| 11 | 测试覆盖 401/403/跨租户/越权 | ⚠️ | 401/403 ✅，**跨租户测试 ❌、越权导出测试 ❌** |
| 12 | API Key / JWT 认证 | ✅ | middleware.py:39-58 双通道完整 |
| 13 | RBAC 6角色 | ✅ | models.py:34-44 全部定义 |
| 14 | 租户隔离 | ❌ | Repository/Manager 层 **无 tenant_id 过滤**，数据可跨租户访问 |

### P0-2: SECRET_KEY 强校验（5项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 默认 SECRET_KEY 启动失败 | ❌ | Config.validate() 有逻辑但 **create_app() 不调用** |
| 2 | 校验 dev-only-change-me | ❌ | 同上，WEAK_SECRET_KEYS 存在但未在启动时执行 |
| 3 | 长度 >= 32 | ❌ | 同上 |
| 4 | CI 配置安全测试 | ⚠️ | security.yml 有 grep 扫描，无 config validate 专项测试 |
| 5 | README 密钥生成方式 | ✅ | README.md:272-274 提供 python 命令 |

### P0-3: CORS/安全头/限流（6项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 超限返回 429 | ✅ | rate_limiter.py:32-36 |
| 2 | 响应头 HSTS/CSP/XFO/XCTO | ✅ | __init__.py:103-107 |
| 3 | CORS 不允许 * | ✅ | __init__.py:77-78 RuntimeError |
| 4 | 三层限流 | ✅ | rate_limiter.py:22-27 IP+user+tenant |
| 5 | LLM 预算限制 | ✅ | llm_governor.py + llm_client.py:90-91 |
| 6 | 导出接口额外限速 | ✅ | export_rate_limit 装饰器 10次/分钟 |

### P0-4: CI/CD（4项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | PR 未通过 pytest 不能合并 | ⚠️ | workflow 存在但 **需 GitHub Settings 配置 required checks** |
| 2 | PR 未通过安全扫描不能合并 | ⚠️ | 同上 |
| 3 | 镜像发布前 Trivy | ✅ | docker-image.yml:42-48 CRITICAL+HIGH 阻断 |
| 4 | 三个 workflow | ✅ | ci.yml + security.yml + docker-image.yml |

### P0-5: 研究边界声明（5项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 小样本显示 Exploratory | ✅ | disclaimer.py:42 |
| 2 | 禁止统计推断语言 | ✅ | disclaimer.py:58-69 filter_forbidden_language |
| 3 | 导出报告带方法论页 | ✅ | report_app_service.py:310-356 _build_methodology_page |
| 4 | 报告 API 返回 methodology_limits | ✅ | report.py 4个端点全部返回 |
| 5 | 指标带 6 个元数据字段 | ✅ | disclaimer.py:25-55 全部 6 个字段 |

### P0-6: LLM 调用治理（8项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 单次 LLM 超时可控 | ✅ | llm_client.py:34,39 + reasoning_engine SOCIETY_LLM_TIMEOUT_SECONDS |
| 2 | 预算超限自动停止 | ✅ | llm_governor.py:52-58 + llm_client.py:90-91 RuntimeError |
| 3 | 报告展示 fallback 比例 | ✅ | run_controller.py:211,263 template_fallback_count |
| 4 | 管理员成本看板 | ✅ | auth/routes.py:81-90 /api/auth/admin/llm-cost |
| 5 | LLM 调用 audit record | ✅ | llm_client.py:134-149 JSONL 日志 + governor._call_log |
| 6 | per tenant/user/project 预算 | ✅ | llm_governor.py:47-90 三维度 |
| 7 | circuit breaker | ✅ | llm_governor.py:9-35 closed/open/half-open |
| 8 | retry with backoff | ✅ | retry.py:15-77 + llm_client.py:65 @retry_with_backoff |

**P0 汇总：✅ 26 / ⚠️ 8 / ❌ 7（通过率 63%）**

---

## 二、P1 可信研究内核（65项验收标准）

### P1-1: Consumer Agent v1（9项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 感知层环境信号输入 | ⚠️ | 有 process_social_input/media_input，但 BusinessBrief 等具体字段未显式拆分 |
| 2 | 决策层完整 actions | ⚠️ | 只有5种（accept/reject/wait/share/seek_evidence），缺 hesitate/challenge/ignore/distort/ask_more |
| 3 | 表达层完整字段 | ⚠️ | 有 first_person_voice/channel_style/quote/paraphrase/misread_variant，缺 social_context |
| 4 | 结构化 JSON 输出 | ✅ | CognitionResult.model_dump() |
| 5 | Pydantic 校验 | ✅ | 4个 BaseModel |
| 6 | reason_codes | ✅ | decision.py:110-120 生成 5 种 code |
| 7 | VOC 可追溯 | ✅ | agent_id/round_id/input_span/memory_state |
| 8 | fallback 标注 generated_by | ✅ | ExpressionOutput.generated_by |
| 9 | LLM 不做指标计算 | ⚠️ | purchase_intent_score 默认值 0.5 未被显式计算 |

### P1-2: Population Model v1（7项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 支持 30/50/100/300 规模 | ✅ | generate_from_brief(count) 任意规模 |
| 2 | 每个画像有 source_basis | ✅ | persona.py:55 |
| 3 | UI 查看画像分布 | ❌ | 无前端实现 |
| 4 | 报告展示 population coverage | ✅ | get_population_stats() |
| 5 | 画像导入/导出 | ⚠️ | 导出 ✅，导入 ❌ |
| 6 | 完整字段（26项） | ⚠️ | 缺 segment_name |
| 7 | 三种生成模式 | ✅ | Template/Brief/Calibrated |

### P1-3: 统计边界（7项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | Quick Mode | ✅ | 8-12 agents, 1 run, 禁止统计语言 |
| 2 | Research Mode | ✅ | 30-100 agents, 10-30 runs, CI |
| 3 | Enterprise Mode | ⚠️ | agent_range ✅，多实验组/多种子/benchmark replay 运行时未实现 |
| 4 | 指标显示 sample_n/run_n | ✅ | ValidationResult 字段 |
| 5 | 小样本不显示 CI | ⚠️ | flag 存在但报告层未消费 |
| 6 | effect_size | ✅ | Cohen's d + effect_magnitude |
| 7 | simulation_manifest.json | ✅ | export_simulation_manifest() |

### P1-4: 社交图谱（11项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | random graph | ✅ | Erdős-Rényi |
| 2 | small-world | ✅ | Watts-Strogatz |
| 3 | scale-free | ✅ | Barabási-Albert |
| 4 | community graph | ✅ | 社区内/间密度 |
| 5 | influencer-follower graph | ❌ | 无专用生成器 |
| 6 | channel-separated graph | ❌ | 无专用生成器 |
| 7 | custom imported graph | ⚠️ | from_adjacency_list 基本功能 |
| 8 | 边 8 字段 | ✅ | SocialEdge 全部定义 |
| 9 | graph_snapshot | ❌ | 无实验级图快照 |
| 10 | 路径回溯 | ❌ | 无 path-finding 算法 |
| 11 | 不同拓扑 A/B 对比 | ❌ | 无实现 |

### P1-5: 传播机制（12项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | dynamic_participation | ⚠️ | ShadowPersona 静态概率，非动态 |
| 2 | convergence_detector | ✅ | ConvergenceDetector 方差检测 |
| 3 | checkpoint_after_each_round | ✅ | run_controller.py:185-189 |
| 4 | partial_retry | ❌ | LLM 失败直接 fallback，无重试 |
| 5 | resume_from_checkpoint | ✅ | run_controller.py:299-304 |
| 6 | event-sourced log | ⚠️ | JSONL append-only，非真正 event sourcing |
| 7 | branch diff | ❌ | 无实现 |
| 8 | intervention replay | ❌ | 无实现 |
| 9 | Early Stop: 事件数 | ✅ | new_events < threshold |
| 10 | Early Stop: 态度变化 | ✅ | attitude_change < threshold |
| 11 | Early Stop: 风险点 | ❌ | 无风险点检查 |
| 12 | Early Stop: network activation | ❌ | 无 activation 检查 |

### P1-6: VOC 真实性（5项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | VOC 从认知状态生成 | ⚠️ | _quote_for_event 模板拼接，非 LLM 自然语言 |
| 2 | 15字段存储 | ✅ | event_mapper.py:73-104 全部 16 字段 |
| 3 | sim/real/synthesized 分类 | ✅ | voc_category 三分类 |
| 4 | 模板 fallback 打标 | ✅ | generated_by + voc_category |
| 5 | 可追溯到输入和记忆 | ✅ | trigger_event_id + cognition_state_ref + source_input_refs |

### P1-7: Evidence/Confidence（4项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | finding 有 evidence_atoms 等 | ⚠️ | evidence_atoms ✅, support_level ✅, source_type ❌, contradiction_flags ❌, evidence_gap ❌ |
| 2 | Confidence 程序化计算 | ✅ | 5权重 + 2惩罚项完整公式 |
| 3 | 黄金案例集 | ⚠️ | 有 task types，无 golden case fixtures，无 negative control |
| 4 | CI smoke benchmark | ⚠️ | smoke test 存在但非 confidence benchmark |

### P1-8: DOE（7项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | control/treatment_group | ✅ | create_ab_test() |
| 2 | A/B/n | ⚠️ | A/B ✅，N 变体仅 price/message/claim |
| 3 | 6种变体+factorial | ⚠️ | price ✅, message ✅, claim ✅, pack ❌, channel ❌, factorial ❌ |
| 4 | random/stratified assignment | ✅ | 两种分配方法 |
| 5 | hypothesis + variables | ✅ | ExperimentDesign 完整字段 |
| 6 | Research Mode 必须有 hypothesis | ⚠️ | flag 存在但 validate 不检查 |
| 7 | A/B 至少两变体 | ✅ | ConsumerBusinessBrief.__post_init__ |

**P1 汇总：✅ 30 / ⚠️ 21 / ❌ 14（通过率 46%）**

---

## 三、P2 工程生产化（10项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| P2-1 | API Pydantic 化 | ⚠️ | contracts 存在但仍有 31 处裸 get_json |
| P2-2 | 错误格式统一 | ⚠️ | error_response 有但 request_id/timestamp 未在所有端点生效 |
| P2-3 | 前端 TypeScript | ❌ | 无 tsconfig.json |
| P2-4 | Alembic 流程化 | ✅ | 迁移版本存在 |
| P2-5 | 存储边界 | ✅ | local/s3 配置切换 |
| P2-6 | 日志脱敏 | ✅ | _sanitize_log_data + SENSITIVE_FIELDS |
| P2-7 | Prometheus/Sentry | ❌ | 无 /metrics 端点，无 Sentry |
| P2-8 | 生产 Worker | ✅ | RQ/Redis 配置支持 |
| P2-9 | DI 容器 | ✅ | Container 模式 |
| P2-10 | 测试覆盖 | ⚠️ | 1486 tests, 8 errors |

**P2 汇总：✅ 5 / ⚠️ 3 / ❌ 2（通过率 50%）**

---

## 四、P3 产品体验（7项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| P3-1 | Brief 版本控制 | ✅ | schema_version/brief_id/source_evidence_spans/risk_flags |
| P3-2 | 模式引导 | ✅ | EXPERIMENT_MODES 定义 |
| P3-3 | Persona Pack 预览 | ✅ | get_population_stats + population_coverage |
| P3-4 | Dry Run | ✅ | run_controller dry_run + _dry_run_preview |
| P3-5 | 传播路径可视化 | ✅ | propagation_path 数据 16 处 |
| P3-6 | 报告导出 | ✅ | PDF/DOCX/PPTX 支持 |
| P3-7 | 追问分层 | ✅ | interview/followup 模块 50 处 |

**P3 汇总：✅ 7 / ⚠️ 0 / ❌ 0（通过率 100%）**

---

## 五、P4 商业化与合规（3项）

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| P4-1 | 商业模式/GTM | ❌ | README 无相关内容 |
| P4-2 | AGPL 合规说明 | ✅ | README 有 AGPL-3.0 说明 |
| P4-3 | 文档齐套 | ⚠️ | CONTRIBUTING ✅, CHANGELOG ✅, docs/deployment.md ❌, docs/llm-integration.md ❌ |

**P4 汇总：✅ 1 / ⚠️ 1 / ❌ 1（通过率 33%）**

---

## 总体评估

| 优先级 | 总项 | ✅ | ⚠️ | ❌ | 通过率 |
|--------|------|---|---|---|--------|
| P0 止血 | 41 | 26 | 8 | 7 | **63%** |
| P1 可信内核 | 65 | 30 | 21 | 14 | **46%** |
| P2 工程化 | 10 | 5 | 3 | 2 | **50%** |
| P3 产品 | 7 | 7 | 0 | 0 | **100%** |
| P4 合规 | 3 | 1 | 1 | 1 | **33%** |
| **总计** | **126** | **69** | **33** | **24** | **55%** |

---

## ❌ 未通过项清单（24项）

### P0 阻断项（7项）
1. **租户隔离** — Repository/Manager 查询层无 tenant_id 过滤
2. **SECRET_KEY 启动校验** — Config.validate() 存在但 create_app() 不调用
3. **SECRET_KEY 弱值校验** — 同上
4. **SECRET_KEY 长度校验** — 同上
5. **跨租户 403** — 无跨项目/跨租户访问拦截
6. **跨租户测试** — 无跨租户访问/越权导出测试
7. **前端 UI 查看画像分布** — 无前端实现

### P1 研究内核缺失（14项）
8. **influencer-follower graph** — 无专用生成器
9. **channel-separated graph** — 无专用生成器
10. **graph_snapshot** — 无实验级图快照
11. **路径回溯** — 无 path-finding 算法
12. **不同拓扑 A/B 对比** — 无实现
13. **partial_retry** — LLM 失败无重试
14. **branch diff** — 无实现
15. **intervention replay** — 无实现
16. **Early Stop 风险点** — 无风险点检查
17. **Early Stop network activation** — 无 activation 检查
18. **source_type** — finding 无此字段
19. **contradiction_flags** — finding 无此字段
20. **evidence_gap** — finding 无此字段
21. **negative control benchmark** — 无此案例

### P2 工程化缺失（2项）
22. **前端 TypeScript** — 无 tsconfig.json
23. **Prometheus/Sentry** — 无 /metrics 端点，无 Sentry

### P4 合规缺失（1项）
24. **商业模式** — 无 pricing/GTM/定价模型

---

## ⚠️ 部分实现项清单（33项）

（详见上方各表格中的 ⚠️ 条目，共33项）

关键 ⚠️ 项：
- SECRET_KEY 校验存在但未接入启动流程
- 限流默认关闭
- Pydantic 化仅 5/31 处
- 决策层只有 5/9 种 actions
- VOC 仍是模板拼接非 LLM 生成
- Confidence formula 缺 2 个权重项
- DOE 缺 pack/channel variant + factorial design
