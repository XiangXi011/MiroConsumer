# Agent Operating Rules

## Delegating To Claude Code

Every task in this repository must load and follow:

```text
C:\Users\05537\.agents\skills\delegating-to-claude-code\SKILL.md
```

Codex owns:

- problem framing
- decomposition and task ordering
- safety checks
- audit of Claude Code output
- final communication with the user

Claude Code owns bounded execution work:

- file edits
- command execution
- targeted tests
- verification artifact collection

For implementation, editing, or verification tasks, Codex must invoke:

```powershell
python "C:\Users\05537\.agents\skills\delegating-to-claude-code\invoke_claude_executor.py" `
  --cwd "<repository-or-worktree-path>" `
  --task "<bounded execution task>" `
  --allowed-path "<allowed path>"
```

Codex must inspect the resulting diff and rerun critical checks before reporting completion.

## Timeout Policy

Codex must not use a 300-second timeout for Claude Code delegation. The default timeout for delegated implementation, editing, or verification work is at least 900 seconds.

For broad implementation work, full regression checks, documentation generation, or multi-file verification, Codex must use at least 1800 seconds or split the work into smaller delegated tasks with separate audits.

This rule is repository-wide and applies to all future tasks unless the user explicitly disables Claude Code delegation for a specific task.
