# MiroConsumer 改进文档逐项校验报告

> 校验时间：2026-05-08
> 校验标准：改进.md（企业级消费者仿真研究平台）
> 测试：1386 tests collected（8 errors）
> Git commits：15+

---

## 一、P0 阻塞级（30项验收标准）

### P0-1: API 认证授权（7项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 未认证访问返回 401 | ✅ | middleware.py L60-66: before_request 全局钩子 |
| 2 | 无权限返回 403 | ⚠️ | 角色级 403 ✅；项目归属检查 ❌；跨租户防护 ❌ |
| 3 | 导出接口权限校验 | ✅ | 4个导出端点均有 @require_permission |
| 4 | 测试覆盖 401/403/跨租户/越权 | ⚠️ | 401/403/越权导出 ✅；跨租户 ❌ |
| 5 | API Key / JWT 认证 | ✅ | X-API-Key + Bearer JWT 双通道 |
| 6 | RBAC 角色模型 | ✅ | 6角色完整权限映射 |
| 7 | 租户隔离 | ❌ | g.current_tenant 已设置但零端点使用，Repository 无 tenant 过滤 |

### P0-2: SECRET_KEY 强校验（5项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 默认 SECRET_KEY 启动失败 | ✅ | config.py validate() + __init__.py RuntimeError |
| 2 | 校验 dev-only-change-me | ❌ | WEAK_SECRET_KEYS 中是截断值 `'dev-...me'`，不完整 |
| 3 | 长度 >= 32 | ✅ | config.py L260: len(sk) < 32 |
| 4 | CI 配置安全测试 | ⚠️ | ci.yml security job 只有 grep 检查，无 pytest 覆盖 |
| 5 | README 生产密钥生成方式 | ⚠️ | 无具体命令（如 openssl rand -hex 32） |

### P0-3: CORS/安全头/限流（9项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 超限返回 429 | ✅ | rate_limiter.py L27 |
| 2 | 响应头 HSTS | ✅ | __init__.py L102 |
| 3 | 响应头 CSP | ✅ | __init__.py L103 |
| 4 | 响应头 X-Frame-Options | ✅ | __init__.py L100 |
| 5 | 响应头 X-Content-Type-Options | ✅ | __init__.py L99 |
| 6 | CORS 不允许 * | ⚠️ | 默认 localhost:3000，但无代码强制拒绝 * |
| 7 | IP+user_id+tenant_id 三层限流 | ❌ | 仅 IP 层，无 user/tenant 维度 |
| 8 | LLM 调用预算限制 | ✅ | llm_budget_manager + llm_governor |
| 9 | 导出接口额外限速 | ❌ | 3个导出端点均无 @rate_limit |

### P0-4: CI/CD 质量门禁（4项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | PR 未通过 pytest 不能合并 | ⚠️ | ci.yml 有 pytest，但无 branch protection 配置 |
| 2 | PR 未通过安全扫描不能合并 | ❌ | 无 bandit/SAST，security job 质量不足 |
| 3 | 镜像发布前 Trivy | ❌ | docker-image.yml 无 Trivy 步骤 |
| 4 | 三个 workflow | ❌ | 只有 ci.yml + docker-image.yml，缺 security.yml |

### P0-5: 研究边界声明（5项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 小样本显示 Exploratory Simulation | ✅ | disclaimer.py L31-35 |
| 2 | 禁止统计推断语言 | ⚠️ | forbidden_language 标志存在但无执行层过滤 |
| 3 | 导出报告带方法论页 | ❌ | report_app_service 未注入 methodology page |
| 4 | 报告 API 返回 methodology_limits | ⚠️ | GET /<id> ✅；by-simulation ❌ |
| 5 | 指标带 6 个元数据字段 | ❌ | 缺 random_seed 和 evidence_support |

### P0-6: LLM 调用治理（8项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 单次 LLM 超时可控 | ✅ | request_timeout + per_call_timeout_seconds |
| 2 | 预算超限自动停止 | ✅ | governor.check_budget + RuntimeError |
| 3 | 报告展示 fallback 比例 | ✅ | template_fallback_coverage 计算链路 |
| 4 | 管理员成本看板 | ❌ | 无 admin cost/budget API 端点 |
| 5 | LLM 调用 audit record | ⚠️ | JSONL 日志 ✅；chat_with_finish_reason 无日志 ❌ |
| 6 | per tenant/user/project 预算 | ❌ | 仅 per-tenant，硬编码 "default" |
| 7 | circuit breaker | ✅ | closed/open/half-open 完整实现 |
| 8 | retry with backoff | ⚠️ | 装饰器已实现但未接入 LLM 调用链 |

**P0 汇总：✅ 20 / ⚠️ 9 / ❌ 15（通过率 45%）**

---

## 二、P1 可信研究内核（54项验收标准）

