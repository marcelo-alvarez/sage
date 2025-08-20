# Claude Code Orchestrator

A workflow system for Claude Code that guides development through focused agent phases with human approval gates.

## Overview

This orchestrator runs inside Claude Code conversations, directing Claude through a structured workflow: Explorer → Criteria Gate → Planner → Coder → Scribe → Verifier → Completion Gate. At decision gates, the workflow pauses and presents slash command options for you to control the next steps.

The key insight is separating the work phases (automated) from the decision points (human-controlled), while maintaining context isolation between agents through `/clear` commands and file-based handoffs.

## Quick Start

### Installation

Install the orchestrator with a single command:

```bash
# Global installation (recommended) - creates cc-orchestrate command in PATH
curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/claude-orchestrator/main/install.sh | bash
```

After installation, the `cc-orchestrate` command is available globally for running workflows.

### Basic Usage (Headless Mode - Default)

The orchestrator runs in clean headless mode by default, showing only essential progress:

```bash
# Run a complete workflow automatically
cc-orchestrate continue

# Start fresh workflow  
cc-orchestrate start

# Bootstrap initial tasks for your project
cc-orchestrate bootstrap

# Check current workflow status
cc-orchestrate status
```

**Example Output:**
```
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

### Interactive Mode

For step-by-step control with gates, use interactive mode:

```bash
# Run with interactive gates for approval control
cc-orchestrate continue --interactive

# Persistent interactive workflow (single process)
cc-orchestrate interactive
```

### Two Ways to Run Workflows

**Terminal (Primary)** - Clean headless execution:
```bash
cc-orchestrate continue      # Headless mode (default)
cc-orchestrate continue --interactive  # With gates
```

**Claude Code Slash Commands** - Interactive workflow within conversations:
```bash
/orchestrate continue        # Continue workflow in Claude Code
/orchestrate start           # Start fresh workflow
```

The terminal commands provide clean output for automation and regular use, while slash commands are perfect for development and interactive workflow control within Claude Code conversations.

### Installation Options

The `install.sh` script supports these arguments:

| Argument | Description | Default |
|----------|-------------|---------|
| `--project-dir DIR` | Initialize project files in specific directory | Current directory |
| `--branch BRANCH` | Install from specific git branch | `main` |
| `--local-command` | Install slash command locally in project instead of globally | Global installation |
| `--help` | Show detailed usage information | - |

**Installation Behavior:**
- **Runtime files** install to `~/.claude-orchestrator/` (global)
- **cc-orchestrate command** added to PATH for global access
- **Slash command** installs to `~/.claude/commands/` (global) or `.claude/commands/` (local)
- **Project files** (`.claude/tasks*.md`) created in specified project directory

### Generate Initial Tasks

Use the bootstrap command to analyze your project and create initial tasks:
```bash
cc-orchestrate bootstrap
```

Claude will:
1. Analyze your codebase and project structure
2. Ask about your goals and priorities
3. Generate specific, actionable tasks
4. Create both `tasks.md` and `tasks-checklist.md` files

Alternatively, manually add tasks to `.claude/tasks-checklist.md`:
```markdown
- [ ] Fix authentication bug
- [ ] Add user profile feature
```

### Usage

The orchestrator supports two execution modes:

#### Interactive Mode (Default)
In interactive mode, Claude shows you instructions to execute manually, giving you full control over each step. Note that interactive mode has known context accumulation issues where conversation history can become large over time, affecting performance.

```
/orchestrate start
```

Claude will present instructions like:
```
INSTRUCTION TO CLAUDE:
Read the file .agent-outputs/next-command.txt
Then follow the instructions it contains exactly.
============================================================
AGENT: EXPLORER
============================================================
```

You can then read the file and execute the agent instructions manually.

#### Headless Mode (Experimental)
For automated execution, add the `--headless` flag:

```
/orchestrate start --headless
```

In headless mode, the orchestrator runs automatically without human intervention until it reaches a decision gate:
```
🚪 CRITERIA GATE: Human Review Required
• /orchestrate approve-criteria
• /orchestrate modify-criteria "your changes"  
• /orchestrate retry-explorer
```

Choose your path and the workflow continues based on your decision.

#### When to Use Each Mode

**Interactive Mode (Default)** - Best for:
- Development and debugging
- Learning how the orchestrator works
- Fine-grained control over each step
- Reviewing agent instructions before execution
- Working on complex or sensitive tasks
- Note: Has context accumulation issues that may affect performance over long sessions

**Headless Mode (Experimental)** - Best for:
- CI/CD automation (when stabilized)
- Batch processing multiple tasks
- Well-tested workflows
- Background execution
- Meta-orchestration testing during development
- Note: Currently experimental - will become the default once stabilized due to better context isolation

**Example Workflow:**
```bash
# Start development with interactive mode for control
/orchestrate start

