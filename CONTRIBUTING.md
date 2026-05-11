# Contributing Guide / 贡献指南

## Development Environment / 开发环境

1. Clone the repository
2. Install dependencies: `cd backend && pip install -e ".[dev]"`
3. Run tests: `pytest`
4. Start dev server: `flask run`

## Code Standards / 代码规范

- Python: PEP 8, use `ruff lint`
- Tests: pytest, coverage >= 70%
- Commit: Conventional Commits format

## PR Process / PR 流程

1. Fork -> Create branch
2. Write tests / 编写测试
3. Pass CI (pytest + lint + security scan)
4. Submit PR with change description / 提交 PR，填写变更说明