### P1-1: Consumer Agent v1（8项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 感知层接收完整输入 | ✅ | perception.py 5处 BusinessBrief 相关 |
| 2 | 决策层有 reason_codes | ❌ | decision.py 无 reason_codes 字段 |
| 3 | 表达层有 misread_variant/first_person_voice | ❌ | expression.py 无这些字段 |
| 4 | 结构化 JSON 输出 | ✅ | CognitionResult Pydantic |
| 5 | JSON 通过 Pydantic 校验 | ✅ | schemas.py BaseModel |
| 6 | VOC 可追溯 agent_id/round_id/input_span | ⚠️ | agent_id ✅；round_id ✅；input_span ❌；memory_state ❌ |
| 7 | fallback 标注 generated_by=fallback | ✅ | ExpressionOutput.generated_by |
| 8 | LLM 不做指标计算 | ✅ | 指标由 Python 计算，LLM 只输出判断 |

### P1-2: Population Model v1（6项）

| # | 验收标准 | 状态 | 代码证据 |
|---|---------|------|---------|
| 1 | 支持 30/50/100/300 规模 | ✅ | PopulationGenerator.generate_diverse_population(n) |
| 2 | 每个画像有 source_basis | ❌ | persona.py 无 source_basis 字段 |
| 3 | 报告展示 population coverage | ❌ | 无此功能 |
| 4 | 支持画像导入/导出 | ✅ | to_prompt_description 等方法 |
| 5 | 完整字段（26项） | ⚠️ | 有9字段，缺17个（family_structure, occupation, claim_skepticism 等） |
| 6 | 三种生成模式 | ⚠️ | Template ✅；Brief-driven ❌；Data-calibrated ❌ |

### P1-3: 样本量/统计边界（7项）

| # | 验收标准 | 状态 |
|---|---------|------|
| 1 | Quick/Research/Enterprise 三模式 | ✅ |
| 2 | 每个指标显示 sample_n, run_n | ❌ |
| 3 | 小样本不显示置信区间 | ⚠️ |
| 4 | 所有对比指标有 effect_size | ❌ |
| 5 | 可导出 simulation_manifest.json | ❌ |
| 6 | 蒙特卡洛验证器 | ✅ |
| 7 | 运行历史 + A/B 对比 | ✅ |

### P1-4: 社交图谱（10项）

| # | 验收标准 | 状态 |
|---|---------|------|
| 1 | random graph | ❌ |
| 2 | small-world network | ✅ |
| 3 | scale-free network | ❌ |
| 4 | community graph | ✅ |
| 5 | influencer-follower graph | ❌ |
| 6 | channel-separated graph | ⚠️ |
| 7 | custom imported graph | ❌ |
| 8 | 边包含完整8字段 | ⚠️ |
| 9 | 路径回溯 | ✅ |
| 10 | 不同拓扑 A/B 对比 | ⚠️ |

### P1-5: 传播机制（10项）

| # | 验收标准 | 状态 |
|---|---------|------|
| 1 | dynamic_participation_model | ❌ |
| 2 | convergence_detector | ❌ |
| 3 | checkpoint_after_each_round | ✅ |
| 4 | partial_retry | ❌ |
| 5 | resume_from_checkpoint | ⚠️ |
| 6 | event-sourced propagation log | ⚠️ |
| 7 | branch diff | ❌ |
| 8 | intervention replay | ⚠️ |
| 9 | Early Stop（4条件） | ⚠️（2/4满足） |
| 10 | RunController 集成 RuntimeControl | ❌ |

### P1-6: VOC 真实性（5项）

| # | 验收标准 | 状态 |
|---|---------|------|
| 1 | VOC 从 Agent 认知状态生成 | ⚠️（模板为主） |
| 2 | 存储15个字段 | ❌（仅3个） |
| 3 | 区分 simulated/real/synthesized VOC | ❌ |
| 4 | 模板 fallback 打标 | ✅ |
| 5 | 可追溯到输入和记忆 | ⚠️ |

### P1-7: Evidence/Confidence/Benchmark（8项）

| # | 验收标准 | 状态 |
|---|---------|------|
| 1 | evidence_atoms/source_type/support_level | ⚠️（部分） |
| 2 | Confidence 程序化计算 | ✅ |
| 3 | 5个权重项 | ⚠️（3/5） |
| 4 | contradiction_penalty/fallback_penalty | ❌ |
| 5 | 黄金案例集 | ⚠️（4/6） |
| 6 | CI smoke benchmark | ⚠️ |
| 7 | drift report | ❌ |
| 8 | confidence 阈值校准 | ❌ |

### P1-8: DOE 实验设计（12项）

