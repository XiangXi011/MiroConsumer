# Agent Operating Rules

## Delegation Policy

Claude Code delegation is **optional**, not the default. Codex is the default executor for file edits, command execution, and verification tasks. Codex retains responsibility for framing, execution choice, audit, and final communication with the user.

Claude Code should only be used when the user explicitly asks for it, or when Codex deliberately chooses to delegate a bounded, well-scoped task. Any work delegated to Claude Code must remain bounded and be audited by Codex before it is considered complete.

## File Operations

When creating or editing files, use `exec_command` with shell commands like:
- `printf 'content' > file` for new files
- `cat > file << 'EOF'` for multi-line files
- `sed -i '' 's/old/new/' file` for edits

Do NOT use `apply_patch` tool - it does not work with this API provider.
Always verify file creation with `ls -la` or `cat` after writing.

## Testing

Always run tests after making changes:
```bash
cd ~/MiroConsumer-phase5 && python -m pytest backend/tests/ -x -q
```
