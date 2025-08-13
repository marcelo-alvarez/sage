# Claude Orchestrator

A reusable orchestration system for Claude Code that provides:
- Focused agent-based task execution
- Task tracking and management  
- Context isolation between phases
- Visibility into Claude's process

## Required Files

The orchestrator requires these files in your project root:

| File | Purpose | Created By |
|------|---------|------------|
| `CLAUDE.md` | Project context and guidelines for Claude Code | `setup_orchestrator.sh` (template) |
| `tasks-checklist.md` | List of tasks to complete (source of truth) | `setup_orchestrator.sh` (template) |
| `tasks.md` | Task status tracking and history | `setup_orchestrator.sh` (template) |
| `.orchestrator.env` | Environment setup commands (optional) | User (when needed) |

## Quick Start

### 1. Setup in Your Project

```bash
# From your project directory
./setup_orchestrator.sh
```

This creates:
- Agent configuration files in `.claude-agents/`
- Output directory `.agent-outputs/`
- Template files: `CLAUDE.md`, `tasks-checklist.md`, `tasks.md`

### 2. Customize Project Context

Edit `CLAUDE.md` to add your project-specific information:
```markdown
## PROJECT OVERVIEW

[Replace with: Description of your project, main purpose, key technologies]

## PROJECT-SPECIFIC GUIDELINES

[Add: Any project conventions, patterns, or requirements]
```

### 3. Add Tasks

Edit `tasks-checklist.md`:
```markdown
- [ ] Fix authentication bug
- [ ] Add user profile feature
- [ ] Optimize database queries
```

### 4. Configure Environment (Optional)

If your project requires environment setup (e.g., virtual environments, API keys):
```bash
# Create .orchestrator.env in your project root
echo 'source venv/bin/activate' > .orchestrator.env
echo 'export API_KEY=your-key' >> .orchestrator.env
```

The orchestrator will automatically source `.orchestrator.env` before running.

### 5. Enable Slash Command (Optional)

Copy the orchestrate command to Claude Code's commands directory:
```bash
# For global use across all projects
cp orchestrator-commands/orchestrate.md ~/.claude/commands/

# OR for project-specific use
cp orchestrator-commands/orchestrate.md .claude/commands/
```

This enables `/orchestrate` commands in Claude Code.

### 6. Run in Claude Code

Tell Claude:
```
Run the task orchestration. Always use: python orchestrate_claude.py
Start with "status", then "next" for each agent until complete.
```

Or use the slash command if enabled:
```
/orchestrate status
/orchestrate next
```

## How It Works

The orchestrator runs Claude through focused agents with user approval gates:

1. **Explorer** - Understands the task and explores the codebase
2. **Criteria Gate** - User approves/modifies success criteria (human-in-the-loop)
3. **Planner** - Creates an implementation plan based on approved criteria
4. **Coder** - Implements the plan exactly
5. **Verifier** - Verifies all changes with fresh context
6. **Completion Gate** - User approves completion or requests changes (human-in-the-loop)

### Agent Characteristics
Each agent:
- Starts with `/clear` to reset context
- Has a single, focused responsibility
- Cannot exceed its defined scope
- Passes outputs to the next agent via files

### User Gates
- **Criteria Gate**: Review and approve success criteria after exploration
- **Completion Gate**: Verify work is complete or request modifications

## Commands

| Command | Description | When to Use |
|---------|-------------|-------------|
| `python orchestrate_claude.py` (no args) | Start fresh workflow | Begin new task |
| `python orchestrate_claude.py start` | Start fresh workflow | Same as no args |
| `python orchestrate_claude.py next` | Continue from current state | Resume workflow |
| `python orchestrate_claude.py status` | Show current progress | Check what's done |
| `python orchestrate_claude.py clean` | Clean outputs only | Reset without starting |
| `python orchestrate_claude.py complete` | Mark task complete | Force completion |
| `python orchestrate_claude.py fail` | Mark task failed | Force failure |

**Key Differences:**
- **`start`** (default): Always begins fresh by cleaning outputs first, then starts Explorer
- **`next`**: Continues from wherever you left off (Explorer → Criteria Gate → Planner → Coder → Verifier → Completion Gate)
- **`clean`**: Just resets outputs without starting the workflow

## License

MIT
