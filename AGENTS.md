# Agent Operating Rules

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
