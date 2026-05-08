# P0-3: 认证信息迁移到共享持久存储

## 目标
将 `backend/app/auth/middleware.py` 中的内存字典 `_api_keys` 和 `_users` 替换为可持久化的存储后端，使认证状态在服务重启后不丢失、多实例可共享。

## 当前状态
- `backend/app/auth/middleware.py` 使用 `_api_keys = {}` 和 `_users = {}` 内存字典
- `register_user()` 和 `register_api_key()` 直接写内存
- `routes.py` 也有自己的 `_users_db = {}` 和 `_api_keys_db = {}`
- 项目已有 Repository 模式（`backend/app/repositories/`），支持 filesystem/sqlalchemy/postgresql

## 要求

### 必须做
1. 新增 `backend/app/auth/repository.py`，定义 `AuthRepository` 抽象接口：
   - `save_user(user: User) -> None`
   - `get_user(user_id: str) -> Optional[User]`
   - `save_api_key(api_key: APIKey) -> None`
   - `get_api_key_by_id(key_id: str) -> Optional[APIKey]`
   - `get_api_keys_by_user(user_id: str) -> List[APIKey]`
   - `delete_api_key(key_id: str) -> bool`
   - `clear_all() -> None`（仅测试用）

2. 实现两个后端：
   - `MemoryAuthRepository`：内存字典实现，用于测试 fallback
   - `SqlAlchemyAuthRepository`：PostgreSQL 实现，使用 SQLAlchemy Core（参考 `repositories/sqlalchemy.py` 的 Table 定义风格）

3. 在 `middleware.py` 中：
   - 移除全局 `_api_keys` 和 `_users` 字典
   - `init_auth(app)` 接受可选 `auth_repository` 参数
   - 认证逻辑通过 repository 查询而非内存字典
   - `register_user()` 和 `register_api_key()` 委托给 repository
   - 无 repository 时 fallback 到 MemoryAuthRepository

4. 在 `routes.py` 中：
   - 移除 `_users_db` 和 `_api_keys_db`
   - 使用 middleware 提供的 repository

5. 新增 Alembic 迁移文件：
   - `auth_users` 表：user_id(PK), username, email, role, tenant_id, workspace_id, is_active, created_at
   - `auth_api_keys` 表：key_id(PK), key_hash(bcrypt), user_id(FK), tenant_id, scopes(JSON), is_active, created_at, expires_at
   - 为 user_id, tenant_id, key_hash 添加索引

6. 测试：
   - 新增 `tests/test_auth_repository.py`
   - 测试 MemoryAuthRepository 的 CRUD
   - 测试 SqlAlchemyAuthRepository 的 CRUD（用 SQLite in-memory）
   - 测试服务重启后认证状态保持（模拟：创建用户 → 换 repository 实例 → 验证仍可查到）
   - 现有 `tests/test_auth.py` 26 个测试必须全部通过

### 不要做
- 不改变 RBAC 权限模型
- 不改变 JWT 生成/验证逻辑
- 不改变 API 响应格式
- 不引入新的 ORM 框架（用 SQLAlchemy Core Table 风格）
- 不在 routes.py 中直接操作数据库

## 参考代码
- Repository 模式参考：`backend/app/repositories/sqlalchemy.py`（Table 定义、_shared_columns）
- Repository 工厂参考：`backend/app/repositories/factory.py`
- Alembic 迁移参考：`backend/alembic/versions/20260429_0001_7a1_initial_20_tables.py`
- 现有认证模型：`backend/app/auth/models.py`（User, APIKey dataclass）
- 现有认证中间件：`backend/app/auth/middleware.py`
- 现有认证路由：`backend/app/auth/routes.py`

## 验收标准
1. `git grep "_api_keys = {}" -- backend/app/auth/` 无结果
2. `git grep "_users = {}" -- backend/app/auth/` 无结果
3. `python -m pytest tests/test_auth.py tests/test_auth_repository.py -v` 全部通过
4. MemoryAuthRepository 作为默认 fallback 可正常工作
5. SqlAlchemyAuthRepository 用 SQLite in-memory 测试通过

## 环境
- Python: 使用 `/Users/xiangdong/.hermes/hermes-agent/venv/bin/python`
- 工作目录: `/Users/xiangdong/MiroConsumer-phase5`
- 分支: `phase7/gatekeeper-comprehensive-fixes`
- 测试命令: `cd backend && /Users/xiangdong/.hermes/hermes-agent/venv/bin/python -m pytest tests/test_auth.py tests/test_auth_repository.py -v`
