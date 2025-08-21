# Claude Code Orchestrator

A workflow automation system that guides development through focused agent phases with human approval gates.

## Overview

The orchestrator manages a structured development workflow: **Explorer → Criteria Gate → Planner → Coder → Scribe → Verifier → Completion Gate**. Each agent focuses on a specific responsibility, with human decision points at critical gates.

The system separates automated work phases from human decision points, maintaining context isolation between agents through file-based handoffs in `.agent-outputs/`.

## Quick Start

### Installation

```bash
# Global installation (recommended) - creates cc-orchestrate command
curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash
```

After installation, the `cc-orchestrate` command is available globally.

### Working Directory

**Important**: Always run `cc-orchestrate` from your project's root directory. The orchestrator operates on files relative to the current working directory:
- Looks for tasks in `./claude/` 
- Creates agent outputs in `./.agent-outputs/`
- Reads project files from the current directory

```bash
cd /path/to/your/project  # Navigate to your project first
cc-orchestrate continue    # Run from project root
```

### Required Files

The orchestrator needs task files in your project's `.claude/` directory:
- `.claude/tasks.md` - Task status tracking
- `.claude/tasks-checklist.md` - Task list (source of truth)

These can be created manually or generated using the bootstrap command (see below).

### Basic Usage

#### 1. Generate Initial Tasks (First Time Setup)

Since bootstrap requires interaction with Claude, run it within Claude Code:

```bash
# In Claude Code, use the slash command:
/orchestrate bootstrap
```

Or if you prefer to see the bootstrap instructions from command line:
```bash
cc-orchestrate bootstrap
# Copy the output instructions and paste into Claude Code for execution
```

#### 2. Run Workflows (Command Line - Headless Mode)

After tasks are created, run workflows from your terminal:

```bash
# Run complete workflow automatically (default headless mode)
cc-orchestrate continue

# Start fresh workflow
cc-orchestrate start

# Check current status
cc-orchestrate status
```

**Example Output:**
```
$ cc-orchestrate continue

Claude Code Orchestrator running on task: Implement user authentication

Exploring...
✓ Exploring complete
Planning...
✓ Planning complete
Coding...
✓ Coding complete
Verifying...
✓ PASS - see verification.md for details
✓ WORKFLOW COMPLETED SUCCESSFULLY
```

#### 3. Interactive Mode (Within Claude Code)

For step-by-step control within Claude Code conversations:

```bash
# Use slash commands in Claude Code:
/orchestrate start          # Start workflow
/orchestrate continue       # Continue to next agent
/orchestrate status         # Check progress
```

### Web UI (Coming Soon)

A web-based user interface for the orchestrator is in development to provide a more intuitive way to manage workflows and tasks.

## Execution Modes

#### Headless Mode (Default for Command Line)
- **How it works**: Executes agents automatically using `claude -p` until reaching gates
- **Best for**: Command line usage, CI/CD, batch processing
- **Run with**: `cc-orchestrate continue` (default)
- **Benefits**: Clean output, automated execution, better context isolation

#### Interactive Mode (For Claude Code)
- **How it works**: Generates instructions for Claude to execute within the conversation
- **Best for**: Development within Claude Code, debugging, learning the system
- **Run with**: `/orchestrate continue` (slash command) or `cc-orchestrate continue --interactive`
- **Note**: Has context accumulation issues over long sessions

### Gate Decisions

When the workflow reaches a gate, it pauses for human input:

```
🚪 CRITERIA GATE: Human Review Required
• approve-criteria - Accept and continue
• modify-criteria "changes" - Modify criteria first
• retry-explorer - Restart exploration

Enter your choice: approve-criteria
```

**Available gate commands:**
- `approve-criteria` - Accept success criteria
- `modify-criteria "your changes"` - Request criteria modifications
- `retry-explorer` - Restart from exploration
- `approve-completion` - Mark task complete
- `retry-from-planner` - Restart from planning (keep criteria)
- `retry-from-coder` - Restart from coding (keep plan)
- `retry-from-verifier` - Re-run verification only

## Installation Details

The installer creates:

### Global Runtime Files
```
~/.claude-orchestrator/     # Orchestrator runtime
├── orchestrate.py          # Main script
├── agents/                 # Agent templates
│   ├── explorer/
│   ├── planner/
│   ├── coder/
│   ├── scribe/
│   └── verifier/
└── config/                 # Default configurations
```

### Project Files (per project)
```
your-project/              # Must be current working directory when running cc-orchestrate
├── .claude/
│   ├── tasks.md            # Task status tracking
│   ├── tasks-checklist.md  # Task list (edit this to add tasks)
│   └── commands/           # Slash commands (if local install)
└── .agent-outputs/         # Agent work products (created in current directory)
    ├── exploration.md
    ├── success-criteria.md
    ├── plan.md
    ├── changes.md
    ├── documentation.md
    └── verification.md
```

### Global Commands

#### Regular Mode
- `cc-orchestrate` - Command line executable for regular orchestration
- `/orchestrate` - Claude Code slash command for regular mode

#### Meta Mode  
- `cc-morchestrate` - Command line executable for meta mode orchestration
- `/morchestrate` - Claude Code slash command for meta mode

