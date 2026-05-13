下面是一份可以直接交给 Codex 执行的 **MiroConsumer 修复 SPEC v1.0**。目标是：**修完后让项目从当前约 7.0 分提升到 8.0+，并且能够经得起第二轮真实代码审计。**

---

# MiroConsumer 修复 SPEC v1.0

**目标分支**：`phase7/gatekeeper-comprehensive-fixes`
**目标评分**：≥ 8.0 / 10
**修复策略**：优先修真实 P0/P1 问题，纠正报告中的旧路径/误判项，避免无效大改。

## 0. 背景与证据基准

本 SPEC 基于两类材料制定：

1. 项目真实文档与当前代码。
2. 已上传的《MiroConsumer 全方位技术评审综合报告》。该报告提出了 23 个维度、综合 7.51/10、条件性通过、P0 安全问题必须先修等结论。

项目 README/中文 README 对产品定位、BusinessBrief、消费者画像、可见性图谱、Round 0 / Round 1-N、VOC 报告、证据验证、置信度评分、Benchmark Replay 等能力已有明确描述，可作为产品与架构基线。 

PRD 明确了当前产品不是静态 persona 打分，而是面向“初见反应 → 群体传播 → 态度分化 → 误读放大 → 报告归因”的消费者传播仿真工作流，并引用 Rogers、Katz & Lazarsfeld、Granovetter 等理论，同时声明为工程近似而非严格学术复现。

安全修复必须参考 OWASP API Security Top 10：当前最相关的是 API2 Broken Authentication、API1 Broken Object Level Authorization、API4 Unrestricted Resource Consumption、API5 Broken Function Level Authorization。OWASP 明确将弱认证、弱密钥、未验证 token、缺少暴力破解防护等列为认证风险，并建议对认证端点实施比普通 API 更严格的限流与防暴力破解机制。([OWASP Foundation][1])

---

# 1. 总体修复目标

## 1.1 最终目标

修复完成后，项目必须达到以下状态：

| 维度      |      当前判断 | 修复后目标 |
| ------- | --------: | ----: |
| 安全性     |   6.0-6.5 | ≥ 8.5 |
| API 契约  |   7.0-7.5 | ≥ 8.0 |
| CI/CD   |       7.0 | ≥ 8.0 |
| 测试质量    |       7.5 | ≥ 8.2 |
| 文档完整性   |       7.0 | ≥ 7.8 |
| 可观测性    |       6.5 | ≥ 7.5 |
| 前端流程完整度 |       7.0 | ≥ 8.0 |
| 综合评分    | 约 7.0-7.5 | ≥ 8.0 |

## 1.2 不做的事情

本轮不是重构整个项目，不做以下事情：

1. 不把项目整体迁移到 FastAPI。
2. 不强制完成全量数据库化替换。
3. 不重写消费者仿真核心。
4. 不按报告里的旧路径盲改，例如 `backend/src/...`。
5. 不把已存在的 JSON/CSV/manifest 导出当成“完全没有导出”。
6. 不把 Repository 层误判为“全是桩代码”后大规模推倒重写。

---

# 2. 当前报告中需要纠正的误判项

Codex 执行前必须先理解：原报告部分结论是对的，但部分证据路径过期。

## 2.1 路径纠正

当前项目实际路径是：

```text
backend/app/...
frontend/src/...
.github/workflows/...
```

不要按以下旧路径修：

```text
backend/src/auth/routes.py
backend/src/config.py
backend/src/services/phase6j.py
backend/src/repositories/simulation_repository.py
```

实际认证路由在：

```text
backend/app/auth/routes.py
```

登录接口当前确实只基于 `user_id` 查用户并签发 token，没有密码验证。

JWT 初始化逻辑在：

```text
backend/app/auth/middleware.py
```

这里仍存在 `app.config.get('SECRET_KEY', 'dev-secret')` 风险 fallback。

主配置在：

```text
backend/app/config.py
```

其中已经存在 `WEAK_SECRET_KEYS`、生产环境 SECRET_KEY 校验等逻辑，但认证中间件仍需闭环修复。

## 2.2 Repository 误判纠正

