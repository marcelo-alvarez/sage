# Orchestrate
Manage the orchestration workflow for tasks with human-in-the-loop gates.

## Setup
To enable this slash command in Claude Code, copy this file to either:
- `~/.claude/commands/orchestrate.md` (for global use across all projects)
- `./.claude/commands/orchestrate.md` (for project-specific use)

## Instructions
Execute the orchestration command with enhanced visibility:

```bash
# Source environment and run orchestrator with immediate output visibility
if [ -f ".orchestrator.env" ]; then
    source .orchestrator.env
elif [ -f "load_env.sh" ]; then
    source load_env.sh
fi

# Run orchestrator and immediately show results
echo "Running orchestrator command: $ARGUMENTS"
echo "================================================"
result=$(python orchestrate_claude.py $ARGUMENTS)
echo "$result"
echo "================================================"

# If this is a gate command, ensure options are visible
if [[ "$result" == *"GATE"* && "$result" == *"OPTIONS:"* ]]; then
    echo ""
    echo "GATE DETECTED - OPTIONS AVAILABLE ABOVE"
    echo "Choose one of the /orchestrate commands listed above"
    echo ""
fi
```

## Configuration
To configure environment loading, create `.orchestrator.env` in your project root with any required environment setup commands.