# Once confident in the workflow, switch to headless for speed
/orchestrate continue --headless

# Switch back to interactive for final review
/orchestrate continue
```

## Workflow

```
Explorer ──→ Criteria Gate ──→ Planner ──→ Coder ──→ Scribe ──→ Verifier ──→ Completion Gate
   ↓              ↓               ↓          ↓          ↓           ↓              ↓
analyzes     USER APPROVES     creates   implements  documents   verifies     USER APPROVES
  task         criteria         plan      changes      work       results      completion
```

**Automated phases:** Explorer, Planner, Coder, Scribe, Verifier run automatically and hand off to the next phase.

**Decision gates:** Criteria Gate and Completion Gate pause for human input via slash commands.

**Context isolation:** Each agent starts with `/clear` and communicates through files in `.agent-outputs/`.

### Meta-Orchestration (Advanced)

When developing the orchestrator itself, use meta-mode to prevent interference with your main development workflow:

```bash
# Interactive meta-orchestration (default)
/morchestrate start    # Uses .agent-outputs-meta/ and .claude-meta/
/morchestrate status   # Check meta workflow progress
/morchestrate clean    # Clean meta workflow files

# Headless meta-orchestration for automated testing
/morchestrate start --headless    # Run meta workflow automatically
/morchestrate continue --headless # Continue meta workflow automatically
```

**Meta-mode features:**
- **Complete isolation:** Uses separate directories (`.agent-outputs-meta/`, `.claude-meta/`)
- **Self-propagating:** All continuation commands automatically include `meta` flag
- **Prevents collision:** Testing/development won't interfere with main workflow
- **Identical functionality:** Same agents and workflow, just isolated namespace
- **Same execution modes:** Supports both interactive and headless execution

## Commands

### Main Workflow Commands

**Workflow control:**
- `/orchestrate bootstrap` - Generate initial tasks for your project
- `/orchestrate start` - Start fresh workflow  
- `/orchestrate continue` - Continue to next agent
- `/orchestrate status` - Show current progress
- `/orchestrate clean` - Reset outputs

**Gate decisions:**
- `/orchestrate approve-criteria` - Accept criteria and continue
- `/orchestrate modify-criteria "changes"` - Edit criteria based on feedback
- `/orchestrate approve-completion` - Mark task complete
- `/orchestrate retry-explorer` - Restart from exploration phase
- `/orchestrate retry-from-planner` - Restart from planning phase
- `/orchestrate retry-from-coder` - Restart from coding phase
- `/orchestrate retry-from-verifier` - Re-verify only

**Execution modes:**
Add `--headless` to any command to run in automated mode:
- `/orchestrate start --headless` - Start in headless mode
- `/orchestrate continue --headless` - Continue in headless mode
- Default: Interactive mode (shows instructions to Claude)

### Meta-Orchestration Commands

When working on orchestrator development, use these isolated commands:

**Meta workflow control:**
- `/morchestrate bootstrap` - Generate tasks in meta mode
- `/morchestrate start` - Start workflow in isolated meta mode
- `/morchestrate continue` - Continue meta workflow
- `/morchestrate status` - Show meta workflow progress
- `/morchestrate clean` - Reset meta workflow outputs

**Meta gate decisions:**
- `/morchestrate approve-criteria` - Accept criteria in meta mode
- `/morchestrate modify-criteria "changes"` - Edit criteria in meta mode
- `/morchestrate approve-completion` - Mark meta task complete

**Meta execution modes:**
Add `--headless` to any meta command to run in automated mode:
- `/morchestrate start --headless` - Start meta workflow in headless mode
- `/morchestrate continue --headless` - Continue meta workflow in headless mode
- Default: Interactive mode (shows instructions to Claude)

### Custom Environment Configuration

The orchestrator supports project-specific environment setup through optional configuration files in your project root.

#### Environment Files

- **`.orchestrator.env`** - Simple environment variable exports
- **`load_env.sh`** - Complex shell script for advanced environment setup

#### Loading Behavior

Before executing orchestrator commands, the system automatically sources environment files in this priority order:

1. `.orchestrator.env` (if exists)
2. `load_env.sh` (if exists and no `.orchestrator.env` found)
3. System defaults (if no environment files found)

This allows you to customize the development environment on a per-project basis without modifying the global orchestrator installation.

## Architecture

The orchestrator is a state machine where:
- Python script (`.claude/orchestrate.py`) manages workflow state and generates agent instructions
- Claude Code executes the instructions within the conversation
- Files in `.agent-outputs/` provide context between isolated agent phases
- Human input via slash commands controls workflow branching at decision points

## File Structure

### Global Runtime (installed once)
```
~/.claude-orchestrator/   # Global runtime files
├── orchestrate.py        # Main orchestrator script
├── agents/               # Agent templates
│   ├── explorer/CLAUDE.md
│   ├── planner/CLAUDE.md
│   ├── coder/CLAUDE.md
│   ├── scribe/CLAUDE.md
│   ├── verifier/CLAUDE.md
│   └── example-custom/CLAUDE.md
└── config/               # Default configurations
    ├── agent-config.json
    └── workflow-config.json