报告说 Repository 层“大量返回 `[]/None` 桩代码”，这一点不能照抄。当前真实情况是：

* Repository 抽象定义在 `backend/app/repositories/__init__.py`。
* 文件系统实现位于 `backend/app/repositories/filesystem.py`。
* 当前实现是“filesystem-backed thin adapter”，并不是简单 TODO 桩代码。 

本轮正确修复方向：

```text
不是：实现所谓“空 Repository 桩代码”
而是：明确 Repository 当前是文件系统适配器，补测试、补文档、补生产限制说明；只修发现的真实 bug。
```

## 2.3 Phase6J 误判纠正

报告中提到 `replay_score = 0.5` 占位符，但当前可见的 Phase6J 与 Benchmark Replay 代码已有实际 gate 和 replay 计算逻辑，不应直接按“占位符”修。 

本轮要求：

```text
先搜索确认是否仍存在 replay_score = 0.5。
若不存在，不要制造重复实现。
若存在于其他文件，才按真实路径修复。
```

## 2.4 导出能力误判纠正

报告说“仅支持纯文本导出”不准确。当前 `export_simulation` 已支持：

```text
json
csv
manifest
```

正确问题是：

```text
已有基础机器可读导出，但缺少 PDF / Word / PPT 等业务汇报格式。
```

当前导出逻辑在 simulation API 中。

## 2.5 CI Trivy 误判纠正

报告说 Trivy “推送后扫描”不准确。当前 workflow 是先写 Trivy，再 Build and push；但问题在于 Trivy 扫描的镜像引用可能并不是当前 job 已构建出来的本地镜像，因此仍需要修。

Aqua Security 官方 Trivy Action 示例是：先 `docker build -t <image>:${{ github.sha }}`，再对这个 image-ref 执行 Trivy 扫描。([GitHub][2])

---

# 3. P0 修复：安全闭环

P0 必须全部完成，否则不得声称 8 分以上。

---

## P0-1：修复无密码登录

### 当前问题

`backend/app/auth/routes.py` 的 `/api/auth/login` 当前逻辑是：

```python
user_id = data.get('user_id')
user = get_auth_repository().get_user(user_id)

if user:
    token = create_jwt_token(user)
```

这等于知道 `user_id` 就能登录。

### 目标

登录必须验证真实凭证，不允许仅凭 `user_id` 换取 JWT。

### 具体实现要求

修改：

```text
backend/app/auth/models.py
backend/app/auth/routes.py
backend/app/auth/repository.py
backend/app/auth/middleware.py
相关 tests
```

实现：

```python
User:
  password_hash: str
  password_changed_at: Optional[float]
  failed_login_count: int
  locked_until: Optional[float]
```

注册接口 `/api/auth/register`：

```json
{
  "username": "demo",
  "email": "demo@example.com",
  "password": "StrongPassword123!",
  "role": "researcher",
  "tenant_id": "default"
}
```

要求：

1. `password` 必填。
2. 密码长度 ≥ 10。
3. 至少包含字母与数字。
4. 密码只保存 hash，不允许保存明文。
5. 使用已有依赖 `bcrypt` 或 Werkzeug 安全哈希。
6. 返回体不得包含 password 或 password_hash。

登录接口 `/api/auth/login`：

推荐支持：

```json
{
  "username": "demo",
  "password": "StrongPassword123!"
}
```

或：

```json
{
  "email": "demo@example.com",
  "password": "StrongPassword123!"
}
```

兼容性要求：

```text
可以暂时兼容 user_id + password；
禁止 user_id-only 登录。
```

错误响应：

```json
{
  "success": false,
  "error": "AUTH_FAILED",
  "message": "Invalid credentials"
}
```

不得区分：

```text
用户不存在
密码错误
账号禁用
```

防止账号枚举。

### 验收标准

新增测试：

```text
backend/tests/auth/test_password_login.py
```

必须覆盖：

1. 注册时 password 必填。
2. 注册后 repository 中不保存明文密码。
3. 正确用户名 + 正确密码可以登录。
4. 正确 user_id 但无 password 不能登录。
5. 正确 user_id + 错误 password 不能登录。
6. 不存在用户与错误密码返回相同错误结构。
7. 禁用用户不能登录。
8. token payload 不包含 password_hash。

