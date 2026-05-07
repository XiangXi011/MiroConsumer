# MiroConsumer 改进文档逐项校验报告（最终版）

> 校验时间：2026-05-09
> 校验标准：改进.md（企业级消费者仿真研究平台）
> 校验方式：3个独立审核 Agent 逐代码、逐行号校对
> 测试状态：关键测试集 84 passed, 0 failed

---

## 总体评估

| 优先级 | 总项 | ✅通过 | ⚠️部分 | ❌未通过 | 通过率 |
|--------|------|--------|--------|----------|--------|
| P0 止血 | 38 | 33 | 5 | 0 | **87%** |
| P1 可信内核 | 66 | 66 | 0 | 0 | **100%** |
| P2 工程化 | 10 | 8 | 1 | 1 | **80%** |
| P3 产品 | 7 | 6 | 1 | 0 | **86%** |
| P4 合规 | 3 | 2 | 0 | 1 | **67%** |
| **总计** | **124** | **115** | **7** | **2** | **93%** |

---

## 一、P0 止血级（38项）— 87%

### P0-1: API 认证授权（7项）— ✅ 7/7

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 未认证访问返回 401 | ✅ | auth/middleware.py L60-66 |
| 2 | 无权限返回 403 | ✅ | auth/middleware.py L72-91 |
| 3 | 导出接口权限校验 | ✅ | simulation.py L405, report.py L338/L869 |
| 4 | 测试覆盖 401/403/跨租户/越权 | ✅ | test_auth.py + test_tenant_isolation.py |
| 5 | API Key / JWT 认证 | ✅ | middleware.py L36-58 双通道 |
| 6 | RBAC 角色模型 | ✅ | auth/models.py L34-44 6角色 |
| 7 | 租户隔离 | ✅ | middleware.py L69 + simulation.py L382/451 + report.py L217/306 |

### P0-2: SECRET_KEY 强校验（5项）— ✅ 4/5（1⚠️）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 默认 SECRET_KEY 启动失败 | ✅ | config.py L255-262 + __init__.py L44-49 |
| 2 | WEAK_SECRET_KEYS 内容完整 | ⚠️ | 6个弱值，第一个因显示截断无法100%确认 |
| 3 | 长度 >= 32 | ✅ | config.py L261 |
| 4 | CI 配置安全测试 | ✅ | ci.yml L102-122 + security.yml |
| 5 | README 生产密钥生成方式 | ✅ | README.md L269-280 |

### P0-3: CORS/安全头/限流（9项）— ✅ 9/9

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 超限返回 429 | ✅ | rate_limiter.py L31-36 |
| 2-5 | 安全头 HSTS/CSP/X-Frame/X-Content-Type | ✅ | __init__.py L109-113 |
| 6 | CORS 不允许 * | ✅ | __init__.py L78-83: production RuntimeError |
| 7 | 三层限流 | ✅ | rate_limiter.py L22-27: ip/user/tenant |
| 8 | LLM 预算限制 | ✅ | llm_governor.py + llm_client.py L89-91 |
| 9 | 导出接口限速 | ✅ | rate_limiter.py L48-66 + simulation.py L406 + report.py L339/L870 |

### P0-4: CI/CD 质量门禁（4项）— ✅ 1/4（3⚠️）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | PR pytest 阻止合并 | ⚠️ | ci.yml 有 pytest，但 branch protection 需 GitHub 配置 |
| 2 | PR 安全扫描阻止合并 | ⚠️ | security.yml 有扫描，但 branch protection 需 GitHub 配置 |
| 3 | Trivy 镜像扫描 | ⚠️ | docker-image.yml L42-48 有 Trivy，但执行顺序在 Build 之前 |
| 4 | 三个 workflow | ✅ | ci.yml + docker-image.yml + security.yml |

### P0-5: 研究边界声明（5项）— ✅ 5/5

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 小样本显示 Exploratory | ✅ | disclaimer.py L41-45 |
| 2 | 禁止统计推断语言 | ✅ | disclaimer.py L58-69 + report_app_service.py L339/391 |
| 3 | 导出报告带方法论页 | ✅ | report_app_service.py L310-361/380/390 |
| 4 | 报告 API 返回 methodology_limits | ✅ | report.py L123/230/267/320 |
| 5 | 指标带 6 个元数据字段 | ✅ | disclaimer.py L25-55: 10个字段 |

### P0-6: LLM 调用治理（8项）— ✅ 7/8（1⚠️）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 单次 LLM 超时可控 | ✅ | llm_client.py L34/73/107-109 |
| 2 | 预算超限自动停止 | ✅ | llm_client.py L89-91 + llm_governor.py L52-58 |
| 3 | 报告展示 fallback 比例 | ⚠️ | chat_json_with_meta 有诊断数据但未接入报告展示 |
| 4 | 管理员成本看板 | ✅ | auth/routes.py L85-94: /admin/llm-cost |
| 5 | LLM 调用 audit record | ✅ | llm_governor.py L65-72 + llm_client.py L236-252 JSONL |
| 6 | per tenant/user/project 预算 | ✅ | llm_governor.py L47-50/81-90 |
| 7 | circuit breaker | ✅ | llm_governor.py L9-35 + llm_client.py L93-124 |
| 8 | retry with backoff | ✅ | retry.py L15-77 + llm_client.py L65-66 |

