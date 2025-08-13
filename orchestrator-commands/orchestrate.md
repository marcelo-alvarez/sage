# Orchestrate
Manage the orchestration workflow for tasks with human-in-the-loop gates.

## Setup
To enable this slash command in Claude Code, copy this file to either:
- `~/.claude/commands/orchestrate.md` (for global use across all projects)
- `./.claude/commands/orchestrate.md` (for project-specific use)

## Instructions
Execute the orchestration command with the specified arguments:

```bash
# Source environment and run orchestrator in same bash instance
if [ -f ".orchestrator.env" ]; then
    source .orchestrator.env && python orchestrate_claude.py $ARGUMENTS
elif [ -f "load_env.sh" ]; then
    source load_env.sh && python orchestrate_claude.py $ARGUMENTS
else
    python orchestrate_claude.py $ARGUMENTS
fi
```

## Configuration
To configure environment loading, create `.orchestrator.env` in your project root with any required environment setup commands.