---

## P0-2：修复 JWT 默认密钥 fallback

### 当前问题

`init_auth()` 中仍存在：

```python
_jwt_secret = app.config.get('SECRET_KEY', 'dev-secret')
```

这会让认证安全依赖其他地方的启动校验兜底，不够闭环。

### 目标

任何非测试环境下：

```text
JWT secret 不得为空
不得使用弱值
不得有 dev-secret fallback
长度必须 >= 32
```

### 具体实现要求

在 `backend/app/auth/middleware.py` 中：

```python
_jwt_secret = app.config.get("JWT_SECRET_KEY") or app.config.get("SECRET_KEY")
```

然后强校验：

```python
if not _jwt_secret:
    raise RuntimeError("JWT secret is required")
if _jwt_secret in WEAK_SECRET_KEYS:
    raise RuntimeError("JWT secret must not use a weak/default value")
if len(_jwt_secret) < 32:
    raise RuntimeError("JWT secret must be >= 32 characters")
```

测试环境允许专用测试密钥：

```text
TESTING=true
SECRET_KEY=test-secret-key-that-is-long-enough-32
```

JWT payload 要求：

```json
{
  "sub": "user_xxx",
  "user_id": "user_xxx",
  "role": "researcher",
  "tenant_id": "tenant_a",
  "workspace_id": "ws_tenant_a",
  "iat": 1710000000,
  "exp": 1710003600,
  "jti": "jwt_xxx"
}
```

### 验收标准

新增测试：

```text
backend/tests/auth/test_jwt_secret_validation.py
```

必须覆盖：

1. 无 SECRET_KEY 启动失败。
2. `dev-secret` 启动失败。
3. 长度不足启动失败。
4. 合法 secret 启动成功。
5. 过期 token 被拒绝。
6. 伪造 token 被拒绝。
7. `alg=none` token 被拒绝。

---

## P0-3：限流器迁移 Redis，保留开发态 memory fallback

### 当前问题

当前限流器使用进程内：

```python
_rate_limit_store = defaultdict(list)
```

这在多进程、多节点部署时无法共享。

OWASP 建议认证端点必须有比普通 API 更严格的限流、防暴力破解与账号锁定机制。([OWASP Foundation][1])

### 目标

生产环境限流必须使用 Redis。

### 具体实现要求

新增或改造：

```text
backend/app/middleware/rate_limiter.py
backend/app/config.py
backend/tests/security/test_rate_limiter.py
```

配置：

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_BACKEND=redis
REDIS_URL=redis://redis:6379/0
RATE_LIMIT_PER_MINUTE=60
AUTH_RATE_LIMIT_PER_MINUTE=5
EXPORT_RATE_LIMIT_PER_MINUTE=10
```

行为：

| 场景     | 限流 key              |               默认阈值 |
| ------ | ------------------- | -----------------: |
| 普通 API | ip + user + tenant  |             60/min |
| 登录接口   | ip + username/email |              5/min |
| 导出接口   | ip + user           |             10/min |
| LLM 调用 | tenant + user       | 按 LLM_BUDGET_LIMIT |

Redis 实现建议：

```text
固定窗口或滑动窗口均可；
必须使用 Redis 原子操作；
必须设置 TTL；
不得无限增长 key。
```

生产环境约束：

```text
RATE_LIMIT_ENABLED=true 且 RATE_LIMIT_BACKEND=redis 时，REDIS_URL 必填；
生产环境不得 silently fallback 到 memory。
```

开发/测试环境允许：

```text
RATE_LIMIT_BACKEND=memory
```

但必须在日志中明确：

```text
Memory rate limiter is for development/testing only.
```

### 验收标准

测试必须覆盖：

1. 登录连续失败超过阈值返回 429。
2. 普通 API 超限返回 429。
3. 导出接口超限返回 429。
4. Redis key 有 TTL。
5. 生产环境开启 Redis backend 但没有 REDIS_URL 时启动失败。
6. memory backend 仅测试/开发可用。
7. 多个用户/tenant 的 key 互不污染。

---

## P0-4：租户隔离与对象级授权

### 当前问题

项目已有部分租户过滤，但不是系统化 Object Level Authorization。OWASP API Top 10 将对象级授权缺失列为 API1:2023，因为 API 常通过对象 ID 暴露数据访问面。([OWASP Foundation][3])

### 目标

任何带以下对象 ID 的接口，都必须做对象级租户校验：

```text
project_id
simulation_id
report_id
benchmark_id
branch_id
api_key_id
user_id
```

### 具体实现要求

新增：

```text
backend/app/auth/tenant_guard.py
```

提供：

```python
class TenantGuard:
    @staticmethod
    def require_same_tenant(resource_tenant_id: str, current_user) -> None:
        ...

    @staticmethod
    def can_access_tenant(current_user, target_tenant_id: str) -> bool:
        ...

    @staticmethod
    def assert_project_access(project_id: str, current_user) -> Project:
        ...

    @staticmethod
    def assert_simulation_access(simulation_id: str, current_user) -> SimulationState:
        ...

    @staticmethod
    def assert_report_access(report_id: str, current_user) -> Report:
        ...