~/.claude/commands/       # Global slash commands (if global install)
├── orchestrate.md        # Main orchestration command
└── morchestrate.md       # Meta-orchestration command
```

### Project Structure (per project)
```
your-project/
├── .orchestrator.env     # Custom environment (optional)
├── load_env.sh          # Complex environment setup (optional)
├── CLAUDE.md            # Project-specific Claude Code instructions
├── .claude/             # Project orchestrator files
│   ├── commands/        # Local slash commands (if local install)
│   │   └── orchestrate.md
│   ├── tasks.md         # Task status tracking
│   ├── tasks-checklist.md # Task list (source of truth)
│   └── agent-config.json  # Custom agent overrides (optional)
├── .agent-outputs/      # Main workflow products
│   ├── exploration.md
│   ├── success-criteria.md
│   ├── plan.md
│   ├── changes.md
│   ├── documentation.md
│   └── verification.md
└── .agent-outputs-meta/ # Meta workflow products (when using /morchestrate)
    ├── exploration.md
    ├── success-criteria.md
    ├── plan.md
    ├── changes.md
    ├── documentation.md
    └── verification.md
```

## Design Principles

**Separation of concerns:** Python manages workflow state, Claude does the development work, human makes decisions.

**Context isolation:** Each agent gets fresh context to avoid pollution and maintain focus.

**File-based communication:** Agents pass information through structured files rather than conversation history.

**Human control:** Decision gates prevent runaway automation and ensure human oversight of critical choices.

## Advanced Features

### Custom Agent Creation

The orchestrator supports custom agent types beyond the built-in ones (explorer, planner, coder, scribe, verifier). You can create specialized agents for your specific workflows.

#### Creating a Custom Agent

1. **Create the agent directory:**
   ```bash
   mkdir -p ~/.claude-orchestrator/agents/my-custom-agent
   ```

2. **Create the agent template file:**
   ```bash
   # ~/.claude-orchestrator/agents/my-custom-agent/CLAUDE.md
   ```

3. **Define the agent template:**
   ```markdown
   You are the MY-CUSTOM-AGENT agent.

   TASK: {{task}}

   YOUR ONLY RESPONSIBILITIES:
   1. Perform specialized analysis
   2. Generate custom reports
   3. Write findings to .agent-outputs/custom-analysis.md

   FORBIDDEN ACTIONS:
   - Modifying source code
   - Making implementation decisions
   - Creating unrelated files
   ```

**Note:** The orchestrator automatically adds completion commands - do not include them in your templates.

#### Template Format Requirements

**Required Elements:**
- **Work section:** Description of agent responsibilities and tasks
- **Variables:** Use `{{variable}}` format for substitution (e.g., `{{task}}`)

**Best Practices:**
- Define clear responsibilities section
- Specify forbidden actions to maintain focus
- Avoid including completion commands (auto-generated)
- Use descriptive agent names

#### Variable Substitution

Custom agents support variable substitution:
- `{{task}}` - The current task being worked on
- `{{project_name}}` - Project name (for some agents)
- `{{custom_var}}` - Any custom variables you define

Variables are automatically detected and can be passed when creating agent instances.

#### Integration with Workflows

Custom agents are automatically discovered and can be:
- Listed in available agents
- Integrated into workflow sequences
- Used in orchestration commands

The system validates custom templates to ensure they have required fields and proper structure.

### Workflow Customization

You can customize the workflow sequence by creating a `.claude/workflow-config.json` file in your project:

```json
{
  "sequence": ["explorer", "criteria_gate", "planner", "custom-agent", "coder", "scribe", "verifier", "completion_gate"],
  "gates": {
    "criteria": {
      "after": "explorer",
      "options": [
        "Execute the slash-command `/orchestrate approve-criteria` - Accept and continue",
        "Execute the slash-command `/orchestrate modify-criteria` - Modify criteria first"
      ]
    }
  }
}
```

### Agent Overrides

Override built-in agent behavior by creating a `.claude/agent-config.json` file in your project:

```json
{
  "agents": {
    "coder": {
      "work_section": "Custom coder instructions here...",
      "completion_phrase": "CODER COMPLETE",
      "primary_objective": "Complete coding work according to responsibilities"
    }
  }
}
```