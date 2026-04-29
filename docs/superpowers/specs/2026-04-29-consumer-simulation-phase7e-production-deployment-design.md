# MiroConsumer Phase 7E 生产部署规格

## 1. 文档状态

| 字段 | 内容 |
|---|---|
| 日期 | 2026-04-29 |
| 子阶段 | 7E |
| 子阶段名称 | 生产部署 |
| 上游依赖 | Phase 7A 交付的数据库配置；Phase 7B 交付的 worker 启动逻辑；Phase 7C 交付的 lock/conflict 行为；Phase 7D 交付的 env var 规范 |
| 下游依赖 | Phase 7F |
| 文档状态 | 审核基线 |

## 2. 依赖声明

### 2.1 输入依赖

- Phase 7A 交付的 `DB_URL` 配置规范与 database session 基础设施。
- Phase 7B 交付的 `backend/app/worker.py` 启动入口。
- Phase 7D 交付的环境变量清单（`LLM_BUDGET_LIMIT`、`MAX_AGENTS`、`MAX_ROUNDS` 等）。
- Phase 6F 至 Phase 6I 稳定 schema（只读引用，禁止修改）。

### 2.2 输出依赖

Phase 7F 依赖 7E 交付的 production compose 与 Dockerfile 进行集成验证与冒烟测试。

## 3. 交付物

### 3.1 Storage Backend

必须新增环境变量：

```env
STORAGE_BACKEND=local
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_REGION=us-east-1
```

切换规则固定为：

- `STORAGE_BACKEND=local`：使用本地 volume。
- `STORAGE_BACKEND=s3`：使用 S3 兼容存储。
- 其他值：启动失败。

本地存储路径固定为：

```text
backend/uploads
backend/data
```

### 3.2 Docker Image 一致性

必须修改以下文件：

```text
docker-compose.yml
.github/workflows/*
```

规则固定为：

- `docker-compose.yml` 禁止写死 `ghcr.io/666ghj/miroconsumer`。
- 镜像名必须来自环境变量 `MIROCONSUMER_IMAGE`。
- `.env.example` 必须包含：

```env
MIROCONSUMER_IMAGE=ghcr.io/xiangxi011/miroconsumer:latest
```

### 3.3 Production Dockerfiles

必须新增以下文件：

```text
Dockerfile.backend
Dockerfile.frontend
Dockerfile.worker
nginx.conf
docker-compose.prod.yml
```

容器职责固定为：

| container | 职责 |
|---|---|
| frontend | 运行 nginx，服务 Vite build 静态产物 |
| backend | 运行 gunicorn Flask API |
| worker | 运行 `backend/app/worker.py` |
| postgres | PostgreSQL |
| redis | Redis RQ |
| minio | S3 兼容对象存储 |

开发 `Dockerfile` 保留。生产部署必须使用 `docker-compose.prod.yml`。

### 3.4 Backend Server

生产 backend 必须使用 gunicorn。

启动命令固定为：

```bash
gunicorn "app:create_app()" --bind 0.0.0.0:5001 --workers 2 --threads 4 --timeout 300
```

### 3.5 Nginx 配置

`nginx.conf` 必须配置：

- 前端静态文件服务（Vite build 产物）。
- API 请求反向代理到 backend gunicorn（端口 5001）。
- 上传文件大小限制。
- 超时配置。

### 3.6 环境变量治理

`.env.example` 必须包含全部 26 个生产变量：

```env
LLM_API_KEY=
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=
DB_URL=
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_STATEMENT_TIMEOUT_SECONDS=30
QUEUE_BACKEND=thread
REDIS_URL=
QUEUE_RETRY_LIMIT=3
QUEUE_VISIBILITY_TIMEOUT_SECONDS=300
STORAGE_BACKEND=local
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_REGION=us-east-1
MAX_AGENTS=1000
MAX_ROUNDS=10
LLM_BUDGET_LIMIT=500
LLM_DEEP_REASONING_RATIO=0.1
ENABLE_DETERMINISTIC_FALLBACK=true
ENABLE_SOCIETY_MODE=false
ENABLE_GRAPH_MEMORY_WRITEBACK=false
MIROCONSUMER_IMAGE=ghcr.io/xiangxi011/miroconsumer:latest
```

`Config.validate()` 必须校验以下绑定：

- LLM 变量（`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_NAME`）。
- ZEP 变量（`ZEP_API_KEY`）。
- `DB_URL` scheme（空、`sqlite:///`、`postgresql+psycopg://`）。
- `QUEUE_BACKEND` 取值（`thread`、`sqlite`、`rq`）。
- `REDIS_URL` 与 `QUEUE_BACKEND=rq` 的绑定（`QUEUE_BACKEND=rq` 时 `REDIS_URL` 非空）。
- `STORAGE_BACKEND` 取值（`local`、`s3`）。
- S3 变量与 `STORAGE_BACKEND=s3` 的绑定（`STORAGE_BACKEND=s3` 时 S3 变量非空）。

## 4. 禁止范围

本子阶段禁止纳入以下工作：

- 修改 repository 表结构（归属 Phase 7A）。
- 实现队列逻辑（归属 Phase 7B）。
- 实现并发锁逻辑（归属 Phase 7C）。
- 实现成本预算控制（归属 Phase 7D）。
- 实现冒烟测试（归属 Phase 7F）。
- 修改 consumer API response schema。
- 新增消费者模拟内核或渠道规则。
- 删除开发 Dockerfile。

## 5. 退出条件

Phase 7E 退出必须同时满足：

1. `docker-compose.yml` 不再写死旧 GHCR 地址 `ghcr.io/666ghj/miroconsumer`。
2. 镜像名来自环境变量 `MIROCONSUMER_IMAGE`。
3. `Dockerfile.backend` 存在且基于生产基础镜像构建。
4. `Dockerfile.frontend` 存在且基于 nginx 基础镜像构建。
5. `Dockerfile.worker` 存在且基于 `backend` 镜像构建。
6. `nginx.conf` 存在且配置前端静态文件服务与 API 反向代理。
7. `docker-compose.prod.yml` 存在且包含 6 个服务定义（frontend、backend、worker、postgres、redis、minio）。
8. Backend 生产启动使用 gunicorn，命令参数固定为 `--bind 0.0.0.0:5001 --workers 2 --threads 4 --timeout 300`。
9. `.env.example` 包含全部 26 个生产环境变量。
10. `Config.validate()` 校验全部 7 类绑定规则。
11. 无效 `STORAGE_BACKEND` 值触发启动失败。
12. `STORAGE_BACKEND=s3` 时缺少 S3 变量触发启动失败。
13. `QUEUE_BACKEND=rq` 时缺少 `REDIS_URL` 触发启动失败。
14. `docker compose -f docker-compose.prod.yml config` 通过验证。