```

角色规则：

| 角色          | 权限                          |
| ----------- | --------------------------- |
| researcher  | 只能访问本 tenant 资源             |
| analyst     | 只能访问本 tenant 资源             |
| admin       | 只能管理本 tenant 用户与资源          |
| super_admin | 可跨 tenant，但必须显式记录 audit log |

注意：

```text
admin ≠ super_admin。
```

每个访问资源的 API 必须调用 TenantGuard，不能只靠 list 后过滤。

优先覆盖：

```text
backend/app/api/project*.py
backend/app/api/simulation.py
backend/app/api/report*.py
backend/app/api/consumer*.py
backend/app/auth/routes.py
```

### 验收标准

新增测试：

```text
backend/tests/security/test_tenant_isolation.py
```

必须覆盖：

1. tenant_a 用户不能读取 tenant_b project。
2. tenant_a 用户不能读取 tenant_b simulation。
3. tenant_a 用户不能导出 tenant_b report。
4. admin 不能跨 tenant。
5. super_admin 可以跨 tenant。
6. 跨 tenant 拒绝返回 403。
7. 被拒绝访问写入 audit log。

---

## P0-5：权限装饰器覆盖关键 API

### 目标

所有敏感 API 必须具备显式权限要求。

当前 `create_simulation` 已使用 `@require_permission('simulation.run')`，但 `prepare_simulation`、`get_prepare_status`、`get_simulation`、`list_simulations` 等还需要逐项确认。

### 权限矩阵

| API 类型        | 权限                   |
| ------------- | -------------------- |
| 创建仿真          | `simulation.run`     |
| prepare 仿真    | `simulation.run`     |
| start/stop 仿真 | `simulation.run`     |
| 查看仿真          | `simulation.read`    |
| 查看历史          | `simulation.read`    |
| 导出结果          | `report.export`      |
| 创建报告          | `report.generate`    |
| 查看报告          | `report.read`        |
| API Key 创建    | `admin.manage_users` |
| 用户管理          | `admin.manage_users` |
| 成本看板          | `admin.manage_users` |

### 验收标准

新增测试：

```text
backend/tests/security/test_permissions.py
```

必须覆盖：

1. 无 token 访问 API 返回 401。
2. 无权限角色访问敏感 API 返回 403。
3. 有权限角色访问成功。
4. API key scope 不足返回 403。
5. 权限错误响应格式统一。

---

# 4. P1 修复：CI/CD、前端主流程、文档、审计日志

---

## P1-1：修复 Docker + Trivy workflow

### 当前问题

`.github/workflows/docker-image.yml` 中 Trivy 扫描发生在 Build and push 步骤前，但扫描的 image-ref 可能不是本 job 本地构建出来的镜像。

官方 Trivy Action 示例要求先构建镜像，再扫描这个镜像。([GitHub][2])

### 目标

只有通过 Trivy 高危/严重漏洞扫描的镜像才能 push。

### 推荐实现

调整 workflow：

```yaml
- name: Build image locally
  run: |
    docker build -t ghcr.io/${{ github.repository_owner }}/miroconsumer:${{ github.sha }} .

- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@v0.36.0
  with:
    image-ref: ghcr.io/${{ github.repository_owner }}/miroconsumer:${{ github.sha }}
    format: table
    exit-code: "1"
    vuln-type: "os,library"
    severity: "CRITICAL,HIGH"

- name: Push image
  if: success()
  run: |
    docker push ghcr.io/${{ github.repository_owner }}/miroconsumer:${{ github.sha }}
```

如果继续使用 buildx：

```text
必须保证 scan 的 image 是本次 build 产物；
可以使用 load: true 或先 build 到本地，再扫描，再 push。
```

### 验收标准

1. PR 上能跑 Trivy fs/repo scan。
2. tag 或 workflow_dispatch 时，镜像先 build，后 scan，最后 push。
3. Trivy 发现 HIGH/CRITICAL 时 workflow 失败。
4. 不允许 `continue-on-error: true` 掩盖安全扫描失败。
5. workflow 注释解释为什么 scan before push。

---

## P1-2：补充前端主流程导航

### 当前问题

`frontend/src/views/Process.vue` 中：

```js
const goToNextStep = () => {
  // TODO: 进入环境搭建步骤
  alert('环境搭建功能开发中...')
}
```

确实未完成。

但当前 router 中 `/process/:projectId` 实际指向 `MainView.vue`，而不是 `Process.vue`，因此 Codex 必须先确认 `Process.vue` 是否仍被实际引用。

### 目标

用户完成图谱构建后，点击“下一步”必须进入环境搭建/仿真准备步骤，不得弹出“开发中”。

### 具体实现要求

Codex 先执行：

```bash
grep -R "Process.vue\|goToNextStep\|进入环境搭建" frontend/src -n
```

分两种情况：

#### 情况 A：`Process.vue` 已废弃

1. 删除或归档 `Process.vue`。
2. 确认 `MainView.vue` 中主流程完整。
3. 删除无效 route 或 stale component。
4. 补充注释说明旧 Process 页已被 MainView 替代。

#### 情况 B：`Process.vue` 仍在使用

实现 `goToNextStep`：

```js
const goToNextStep = async () => {
  if (!projectData.value?.project_id) return
  if (!projectData.value?.graph_id) {
    error.value = '图谱尚未构建完成'
    return
  }

  // 创建或获取仿真
  const response = await createSimulation({
    project_id: projectData.value.project_id,
    graph_id: projectData.value.graph_id
  })

  if (response.success) {
    router.push({
      name: 'Simulation',
      params: { simulationId: response.data.simulation_id }
    })
  } else {
    error.value = response.error || '创建仿真失败'
  }
}
```

### 验收标准

前端测试必须覆盖：

1. 图谱未完成时按钮不可点击或提示合理。
2. 图谱完成后点击下一步调用 create simulation。
3. 创建成功后跳转到 `Simulation` route。
4. 创建失败时展示错误，不 alert。
5. 不再出现“环境搭建功能开发中”。

---

## P1-3：补充安全审计日志

### 目标

关键安全事件必须可追溯。

新增：

```text
backend/app/security/audit_log.py
```

事件结构：

```json
{
  "event_id": "audit_xxx",
  "event_type": "auth.login_failed",
  "actor_user_id": "user_xxx",
  "actor_tenant_id": "tenant_a",
  "target_type": "simulation",
  "target_id": "sim_xxx",
  "ip": "127.0.0.1",
  "user_agent": "...",
  "success": false,
  "reason": "invalid_credentials",
  "created_at": "2026-05-11T00:00:00Z"
}
```

必须记录：

| 事件                | event_type               |
| ----------------- | ------------------------ |
| 登录成功              | `auth.login_success`     |
| 登录失败              | `auth.login_failed`      |
| 登出                | `auth.logout`            |
| token 拒绝          | `auth.token_rejected`    |
| API key 创建        | `auth.api_key_created`   |
| 权限拒绝              | `auth.permission_denied` |
| 租户拒绝              | `auth.tenant_denied`     |
| 报告导出              | `report.exported`        |
| 仿真启动              | `simulation.started`     |
| 仿真停止              | `simulation.stopped`     |
| benchmark replay  | `benchmark.replayed`     |
| super_admin 跨租户访问 | `tenant.cross_access`    |

存储本轮最低要求：

```text
文件 JSONL 或现有 repository 均可；
必须有测试；
不得记录 password、token、api_key 明文。
```

### 验收标准

1. 登录失败写 audit。
2. 租户拒绝写 audit。
3. API key 创建写 audit，但不写 raw key。
4. report export 写 audit。
5. audit log 不包含 password/token/api_key 明文。
6. 测试能读取 audit log 并断言字段。

---

## P1-4：健康检查分级

### 目标

提供：

```text
/health
/ready
```

`/health`：

```json
{
  "status": "ok"
}
```

不得泄露：

```text
模型名
版本号
密钥
内部路径
平台信息
```

`/ready`：

检查：

```text
Config
Redis
DB，如果启用
S3/MinIO，如果启用
Zep API Key 是否存在，但不外呼或泄露
LLM API Key 是否存在，但不外呼或泄露
```

返回：

```json
{
  "status": "ready",
  "checks": {
    "redis": "ok",
    "db": "ok",
    "storage": "ok",
    "config": "ok"
  }
}
```

失败返回 503。

### 验收标准

1. `/health` 永远不泄露敏感信息。
2. `/ready` 缺 Redis 时返回 503。
3. `/ready` 缺生产 SECRET_KEY 时返回 503 或启动失败。
4. 测试覆盖所有 checks。

---

## P1-5：补全文档

### 当前问题

`CONTRIBUTING.md` 内容很短，只覆盖基础环境、代码标准、PR 流程。
`CHANGELOG.md` 只有一个版本。
`ACCEPTANCE_REPORT.md` 大量任务仍是“待执行/未开始”。

### 必须新增或完善

```text
CONTRIBUTING.md
CHANGELOG.md
DEPLOYMENT.md
SECURITY.md
ACCEPTANCE_REPORT.md
docs/architecture.md
docs/auth-and-tenant-isolation.md
docs/operations.md
```

### DEPLOYMENT.md 必须包含

1. 本地开发启动。
2. Docker Compose 启动。
3. 生产环境变量表。
4. SECRET_KEY / JWT_SECRET_KEY 生成方式。
5. Redis 必填场景。
6. DB_URL 配置。
7. MinIO/S3 配置。
8. Gunicorn 启动示例。
9. 反向代理注意事项。
10. 健康检查与 readiness。
11. 数据备份与恢复。
12. 常见故障排查。

### SECURITY.md 必须包含

1. 密码策略。
2. JWT 策略。
3. API Key 使用边界。
4. 租户隔离模型。
5. 权限模型。
6. 限流策略。
7. 审计日志。
8. 安全测试命令。
9. 漏洞上报流程。

### ACCEPTANCE_REPORT.md 必须更新

将本轮修复项逐项写入：

```text
P0-1 password login
P0-2 JWT secret
P0-3 Redis rate limit
P0-4 tenant isolation
P0-5 permissions
P1-1 CI Trivy
P1-2 frontend navigation
P1-3 audit log
P1-4 health/readiness
P1-5 docs
```

每项包含：

```text
状态
改动文件
测试文件
测试结果
验收结论
未完成风险
```

---

# 5. P1/P2：工程质量修复

---

## P1-6：统一错误响应格式

### 当前问题

项目已有部分统一错误格式，但各 API 仍混杂：

```json
{"error": "..."}
{"success": false, "error": "..."}
{"error": {"code": "..."}}
```

### 目标

统一为：

```json
{
  "success": false,
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "Authentication required",
    "details": {},
    "request_id": "req_xxx",
    "timestamp": "2026-05-11T00:00:00Z"
  }
}
```

### 兼容策略

短期可以保留旧字段，但新字段必须存在：

```json
{
  "success": false,
  "error": "AUTH_REQUIRED",
  "message": "Authentication required",
  "request_id": "req_xxx",
  "timestamp": "..."
}
```

### 验收标准

1. 401/403/404/409/422/429/500 都有 request_id。
2. validation error 返回 400 或 422。
3. tenant mismatch 返回 403。
4. rate limit 返回 429。
5. 测试断言响应结构。

---

## P1-7：OpenAPI 文档最小可用

### 目标

提供：

```text
/api/openapi.json
/api/docs
```

当前 middleware 已把 `/api/openapi.json`、`/api/docs` 列为公开路径，但必须确认真实可用。

### 最小要求

OpenAPI 至少覆盖：

```text
auth register/login/me/api-keys
project create/list/get
simulation create/prepare/status/start/get/list/export
report create/get/export
consumer summary
benchmark register/replay
```

### 验收标准

1. `/api/openapi.json` 返回合法 JSON。
2. `/api/docs` 可打开。
3. CI 中增加 OpenAPI schema smoke test。
4. 文档中的认证方式包含 Bearer JWT 与 X-API-Key。

---

## P2-1：导出能力增强，非本轮 8 分硬门槛

当前已有 JSON/CSV/manifest 导出。

本轮目标只要求文档修正：

```text
不要写“仅支持纯文本导出”；
写清楚已有 JSON/CSV/manifest；
PDF/Word/PPT 放入后续 roadmap。
```

可选增强：

```text
report export markdown
report export html
```

PDF/Word/PPT 不作为本轮 8 分硬门槛。

---

## P2-2：Repository 与数据库化说明

当前 repository 是抽象 + filesystem-backed adapter。 

本轮不要求全量数据库化。

必须做：

1. 在 `docs/architecture.md` 写清楚当前 persistence 状态。
2. 标明生产风险：文件系统存储在多实例部署下需共享卷或对象存储。
3. 标明未来路线：SQLAlchemy Repository、Alembic、PostgreSQL。
4. 不要误删 filesystem repository。

可选做：

```text
增加 Repository contract tests，确保 filesystem 实现满足接口。
```

---

# 6. 测试 SPEC

## 6.1 必须新增测试文件

```text
backend/tests/auth/test_password_login.py
backend/tests/auth/test_jwt_secret_validation.py
backend/tests/security/test_rate_limiter.py
backend/tests/security/test_tenant_isolation.py
backend/tests/security/test_permissions.py
backend/tests/security/test_audit_log.py
backend/tests/api/test_error_response_contract.py
backend/tests/api/test_openapi_docs.py
backend/tests/ops/test_health_readiness.py
frontend/tests/navigation.test.js
```

## 6.2 必须保留现有测试

不得删除或跳过现有 golden tests：

```text
tests/e2e/test_consumer_concept_test_golden_flow.py
tests/e2e/test_consumer_golden_cases.py
tests/api/test_consumer_canonical_routes.py
tests/api/test_phase6a_project_type_contract.py
tests/api/test_consumer_society_runtime.py
```

`.github/workflows/ci.yml` 当前已有 backend、frontend、consumer-contract、consumer-smoke、security、benchmark 等 job。

## 6.3 命令验收

Codex 修复后必须跑：

```bash
cd backend
uv run --python 3.12 pytest --cov=app --cov-report=term-missing
```

```bash
cd frontend
npm ci
npm run build
npm test
```

```bash
pip install bandit pip-audit
bandit -r backend/app/ -ll --skip B101
pip-audit
```

Docker/Trivy：

```bash
docker build -t miroconsumer:test .
trivy image --severity HIGH,CRITICAL --exit-code 1 miroconsumer:test
```

## 6.4 覆盖率门槛

最低要求：

| 区域                      |   覆盖率 |
| ----------------------- | ----: |
| auth                    | ≥ 85% |
| middleware/rate_limiter | ≥ 85% |
| tenant_guard            | ≥ 90% |
| audit_log               | ≥ 80% |
| API contract tests      |  必须全绿 |
| 前端导航测试                  |  必须全绿 |

整体覆盖率不低于当前水平。

---

# 7. 评分提升门槛

修复完成后必须重新按以下表打分。

| 维度      |   权重 | 8 分验收条件                                             |
| ------- | ---: | --------------------------------------------------- |
| 安全性     | 0.10 | 无 user_id-only 登录；JWT 无弱 fallback；Redis 限流；租户隔离测试全绿 |
| 性能与可扩展性 | 0.07 | 内存限流迁 Redis；生产配置不 silent fallback                   |
| API 契约  | 0.06 | 权限装饰器、统一错误响应、OpenAPI 可用                             |
| 测试质量    | 0.06 | 新增安全/租户/权限/限流测试，CI 全绿                               |
| CI/CD   | 0.04 | Trivy 扫描本次构建镜像，scan before push                     |
| 文档完整性   | 0.03 | DEPLOYMENT/SECURITY/ARCH/ACCEPTANCE 更新              |
| 可观测性    | 0.04 | audit log + readiness checks                        |
| 业务流程 UX | 0.08 | 下一步流程不再 TODO/alert                                  |
| 代码质量    | 0.08 | 不引入大面积重复逻辑；TenantGuard/RateLimiter 抽象清晰             |

达到 8 分的最低门槛：

```text
P0 全部完成
P1-1 / P1-2 / P1-3 / P1-4 / P1-5 完成
所有新增测试通过
CI 全绿
ACCEPTANCE_REPORT.md 更新
```

---

# 8. Codex 执行顺序

## Phase A：证据确认

先执行：

```bash
git checkout phase7/gatekeeper-comprehensive-fixes
find backend/app -maxdepth 4 -type f | sort
find frontend/src -maxdepth 4 -type f | sort
grep -R "def login\|create_jwt_token\|_jwt_secret\|rate_limit\|defaultdict(list)" backend/app -n
grep -R "goToNextStep\|环境搭建功能开发中" frontend/src -n
grep -R "replay_score.*0.5\|Placeholder" backend/app -n
```

输出一份 `FIX_EVIDENCE.md`，记录：

```text
真实存在的问题
报告误判的问题
本轮实际修改计划
```

## Phase B：P0 安全修复

顺序：

```text
1. password login
2. JWT secret validation
3. Redis rate limiter
4. TenantGuard
5. permission decorators
6. security tests
```

## Phase C：P1 工程修复

顺序：

```text
1. Docker + Trivy workflow
2. frontend navigation
3. audit log
4. health/readiness
5. docs
6. OpenAPI / error response
```

## Phase D：回归与验收

最后更新：

```text
ACCEPTANCE_REPORT.md
CHANGELOG.md
FIX_EVIDENCE.md
```

并输出：

```text
TEST_RESULT.md
```

内容包含：

```text
后端测试命令与结果
前端测试命令与结果
安全扫描结果
Trivy 结果
未完成项
是否达到 8 分标准
```

---

# 9. 禁止事项

Codex 不得做以下事情：

1. 不得用 `AUTH_BYPASS_IN_TESTING` 掩盖生产认证问题。
2. 不得把 password 明文写入 User、日志、测试快照。
3. 不得把 raw API key 写入 audit log。
4. 不得把 `dev-secret` 换成另一个硬编码密钥。
5. 不得在生产环境 Redis 不可用时自动降级 memory rate limiter。
6. 不得删除现有 consumer golden tests。
7. 不得删除 BusinessBrief / consumer_test 主链路。
8. 不得为了测试通过降低权限检查。
9. 不得把所有 admin 变成跨租户 super_admin。
10. 不得按旧路径 `backend/src/...` 新建重复模块。

---

# 10. 最终交付物

Codex 修复完成后，仓库必须包含：

```text
FIX_EVIDENCE.md
TEST_RESULT.md
SECURITY.md
DEPLOYMENT.md
docs/architecture.md
docs/auth-and-tenant-isolation.md
docs/operations.md
更新后的 ACCEPTANCE_REPORT.md
更新后的 CHANGELOG.md
```

代码层必须包含：

```text
password-based login
strong JWT secret validation
Redis-backed rate limiter
TenantGuard
permission coverage
audit log
readiness checks
frontend navigation fix
CI Trivy fix
security tests
```

---

