# SAGE

A workflow automation system that guides development through focused agent phases with human approval gates, enhanced with SAGE (project understanding memory) for efficient context-aware orchestration.

## Overview

The orchestrator manages a structured development workflow: **Explorer → Criteria Gate → Planner → Coder → Scribe → Verifier → Completion Gate**. Each agent focuses on a specific responsibility, with human decision points at critical gates.

The system separates automated work phases from human decision points, maintaining context isolation between agents through file-based handoffs in `.agent-outputs/`. Enhanced with SAGE project understanding memory to prevent redundant exploration and maintain institutional knowledge across workflow sessions.

### SAGE Project Understanding Memory

**SAGE (Smart Agent Guided Execution)** provides persistent project understanding to dramatically reduce redundant work:

- **Architecture Quick Reference**: Maintains awareness of key components, directories, and critical files
- **Recent Discoveries**: Tracks the last 20 timestamped insights about the system to prevent rediscovery
- **Known Gotchas**: Documents common pitfalls and critical rules to avoid repeated mistakes
- **Self-Reinforcing Knowledge**: Explorer reads SAGE files first, Scribe updates them after verification
- **Mode-Aware**: Separate files for regular (`SAGE.md`) and meta mode (`SAGE-meta.md`) operations

SAGE reduces exploration time by 40-50% and prevents knowledge loss during agent handoffs by 60-70%.

## Quick Start

### Installation

```bash
# Global installation (recommended) - creates cc-orchestrate command
curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/sage/main/install.sh | bash
```

After installation, the `cc-orchestrate` command is available globally. The installer creates runtime components including the enhanced process management system with `orchestrator_logger.py` for improved reliability and cleanup monitoring.

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

#### 3. Web UI Interface

Access the orchestrator through a web dashboard for real-time workflow monitoring and control:

```bash
# Start the web interface (dashboard port 5678, API port 8000)
cc-orchestrate serve

# Start in meta mode for orchestrator development
cc-morchestrate serve

# Server options
cc-orchestrate serve --no-browser    # Don't open browser automatically
```

**Enhanced Web UI Features:**
- **Real-time Status Monitoring**: Live workflow progress with 30-second auto-refresh and improved connection reliability
- **Interactive Gate Controls**: Streamlined approve/modify buttons for criteria and completion gates with enhanced error handling
- **Advanced File Viewer**: Browse and view all agent outputs with markdown rendering and syntax highlighting
- **Enhanced Dashboard**: Improved status consistency, better error reporting, and comprehensive workflow progress tracking
- **Meta Mode Support**: Visual indicators and mode-specific functionality with clear process isolation
- **Connection Monitoring**: Advanced retry logic with automatic reconnection and detailed status indicators
- **Process Health Checks**: Continuous monitoring with improved reliability and graceful degradation
- **Command Execution**: Clean and continue operations directly from the interface with better feedback

**Robust Server Management:**
- **Enhanced Process Management**: Improved cleanup reliability with `orchestrator_logger.py` integration
- **Automatic Port Resolution**: Intelligent fallback to alternative ports (5678-5698, 6000-6020 for dashboard; 8000-8020, 9000-9020 for API)
- **Advanced Health Monitoring**: Continuous health checks every 30 seconds with comprehensive status logging and timeout handling
- **Graceful Shutdown**: Clean process termination with Ctrl+C and proper cleanup of background processes
- **Process Isolation**: Enhanced separation for regular vs meta mode operations with improved tracking
- **Connection Reliability**: ThreadingHTTPServer implementation for better concurrent request handling

**Access URLs:**
- Dashboard: `http://localhost:5678/dashboard.html`
- API Status: `http://localhost:8000/api/status`
- Health Check: `http://localhost:8000/api/health`

