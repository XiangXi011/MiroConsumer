# P1-1: 补齐开发 docker-compose 基础设施

## 目标
修改 `docker-compose.yml`，使其能通过一条命令启动完整的开发环境（backend + frontend + postgres + redis + minio）。

## 当前状态
`docker-compose.yml` 只有 12 行，仅定义了 `miroconsumer` 单服务。

## 要求

### 必须做
1. 参考 `docker-compose.prod.yml` 的服务定义，在 `docker-compose.yml` 中添加 postgres、redis、minio 服务
2. 保留开发友好的配置：
   - backend 使用 `Dockerfile`（开发合一镜像），端口 5001
   - frontend 端口 3000
   - postgres 端口 5432（方便本地直连调试）
   - redis 端口 6379
   - minio 端口 9000/9001
3. 添加 healthcheck（postgres 必须，redis 建议）
4. backend 的环境变量引用 postgres/redis/minio 服务名
5. volumes 持久化 postgres、redis、minio 数据
6. backend 通过 depends_on 等待 postgres 和 redis 就绪

### 不要做什么
- 不修改 `docker-compose.prod.yml`
- 不把生产密钥硬编码到 compose（使用 `${VAR:-default}` 模式）
- 不改变现有 .env 文件结构

## 验收标准
1. `docker-compose config` 无报错
2. 服务定义包含 backend、frontend、postgres、redis、minio
3. postgres 有 healthcheck
4. README 或 docs 中有启动说明

## 环境
- 工作目录: `/Users/xiangdong/MiroConsumer-phase5`
- 参考文件: `docker-compose.prod.yml`