**Key Differences:**
- **Regular mode** operates on `.agent-outputs/` and `.claude/` directories
- **Meta mode** operates on `.agent-outputs-meta/` and `.claude-meta/` directories  
- **Process isolation**: `cc-orchestrate stop` kills regular processes, `cc-morchestrate stop` kills meta processes
- **Development safety**: Meta mode verifiers can safely test `cc-orchestrate stop` without self-termination

**When to use meta mode:**
- Developing/testing the orchestrator itself
- Running orchestration workflows that need isolation from main development
- Testing process management features safely

## Workflow Phases

1. **Explorer**: Analyzes task requirements and proposes success criteria
2. **Criteria Gate**: Human reviews and approves success criteria
3. **Planner**: Creates implementation plan based on approved criteria
4. **Coder**: Implements the planned changes
5. **Scribe**: Documents the work performed
6. **Verifier**: Tests and validates the implementation
7. **Completion Gate**: Human approves task completion

## Adding Tasks

Edit `.claude/tasks-checklist.md` in your project:

```markdown
# Tasks Checklist

- [ ] Fix authentication bug in login flow
- [ ] Add user profile editing feature
- [ ] Improve error handling in API calls
- [ ] Write tests for payment module
```

## Advanced Features

### Unsupervised Mode

Skip manual gate approvals when criteria are met:

```bash
cc-orchestrate unsupervised   # Enable auto-approval
cc-orchestrate supervised      # Disable auto-approval (default)
```

### Server Commands

Start dashboard and API servers with health monitoring:

```bash
# Start dashboard (port 5678) and API (port 8000) servers
cc-orchestrate serve

# Start in meta mode (uses different process tracking)
cc-morchestrate serve

# Stop all orchestrator processes
cc-orchestrate stop      # Stops regular mode processes
cc-morchestrate stop     # Stops meta mode processes

# Server options
cc-orchestrate serve --no-browser    # Don't open browser automatically
```

**Server Features:**
- Automatic port conflict resolution (tries alternative ports)
- Health monitoring every 30 seconds
- Graceful shutdown with Ctrl+C
- ProcessManager integration for clean process tracking

### Meta-Orchestration

For developing the orchestrator itself, use meta mode to isolate test runs:

```bash
# Run in isolated meta mode
/morchestrate start       # Uses .agent-outputs-meta/
/morchestrate continue    # Continues meta workflow
cc-morchestrate continue  # Command line meta mode
```

### Persistent Interactive Mode

Run interactive workflow with persistent gate handling:

```bash
cc-orchestrate interactive
# Runs continuous workflow with interactive gates
# Use 'exit' at any gate to save state
```

### Custom Environment

Create project-specific environment setup:

```bash
# .orchestrator.env in project root
export API_KEY="your-key"
export DEBUG_MODE="true"
```

## Common Workflows

### Starting a New Project

1. Install orchestrator globally (once):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash
   ```

2. In Claude Code, generate initial tasks:
   ```
   /orchestrate bootstrap
   ```

3. Run first task from command line:
   ```bash
   cc-orchestrate start
   ```

### Daily Development Flow

1. Navigate to your project directory:
   ```bash
   cd /path/to/your/project
   ```

2. Check status:
   ```bash
   cc-orchestrate status
   ```

3. Continue workflow:
   ```bash
   cc-orchestrate continue
   ```

4. At gates, make decisions:
   ```bash
   Enter your choice: approve-criteria
   ```

5. After completion, clean and start next task:
   ```bash
   cc-orchestrate clean
   cc-orchestrate continue
   ```

### Debugging Failed Workflows

1. Run interactively in Claude Code:
   ```
   /orchestrate continue
   ```

2. Or retry specific phases:
   ```bash
   cc-orchestrate retry-from-coder  # Keep plan, redo implementation
   ```

## Troubleshooting

### "No tasks found" or Files Not Found
Ensure you're running `cc-orchestrate` from your project's root directory. The orchestrator looks for `.claude/` and creates `.agent-outputs/` relative to the current working directory.

```bash
pwd  # Check you're in the right directory
ls -la .claude/  # Verify .claude directory exists
```

### Bootstrap Not Working from Command Line
Bootstrap generates instructions for Claude to execute. Run it within Claude Code using `/orchestrate bootstrap` or paste the output from `cc-orchestrate bootstrap` into Claude Code.

### "Claude CLI not found"
Install Claude CLI from [claude.ai/code](https://claude.ai/code). The orchestrator requires it for headless execution.

### Context Accumulation in Interactive Mode
Interactive mode can accumulate context over long sessions. Use headless mode (`cc-orchestrate continue`) for better performance.

### Workflow Stuck at Gate
Gates require human input. Check for pending gate decisions with `cc-orchestrate status`.

## Design Philosophy

- **Separation of Concerns**: Each agent has a single, focused responsibility
- **Human Oversight**: Critical decisions remain under human control
- **Context Isolation**: Agents communicate through files, not conversation history
- **Automation with Control**: Automate repetitive work while maintaining quality gates

## Requirements

- Python 3.6+
- Claude CLI (for headless mode)
- Unix-like environment (Linux, macOS, WSL)