**Known Limitations**: The Web UI uses 30-second polling rather than real-time WebSocket connections. For detailed limitations and troubleshooting, see [KNOWN-ISSUES.md](./KNOWN-ISSUES.md) and [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

The web interface provides a modern, responsive dashboard for managing orchestrator workflows without requiring command-line interaction.

## Execution Modes

#### Headless Mode (Experimental - Future Default)
- **How it works**: Executes agents automatically using `claude -p` with fresh context isolation until reaching gates
- **Best for**: Command line usage, CI/CD, batch processing, consistent performance across long workflows
- **Run with**: `cc-orchestrate continue --headless` or `export CLAUDE_ORCHESTRATOR_MODE=headless`
- **Benefits**: Clean output, automated execution, superior context isolation, prevents token limit issues
- **Current Limitation**: 5+ minute opacity periods during agent execution with no progress indicators
- **Future**: Will become default mode once stability and progress visibility issues are resolved

For detailed headless mode documentation, configuration, and migration timeline, see [HEADLESS.md](./HEADLESS.md).

#### Interactive Mode (Current Default)
- **How it works**: Generates instructions for Claude to execute within the conversation
- **Best for**: Development within Claude Code, debugging, learning the system
- **Run with**: `/orchestrate continue` (slash command) or `cc-orchestrate continue` (default)
- **Note**: Has context accumulation issues over long sessions; will be deprecated when headless mode stabilizes

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
├── orchestrator_logger.py  # Enhanced logging system (new runtime component)
├── process_manager.py      # Process tracking and cleanup management
├── workflow_status.py      # Workflow state management
├── api_server.py          # REST API server for dashboard
├── dashboard_server.py    # Web interface server
├── agents/                # Agent templates
│   ├── explorer/
│   ├── planner/
│   ├── coder/
│   ├── scribe/
│   └── verifier/
└── config/               # Default configurations
```

### Project Files (per project)
```
your-project/              # Must be current working directory when running cc-orchestrate
├── SAGE.md                # SAGE project understanding memory (regular mode)
├── SAGE-meta.md          # SAGE project understanding memory (meta mode)
├── .claude/
│   ├── tasks.md            # Task status tracking
│   ├── tasks-checklist.md  # Task list (edit this to add tasks)
│   ├── session-context.json # Persistent session context (prevents redundant work)
│   └── commands/           # Slash commands (if local install)
├── .agent-outputs/         # Agent work products (created in current directory)
│   ├── exploration.md
│   ├── success-criteria.md
│   ├── plan.md
│   ├── changes.md
│   ├── documentation.md
│   └── verification.md
└── .agent-outputs-meta/    # Meta mode agent outputs (isolated from regular mode)
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

Start dashboard and API servers with enhanced health monitoring and improved process management:

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

**Enhanced Server Features:**
- **Improved Process Management**: `orchestrator_logger.py` integration ensures reliable cleanup and comprehensive process tracking
- **Automatic Port Conflict Resolution**: Intelligent fallback to alternative ports with extended ranges
- **Advanced Health Monitoring**: Continuous health checks every 30 seconds with timeout handling and connection reliability improvements
- **Graceful Shutdown**: Enhanced process termination with Ctrl+C including proper cleanup of background workflow processes
- **ProcessManager Integration**: Complete process tracking for both serve processes and background workflow executions
- **Connection Stability**: ThreadingHTTPServer implementation for better concurrent request handling and reduced unresponsiveness
- **Background Process Registration**: All workflow processes (including `continue` operations) properly tracked for system-wide cleanup

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
   curl -fsSL https://raw.githubusercontent.com/marcelo-alvarez/sage/main/install.sh | bash
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

### Quick Reference

For comprehensive troubleshooting of Web UI issues, server problems, and browser compatibility:
- **Detailed Web UI Troubleshooting**: See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Known Limitations and Issues**: See [KNOWN-ISSUES.md](./KNOWN-ISSUES.md)
- **Headless Mode Configuration**: See [HEADLESS.md](./HEADLESS.md)

### Common Issues

#### "No tasks found" or Files Not Found
Ensure you're running `cc-orchestrate` from your project's root directory. The orchestrator looks for `.claude/` and creates `.agent-outputs/` relative to the current working directory.

```bash
pwd  # Check you're in the right directory
ls -la .claude/  # Verify .claude directory exists
ls -la SAGE.md   # Check SAGE project understanding file exists
```

#### Bootstrap Not Working from Command Line
Bootstrap generates instructions for Claude to execute and creates initial SAGE files. Run it within Claude Code using `/orchestrate bootstrap` or paste the output from `cc-orchestrate bootstrap` into Claude Code.

#### "Claude CLI not found"
Install Claude CLI from [claude.ai/code](https://claude.ai/code). The orchestrator requires it for headless execution.

#### Context Accumulation in Interactive Mode
Interactive mode can accumulate context over long sessions. Use headless mode (`cc-orchestrate continue --headless`) for better performance and context isolation.

#### Workflow Stuck at Gate
Gates require human input. Check for pending gate decisions with `cc-orchestrate status`.

#### Web UI Connection Issues
If the dashboard becomes unresponsive:
```bash
# Force refresh the dashboard connection
# Or restart servers
cc-orchestrate stop
cc-orchestrate serve
```

#### Process Cleanup Issues
Improved process management ensures complete cleanup:
```bash
# Stop all orchestrator processes (enhanced cleanup)
cc-orchestrate stop      # Regular mode
cc-morchestrate stop     # Meta mode
```

## Design Philosophy

- **Separation of Concerns**: Each agent has a single, focused responsibility
- **Human Oversight**: Critical decisions remain under human control
- **Context Isolation**: Agents communicate through files, not conversation history
- **Automation with Control**: Automate repetitive work while maintaining quality gates

## Architecture and Features Summary

**Core Enhancements:**
- **SAGE Project Understanding Memory**: Prevents 40-50% of redundant exploration work with persistent architectural awareness
- **Enhanced Web UI**: Improved dashboard with better connection reliability, advanced health monitoring, and comprehensive status tracking
- **Robust Process Management**: Complete process tracking and cleanup with `orchestrator_logger.py` integration
- **Session Persistence**: Context preservation across runs prevents information rediscovery
- **Advanced Server Architecture**: ThreadingHTTPServer implementation with automatic port resolution and graceful shutdown

**Recent Stability Improvements:**
- Fixed criteria modal icon bugs and workflow retry cleanup issues
- Resolved process cleanup reliability problems with comprehensive ProcessManager integration
- Enhanced agent log task headers consistency across all agents
- Improved workflow sequencing and background process registration
- Added unsupervised mode toggle for automated gate decisions

## Requirements

- Python 3.6+
- Claude CLI (for headless mode)
- Unix-like environment (Linux, macOS, WSL)
- Modern web browser for dashboard interface (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
