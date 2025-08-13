# Orchestrate
Manage the orchestration workflow for tasks.

## Setup
To enable this slash command in Claude Code, copy this file to either:
- `~/.claude/commands/orchestrate.md` (for global use across all projects)
- `./.claude/commands/orchestrate.md` (for project-specific use)

## Usage
- `/orchestrate` - Start fresh workflow (default, same as start)
- `/orchestrate start` - Start fresh workflow (clean outputs + begin)
- `/orchestrate next` - Continue from current state
- `/orchestrate status` - Show current progress  
- `/orchestrate clean` - Clean outputs only

## Instructions
Execute the orchestration command with the specified action:

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

If no arguments provided, defaults to 'start' to begin fresh workflow.

## Configuration
To configure environment loading, create `.orchestrator.env` in your project root with any required environment setup commands.