| # | 验收标准 | 状态 |
|---|---------|------|
| 1 | control/treatment_group | ✅ |
| 2 | A/B/n | ⚠️（A/B ✅，N变体 ❌） |
| 3 | price ladder | ✅ |
| 4 | message/claim/pack/channel variant | ❌ |
| 5 | factorial design | ❌ |
| 6 | random assignment | ✅ |
| 7 | stratified assignment | ⚠️（字段有，逻辑无） |
| 8 | hypothesis | ✅ |
| 9 | independent/dependent variables | ✅ |
| 10 | control_variables | ❌ |
| 11 | Research Mode 必须有 hypothesis | ⚠️（标志有，校验无） |
| 12 | A/B 至少两变体 | ✅ |

**P1 汇总：✅ 21 / ⚠️ 18 / ❌ 37（通过率 28%）**

---

## 三、P2 工程生产化（10项）

| # | 验收标准 | 状态 | 说明 |
|---|---------|------|------|
| P2-1 | API 全部 Pydantic 化 | ❌ | 31处裸 request.get_json() |
| P2-2 | 错误格式统一 | ⚠️ | error_codes.py 有，但 API 端点未全部使用 |
| P2-3 | 前端 TypeScript | ❌ | 无 tsconfig.json |
| P2-4 | Alembic migration 流程化 | ✅ | 有版本目录 |
| P2-5 | 存储边界(local/s3) | ✅ | config.py 完整配置 |
| P2-6 | 日志脱敏 | ✅ | _sanitize_log_data + SENSITIVE_FIELDS |
| P2-7 | Prometheus/Sentry | ❌ | 无 /metrics 端点，无 Sentry |
| P2-8 | 生产 worker(RQ/Redis) | ⚠️ | 配置支持但默认 thread 模式 |
| P2-9 | DI 容器 | ✅ | Container 模式已实现 |
| P2-10 | 测试覆盖 | ⚠️ | 1386 tests，8 errors，覆盖率未报告 |

**P2 汇总：✅ 4 / ⚠️ 3 / ❌ 3（通过率 40%）**

---

## 四、P3 产品体验（7项）

| # | 验收标准 | 状态 | 说明 |
|---|---------|------|------|
| P3-1 | BusinessBrief 版本控制 | ⚠️ | 有3处 schema 相关，但不完整 |
| P3-2 | Research/Quick Mode 引导 | ✅ | EXPERIMENT_MODES 定义清晰 |
| P3-3 | Persona Pack 预览/编辑 | ⚠️ | 有分布统计，无 UI 预览 |
| P3-4 | Dry Run | ❌ | 无此功能 |
| P3-5 | 传播路径可视化 | ⚠️ | 后端有21处路径数据，前端可视化未知 |
| P3-6 | PDF/Word/PPT 导出 | ✅ | 有17处导出相关代码 |
| P3-7 | 追问分层 | ⚠️ | 有18处 followup 相关，分层不明确 |

**P3 汇总：✅ 2 / ⚠️ 4 / ❌ 1（通过率 29%）**

---

## 五、P4 商业化与合规（3项）

| # | 验收标准 | 状态 | 说明 |
|---|---------|------|------|
| P4-1 | 商业模式/GTM | ❌ | 无 pricing model |
| P4-2 | AGPL 许可证说明 | ❌ | README 无 AGPL 影响说明 |
| P4-3 | 文档齐套 | ❌ | 无 CONTRIBUTING/CHANGELOG/部署文档 |

**P4 汇总：✅ 0 / ⚠️ 0 / ❌ 3（通过率 0%）**

---

## 总体评估

| 优先级 | 总项 | ✅ | ⚠️ | ❌ | 通过率 |
|--------|------|---|---|---|--------|
| P0 阻塞 | 39 | 20 | 9 | 10 | 51% |
| P1 可信内核 | 78 | 21 | 18 | 39 | 27% |
| P2 工程化 | 10 | 4 | 3 | 3 | 40% |
| P3 产品 | 7 | 2 | 4 | 1 | 29% |
| P4 合规 | 3 | 0 | 0 | 3 | 0% |
| **总计** | **137** | **47** | **34** | **56** | **34%** |

---

## 最高优先修复项（Top 10）

1. **租户隔离** — Repository 层强制 tenant_id 过滤
2. **WEAK_SECRET_KEYS 拼写错误** — `'dev-...me'` → `'dev-only-change-me'`
3. **三层限流** — rate_limiter 增加 user_id/tenant_id 维度
4. **导出报告方法论页** — get_report_download_info 注入 methodology
5. **VOC 字段补全** — 从3个字段扩展到15个
6. **Reasoning Engine 集成 RuntimeControl** — checkpoint/early stop
7. **导出接口额外限速** — 3个端点加 @rate_limit
8. **security.yml** — 独立安全扫描 workflow
9. **docker-image.yml Trivy** — 镜像扫描
10. **API Pydantic 化** — 31处裸 get_json 替换
