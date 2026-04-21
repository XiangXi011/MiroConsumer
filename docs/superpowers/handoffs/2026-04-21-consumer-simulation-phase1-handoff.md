# Consumer Simulation Phase 1 交接文档

## 1. 交接目标

本文档用于把当前 `consumer_test` Phase 1 的实现状态、验证结果、剩余事项和接手方式说明清楚，确保下一位同事可以在最少上下文损失的前提下继续推进。

## 2. 本轮目标回顾

本轮工作的目标是：

- 以 MiroFish 为主架构
- 将消费者项目中的 `BusinessBrief / persona / scoring / report schema` 迁入 MiroFish
- 落地 `concept_test + copy_feedback + propagation-aware simulation`
- 不破坏原版默认项目流程

## 3. 当前代码位置

- 仓库根：
  - `D:\project\MiroFish`
- 实现 worktree：
  - `D:\project\MiroFish\.worktrees\consumer-simulation-phase1`
- 分支：
  - `codex/consumer-simulation-phase1`

## 4. 已完成内容

### 4.1 后端

- `Project` 增加 `project_type / consumer_brief / consumer_context`
- 新增 `backend/app/services/consumer/`
  - `models.py`
  - `brief_adapter.py`
  - `persona_pack.py`
  - `graph_builder.py`
  - `orchestrator.py`
  - `scoring.py`
  - `report_context.py`
- `/api/graph`
  - 支持 `consumer_test` 项目创建
  - 支持 consumer graph build
- `/api/simulation`
  - 支持 `create / prepare / consumer-summary / start` 的消费者分支
- `/api/report`
  - 支持消费者报告上下文与消费者报告生成

### 4.2 前端

- 首页增加 `consumer_test` 输入模式
- `pendingUpload` 支持保存：
  - `projectType`
  - `consumerBrief`
- Step 2-5 增加消费者模式适配
- Step 3 增加：
  - Round 0 / Round 1-N 语义展示
  - consumer summary
  - VOC 展示
- Step 4/5 增加：
  - 消费者报告标签
  - summary 指标
  - VOC highlights
  - 推荐追问
- 中英 locale 补齐消费者模式文案

### 4.3 文档

本轮已同步更新：

- [PRD.md](</D:/project/MiroFish/.worktrees/consumer-simulation-phase1/PRD.md>)
- [2026-04-20-consumer-simulation-testing-design.md](</D:/project/MiroFish/.worktrees/consumer-simulation-phase1/docs/superpowers/specs/2026-04-20-consumer-simulation-testing-design.md>)
- 本交接文档

## 5. 关键提交

- `14ee662` `feat: persist consumer project metadata`
- `d56544d` `feat: add consumer brief contract`
- `3041c6d` `feat: add consumer persona pack`
- `85c2b2e` `feat: add consumer graph build path`
- `a915efe` `feat: branch simulation prep for consumer tests`
- `1e26c7b` `feat: add consumer simulation orchestration`
- `fbc5108` `feat: add consumer scoring and report context`
- `b5fcf90` `feat: add consumer test intake to home flow`
- `d848327` `feat: adapt step views for consumer simulation mode`

## 6. 已验证结果

### 6.1 后端

命令：

```powershell
D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend\.venv\Scripts\python.exe -m pytest
```

结果：

- `45 passed`

### 6.2 前端测试

命令：

```powershell
node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js
```

结果：

- `9 passed`

### 6.3 前端构建

命令：

```powershell
npm run build
```

结果：

- 构建成功

### 6.4 运行条件检查

已确认：

- 当前环境可读取 LLM 配置
- 当前环境可读取 Zep 配置
- 前后端端口 `3000 / 5001` 可以正常拉起

## 7. 已解决的重要问题

- Step 2 consumer metadata 读取路径兼容 `prepare_info / config / 顶层字段`
- Step 3 rerun 时清理旧 `consumerSummary`
- Step 2-5 新增消费者模式文案全部接入 i18n
- consumer quick prompts 编码异常已修复

## 8. 当前未完成事项

- 尚未形成一次完整的人工 smoke run 记录：
  - `consumer brief -> graph -> prepare -> run -> report -> interaction`
- 尚未形成默认模式与消费者模式双分支的人工回归记录
- 尚未完成真实业务素材下的长轮次或成本压测

## 9. 下一步建议

1. 用最小样本做一次完整人工 smoke run，并把结果记成验收记录。
2. 回归默认模式，确认 `project_type=default` 的旧流程没有被破坏。
3. 用真实业务概念/文案素材跑一轮消费者测试。
4. 根据结果判断是否进入：
   - Phase 2 自动预研
   - 更复杂信息分层
   - 更强群体传播建模

## 10. 启动与验证参考

### 10.1 后端

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend
.\.venv\Scripts\python.exe run.py
```

### 10.2 前端

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

### 10.3 全量后端测试

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend
.\.venv\Scripts\python.exe -m pytest
```

### 10.4 前端测试与构建

```powershell
Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1
node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js

Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend
npm run build
```

## 11. 注意事项

- 当前实现主代码在 worktree 分支，不在主工作区直接落地。
- 主工作区根目录 `.env` 提供运行所需的 LLM / Zep 配置。
- 前端仍存在两个非阻断 warning：
  - `pendingUpload.js` 动静态导入混用
  - chunk size warning
