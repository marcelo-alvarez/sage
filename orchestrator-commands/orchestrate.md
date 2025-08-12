# Orchestrate
Manage the orchestration workflow for tasks.

## Setup
To enable this slash command in Claude Code, copy this file to either:
- `~/.claude/commands/orchestrate.md` (for global use across all projects)
- `./.claude/commands/orchestrate.md` (for project-specific use)

## Usage
- `/orchestrate start` - Begin orchestration for current task
- `/orchestrate next` - Continue to next agent
- `/orchestrate status` - Show current progress  
- `/orchestrate clean` - Reset for fresh start

## Instructions
Execute the orchestration command with the specified action:

```bash
# Check for environment setup script
if [ -f ".orchestrator.env" ]; then
    source .orchestrator.env
elif [ -f "load_env.sh" ]; then
    source load_env.sh
fi

# Run orchestrator
python orchestrate_claude.py $ARGUMENTS
```

If no arguments provided, defaults to 'next' to continue the workflow.

## Configuration
To configure environment loading, create `.orchestrator.env` in your project root with any required environment setup commands.