---

## 二、P1 可信研究内核（66项）— 100%

### P1-1: Consumer Agent v1（8项）— ✅ 8/8

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 感知层接收完整输入 | ✅ | perception.py L21-103 |
| 2 | 决策层有 reason_codes | ✅ | decision.py L114-124 + schemas.py L17 |
| 3 | 表达层有 misread_variant/first_person_voice | ✅ | schemas.py L31-32 + expression.py L44-52 |
| 4 | 结构化 JSON 输出 | ✅ | schemas.py L36-47 + engine.py L146 |
| 5 | JSON 通过 Pydantic 校验 | ✅ | schemas.py: 4个 BaseModel 子类 |
| 6 | VOC 可追溯 agent_id/round_id/input_span/memory_state | ✅ | schemas.py L37-38/45-46 + engine.py L125-142 |
| 7 | fallback 标注 generated_by | ✅ | schemas.py L30 + expression.py L39-41/78-85 |
| 8 | LLM 不做指标计算 | ✅ | engine.py L72-73: 纯算法决策 |

### P1-2: Population Model v1（6项）— ✅ 6/6

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 支持 30/50/100/300 规模 | ✅ | population.py L214-225: 无上限 |
| 2 | 每个画像有 source_basis | ✅ | persona.py L55 |
| 3 | 报告展示 population coverage | ✅ | population.py L243-280: get_population_stats() |
| 4 | 支持画像导入/导出 | ✅ | consumer.py L594: /personas/export + /import |
| 5 | 完整字段（26项） | ✅ | persona.py L7-56: 28个字段 |
| 6 | 三种生成模式 | ✅ | population.py: template(L115)/brief(L124)/calibrated(L166) |

### P1-3: 样本量/统计边界（7项）— ✅ 7/7

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 三模式 | ✅ | modes.py L3-37 |
| 2 | sample_n, run_n | ✅ | monte_carlo.py L22-23 |
| 3 | 小样本不显示置信区间 | ✅ | modes.py L9: quick=False |
| 4 | effect_size | ✅ | monte_carlo.py L146-149: Cohen's d |
| 5 | simulation_manifest.json | ✅ | export.py L51 + simulation.py L427 |
| 6 | 蒙特卡洛验证器 | ✅ | monte_carlo.py L26-110 |
| 7 | 运行历史 + A/B 对比 | ✅ | monte_carlo.py L113-159 |

### P1-4: 社交图谱（10项）— ✅ 10/10

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | random | ✅ | graph.py L161-173 |
| 2 | small-world | ✅ | graph.py L217-283 |
| 3 | scale-free | ✅ | graph.py L175-215 |
| 4 | community | ✅ | graph.py L355-396 |
| 5 | influencer-follower | ✅ | graph.py L285-313 |
| 6 | channel-separated | ✅ | graph.py L315-353 |
| 7 | custom imported | ✅ | graph.py L94-104 |
| 8 | 边8字段 | ✅ | graph.py L9-18: SocialEdge |
| 9 | 路径回溯 | ✅ | graph.py L106-135 |
| 10 | 拓扑 A/B 对比 | ✅ | graph.py L137-152 |

### P1-5: 传播机制（10项）— ✅ 10/10

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | dynamic_participation | ✅ | population.py L15-38: 轮次/状态/压力 |
| 2 | convergence_detector | ✅ | control.py L152-172 |
| 3 | checkpoint_after_each_round | ✅ | control.py L43-55 + run_controller.py L188-192 |
| 4 | partial_retry | ✅ | control.py L103-108 |
| 5 | resume_from_checkpoint | ✅ | control.py L140-149 + run_controller.py L335-340 |
| 6 | event-sourced propagation log | ✅ | run_controller.py L110/149/183 |
| 7 | branch diff | ✅ | control.py L111-126 |
| 8 | intervention replay | ✅ | control.py L129-138 |
| 9 | Early Stop（4条件） | ✅ | control.py L19-31: 6个条件参数 |
| 10 | RunController 集成 RuntimeControl | ✅ | run_controller.py L22/48-51/188-196 |

### P1-6: VOC 真实性（5项）— ✅ 5/5

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | VOC 从认知状态生成 | ✅ | event_mapper.py L28-104 |
| 2 | 存储15个字段 | ✅ | event_mapper.py L73-104: 20个字段 |
| 3 | 区分 sim/real/synthesized | ✅ | event_mapper.py L65-71 |
| 4 | 模板 fallback 打标 | ✅ | event_mapper.py L93 |
| 5 | 可追溯到输入和记忆 | ✅ | event_mapper.py L97-100 |

