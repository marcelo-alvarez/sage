# Claude Code Orchestrator

A workflow system for Claude Code that guides development through focused agent phases with human approval gates.

## Overview

This orchestrator runs inside Claude Code conversations, directing Claude through a structured workflow: Explorer → Criteria Gate → Planner → Coder → Verifier → Completion Gate. At decision gates, the workflow pauses and presents slash command options for you to control the next steps.

The key insight is separating the work phases (automated) from the decision points (human-controlled), while maintaining context isolation between agents through `/clear` commands and file-based handoffs.

## Quick Start

### Setup
1. Copy `orchestrate.md` to your Claude Code commands directory:
   ```bash
   cp orchestrator-commands/orchestrate.md ~/.claude/commands/
   ```

2. Add tasks to `tasks-checklist.md`:
   ```markdown
   - [ ] Fix authentication bug
   - [ ] Add user profile feature
   ```

### Usage
Start a workflow in Claude Code:
```
/orchestrate
```

Claude will work through the Explorer phase automatically, then pause at the Criteria Gate:
```
🚪 CRITERIA GATE: Human Review Required
• /orchestrate approve-criteria
• /orchestrate modify-criteria "your changes"  
• /orchestrate retry-explorer
```

Choose your path and the workflow continues based on your decision.

## Workflow

```
Explorer ──→ Criteria Gate ──→ Planner ──→ Coder ──→ Verifier ──→ Completion Gate
   ↓              ↓               ↓          ↓          ↓              ↓
analyzes     USER APPROVES     creates   implements  verifies     USER APPROVES
  task         criteria         plan      changes     results      completion
```

**Automated phases:** Explorer, Planner, Coder, Verifier run automatically and hand off to the next phase.

**Decision gates:** Criteria Gate and Completion Gate pause for human input via slash commands.

**Context isolation:** Each agent starts with `/clear` and communicates through files in `.agent-outputs/`.

## Commands

**Workflow control:**
- `/orchestrate` - Start fresh workflow  
- `/orchestrate status` - Show current progress
- `/orchestrate clean` - Reset outputs

**Gate decisions:**
- `/orchestrate approve-criteria` - Accept criteria and continue
- `/orchestrate modify-criteria "changes"` - Edit criteria based on feedback
- `/orchestrate approve-completion` - Mark task complete
- `/orchestrate retry-from-planner` - Restart from planning phase

## Architecture

The orchestrator is a state machine where:
- Python script (`orchestrate_claude.py`) manages workflow state and generates agent instructions
- Claude Code executes the instructions within the conversation
- Files in `.agent-outputs/` provide context between isolated agent phases
- Human input via slash commands controls workflow branching at decision points

## File Structure

```
.agent-outputs/          # Agent work products
├── exploration.md       # Task analysis and suggested criteria
├── success-criteria.md  # Approved success criteria  
├── plan.md             # Implementation plan
├── changes.md          # Code changes made
└── verification.md     # Verification results

tasks-checklist.md      # Task list (source of truth)
tasks.md               # Task status tracking
orchestrate_claude.py  # Workflow engine
```

## Design Principles

**Separation of concerns:** Python manages workflow state, Claude does the development work, human makes decisions.

**Context isolation:** Each agent gets fresh context to avoid pollution and maintain focus.

**File-based communication:** Agents pass information through structured files rather than conversation history.

**Human control:** Decision gates prevent runaway automation and ensure human oversight of critical choices.