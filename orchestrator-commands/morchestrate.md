# Meta-Orchestrate
Manage orchestration workflows in meta mode (isolated from main orchestration sessions).

Available commands:

**Workflow Control:**
- `bootstrap` - Generate initial tasks for your project
- `start` - Start fresh workflow in meta mode
- `continue` - Continue to next agent in meta mode
- `status` - Show current progress in meta mode
- `clean` - Reset meta mode outputs
- `complete` - Mark current task as complete
- `fail` - Mark current task as failed

**Gate Decisions:**
- `approve-criteria` - Accept criteria and continue in meta mode
- `modify-criteria "changes"` - Edit criteria based on feedback in meta mode
- `approve-completion` - Mark workflow complete and approve results
- `retry-explorer` - Restart from Explorer phase

**Selective Retry:**
- `retry-from-planner` - Restart from Planner phase (keep criteria)
- `retry-from-coder` - Restart from Coder phase (keep plan)
- `retry-from-verifier` - Re-run Verifier only (keep changes)

**Mode Control:**
- `unsupervised` - Enable automatic gate approval
- `supervised` - Disable automatic gate approval (default)

## Purpose
The `/morchestrate` command is identical to `/orchestrate` but runs in "meta mode":
- Uses `.agent-outputs-meta/` instead of `.agent-outputs/` 
- Uses `.claude-meta/` instead of `.claude/`
- All continuation commands automatically include "meta" flag
- Prevents interference with main orchestration workflows

This is essential when developing the orchestrator itself, as it prevents test runs from interfering with the main development workflow.

## Setup
To enable this slash command in Claude Code, copy this file to either:
- `~/.claude/commands/morchestrate.md` (for global use across all projects)
- `./.claude/commands/morchestrate.md` (for project-specific use)

## Instructions
Execute the meta-orchestration command with enhanced visibility:

```bash
# Source environment and run orchestrator in meta mode
if [ -f ".orchestrator.env" ]; then
    source .orchestrator.env
elif [ -f "load_env.sh" ]; then
    source load_env.sh
fi

# Run orchestrator in meta mode and immediately show results
echo "Running meta-orchestrator command: $ARGUMENTS"
echo "================================================"
result=$(python3 ~/.claude-orchestrator/orchestrate.py $ARGUMENTS meta)
echo "$result"
echo "================================================"

# If this is a gate command, ensure options are visible
if [[ "$result" == *"GATE"* && "$result" == *"OPTIONS:"* ]]; then
    echo ""
    echo "GATE DETECTED - OPTIONS AVAILABLE ABOVE"
    echo "Choose one of the /morchestrate commands listed above"
    echo ""
fi
```

## Configuration
To configure environment loading, create `.orchestrator.env` in your project root with any required environment setup commands.