### P1-7: Evidence/Confidence/Benchmark（8项）— ✅ 8/8

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | evidence_atoms | ✅ | report_context.py L395-485 |
| 2 | Confidence 程序化计算 | ✅ | confidence_scoring.py L99-153/275-294 |
| 3 | 5个权重项 | ✅ | confidence_scoring.py L285-291 |
| 4 | contradiction/fallback penalty | ✅ | confidence_scoring.py L292-293 |
| 5 | 黄金案例集 | ✅ | test_consumer_golden_cases.py |
| 6 | CI smoke benchmark | ✅ | ci.yml L124-141: benchmark job |
| 7 | drift report | ✅ | drift_detector.py + run_controller.py L288-301 |
| 8 | confidence 阈值校准 | ✅ | confidence_calibrator.py + confidence_scoring.py L41-44 |

### P1-8: DOE 实验设计（12项）— ✅ 12/12

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | A/B 测试 | ✅ | doe.py L32-51 |
| 2 | 价格阶梯 | ✅ | doe.py L53-70 |
| 3 | 消息变体 | ✅ | doe.py L72-92 |
| 4 | Claim 变体 | ✅ | doe.py L94-114 |
| 5 | 随机分配 | ✅ | doe.py L116-128 |
| 6 | 分层分配 | ✅ | doe.py L130-156 |
| 7 | 包装变体 | ✅ | doe.py L158-172 |
| 8 | 渠道变体 | ✅ | doe.py L174-188 |
| 9 | 因素设计 | ✅ | doe.py L190-212 |
| 10 | ExperimentDesign | ✅ | doe.py L16-26 |
| 11 | ExperimentVariant | ✅ | doe.py L7-12 |
| 12 | 可重复性 | ✅ | doe.py L24: random_seed |

---

## 三、P2 工程生产化（10项）— 80%

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| P2-1 | API Pydantic 化 | ✅ | 42个 Pydantic Request 类 + safe_get_json() |
| P2-2 | 错误格式统一 | ⚠️ | ErrorCodes 仅 simulation.py 使用 |
| P2-3 | 前端 TypeScript | ❌ | 无 tsconfig.json，纯 JS+Vue |
| P2-4 | Alembic migration | ✅ | alembic.ini + versions/ |
| P2-5 | 存储边界 | ✅ | config.py L196-230 |
| P2-6 | 日志脱敏 | ✅ | __init__.py L19-35 |
| P2-7 | Prometheus/Sentry | ✅ | metrics.py + __init__.py L130-144 |
| P2-8 | Worker continuous loop | ✅ | worker.py L62-99: SIGTERM/SIGINT |
| P2-9 | DI 容器 | ✅ | container.py: Service Locator |
| P2-10 | 测试覆盖配置 | ✅ | pyproject.toml: --cov-fail-under=70 |

---

## 四、P3 产品体验（7项）— 86%

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| P3-1 | Brief 版本控制 | ✅ | models.py L356-358: schema_version |
| P3-2 | Mode 引导 | ✅ | modes.py L3-37 |
| P3-3 | Persona Pack 预览/编辑 | ⚠️ | 预览+上传有，无原地编辑 API |
| P3-4 | Dry Run | ✅ | run_controller.py L38/47/62-63/305-320 |
| P3-5 | 传播路径可视化 | ✅ | consumer.py L131 + PropagationPathGraph.vue |
| P3-6 | PDF/Word/PPT 导出 | ✅ | export.py L70-152: 3个导出函数 |
| P3-7 | 追问分层 | ✅ | followup_question_engine.py L8-32: 7种类型 |

---

## 五、P4 合规（3项）— 67%

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| P4-1 | 商业模式/GTM | ❌ | 无 pricing/GTM 文档 |
| P4-2 | AGPL 许可证说明 | ✅ | LICENSE + README L282-289 |
| P4-3 | 文档齐套 | ✅ | CONTRIBUTING.md + CHANGELOG.md + docs/deployment.md |

---

## 遗留问题清单（9项）

### ❌ 未通过（2项）
1. **P2-3 前端 TypeScript** — 纯 JS+Vue，需全量迁移（大规模重构）
2. **P4-1 商业模式/GTM** — 需业务决策，非代码问题

### ⚠️ 部分完成（7项）
1. **P0-2.2** WEAK_SECRET_KEYS 第一个值因显示截断无法完全验证
2. **P0-4.1** PR pytest 阻止合并依赖 GitHub branch protection 设置
3. **P0-4.2** PR 安全扫描阻止合并同上
4. **P0-4.3** Trivy 执行顺序在 Build 之前，应调整
5. **P0-6.3** LLM fallback 诊断数据未接入报告展示
6. **P2-2** ErrorCodes 仅 simulation.py 使用，其他端点用内联字符串
7. **P3-3** Persona Pack 无原地编辑 API

---

## 与上次审计对比

| 指标 | 上次(5/8) | 本次(5/9) | 提升 |
|------|----------|----------|------|
| P0 通过率 | 45% | **87%** | +42% |
| P1 通过率 | 28% | **100%** | +72% |
| P2 通过率 | 40% | **80%** | +40% |
| P3 通过率 | 29% | **86%** | +57% |
| P4 通过率 | 0% | **67%** | +67% |
| **总体** | **34%** | **93%** | **+59%** |
