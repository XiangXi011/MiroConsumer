# P0-1: RQ 队列真实接入 Redis/RQ

## 目标
将 `backend/app/services/application/rq_queue.py` 从空壳实现改为真实的 Redis/RQ 集成，使 `QUEUE_BACKEND=rq` 时任务能真正进入 Redis 队列并被 worker 消费。

## 当前状态（空壳代码）
```python
def enqueue(self, trace_id: str, fn: Callable, *args: Any, **kwargs: Any) -> str:
    logger.info("RQQueueBackend.enqueue not yet implemented", extra={"trace_id": trace_id})
    self._submitted[trace_id] = {"status": PENDING}
    return trace_id
```
所有方法（enqueue/get_status/cancel）都只操作内存字典 `self._submitted`。

## 需要改动的文件

### 1. `backend/app/services/application/rq_queue.py`（主改动）
- 引入 `redis` 和 `rq` 库
- `__init__` 接受 `redis_url`，创建 `Redis` 连接和 `Queue` 对象
- `enqueue()`: 使用 `queue.enqueue(fn, *args, **kwargs, job_id=trace_id)` 提交真实 RQ job
- `get_status()`: 从 RQ `Job.fetch(trace_id, connection=redis)` 查询状态，映射到内部状态（PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED）
- `cancel()`: 获取 RQ job 并调用 `job.cancel()`
- 保留 `self._submitted` 作为 fallback（当 Redis 不可用时降级到内存）
- 添加连接健康检查：`__init__` 时 ping Redis，连接失败抛出明确错误

### 2. `backend/app/services/application/queue_app_service.py`
- 在 `list_dead_letters()` 中添加 `backend == "rq"` 分支
- RQ 的 dead-letter 可以从 FailedJobRegistry 获取

### 3. `backend/pyproject.toml` 和 `backend/requirements.txt`
- 添加 `redis>=5.0.0` 和 `rq>=1.16.0`

### 4. `backend/tests/test_rq_queue.py`（新增）
- Mock `redis.Redis` 和 `rq.Queue`
- 测试 enqueue 调用 queue.enqueue
- 测试 get_status 从 RQ job 查询并映射状态
- 测试 cancel 调用 job.cancel
- 测试无效 redis_url 时抛出 ConnectionError
- 测试 Redis 不可用时降级到内存模式

## 不要做什么
- 不修改 `task_executor.py` 的抽象接口
- 不修改 `worker.py` 的整体结构（rq worker 通过 `rq worker` CLI 命令运行）
- 不修改 thread/sqlite 后端的逻辑
- 不改变 API 响应 schema
- 不在生产环境使用内存 fallback

## 验收标准
1. `git grep "RQQueueBackend.enqueue not yet implemented" -- backend` → 无结果
2. `git grep "not yet implemented" -- backend/app/services/application/rq_queue.py` → 无结果
3. `cd backend && python -m pytest tests/test_rq_queue.py tests/test_auth.py -v` → 全部通过
4. enqueue/get_status/cancel 都通过 Redis 操作而非内存字典

## 环境
- Python: `/Users/xiangdong/.hermes/hermes-agent/venv/bin/python`
- 工作目录: `/Users/xiangdong/MiroConsumer-phase5`
- 分支: `phase7/gatekeeper-comprehensive-fixes`
- 测试命令: `cd backend && /Users/xiangdong/.hermes/hermes-agent/venv/bin/python -m pytest tests/test_rq_queue.py -v`

## 参考
- 现有 sqlite 后端实现: `backend/app/services/application/sqlite_queue.py`
- 任务状态定义: `backend/app/services/application/task_executor.py`（PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED）
- Config: `QUEUE_BACKEND` 默认 "thread"，rq 时需要 `REDIS_URL`
