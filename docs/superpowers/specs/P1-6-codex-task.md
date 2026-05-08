# P1-6: 增加数据库外键和高频查询索引

## 目标
为 `simulation_id`、`project_id`、`run_id`、`tenant_id`、`status`、`created_at` 等高频查询字段增加索引。

## 当前状态
`backend/app/repositories/sqlalchemy.py` 的表定义中缺少外键和常用查询字段的显式索引。

## 要求

### 必须做
1. 在 `backend/alembic/versions/` 下新增独立迁移文件
2. 为以下字段添加 B-tree 索引：
   - `simulations.project_id`
   - `simulations.tenant_id`
   - `runs.simulation_id`
   - `rounds.run_id`
   - `consumer_states.simulation_id`
   - `reports.simulation_id`
   - `messages.round_id`
   - 各表的 `status` 字段
   - 各表的 `created_at` 字段
3. 迁移文件可独立升级和回滚

### 不要做
- 不重写整个 persistence model
- 不添加 GIN 索引（留到后续优化）
- 不改变表结构

## 验收标准
1. 新迁移文件存在且命名规范
2. 迁移可正常 upgrade
3. 索引在数据库中可见

## 环境
- 工作目录: `/Users/xiangdong/MiroConsumer-phase5`
- 参考: `backend/alembic/versions/20260429_0001_7a1_initial_20_tables.py`
- 迁移命令: `cd backend && /Users/xiangdong/.hermes/hermes-agent/venv/bin/python -m alembic upgrade head`
