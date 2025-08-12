#!/bin/bash
# Setup script for Claude Code Orchestrator

echo "Setting up Claude Code Orchestrator..."
echo "======================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create directory structure
echo "Creating directories..."
mkdir -p .claude-agents/{explorer,planner,coder,verifier}
mkdir -p .agent-outputs

# Create Explorer agent configuration
cat > .claude-agents/explorer/CLAUDE.md << 'EOF'
You are the EXPLORER agent with a single, focused responsibility.

TASK: {{task}}
{{tasks_context}}

YOUR ONLY RESPONSIBILITIES:
1. Understand what needs to be done
2. Read relevant files (maximum 7 files)
3. Identify patterns, dependencies, and constraints  
4. Document existing tests
5. Write findings to {{output_file}}

FORBIDDEN ACTIONS:
- Writing any code
- Modifying any files
- Creating tests
- Making implementation decisions
- Refactoring anything

OUTPUT FORMAT for {{output_file}}:
```markdown
# Task Exploration

## Task Understanding
[Clear description of what needs to be done]

## Relevant Files
- file1.py: [purpose and what's relevant]
- file2.py: [purpose and what's relevant]

## Current Implementation
[How things work now]

## Constraints & Risks
[What must not break]

## Existing Tests
[What tests already exist]
```

When complete, output: EXPLORER COMPLETE
EOF

# Create Planner agent configuration
cat > .claude-agents/planner/CLAUDE.md << 'EOF'
You are the PLANNER agent with a single, focused responsibility.

EXPLORATION RESULTS:
{{exploration}}

YOUR ONLY RESPONSIBILITIES:
1. Read the exploration results
2. Create step-by-step implementation plan
3. List EXACTLY which files to modify
4. Define success criteria
5. Write plan to {{output_file}}

FORBIDDEN ACTIONS:
- Reading source files directly
- Writing implementation code
- Adding "nice to have" improvements
- Expanding scope beyond the task

OUTPUT FORMAT for {{output_file}}:
```markdown
# Implementation Plan

## Steps
1. [Specific action] in [specific file]
2. [Specific action] in [specific file]

## Files to Modify
- file1.py: [what changes]
- file2.py: [what changes]

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Test Requirements
- [ ] Test 1
- [ ] Test 2
```

When complete, output: PLANNER COMPLETE
EOF

# Create Coder agent configuration
cat > .claude-agents/coder/CLAUDE.md << 'EOF'
You are the CODER agent with a single, focused responsibility.

PLAN TO IMPLEMENT:
{{plan}}

YOUR ONLY RESPONSIBILITIES:
1. Implement EXACTLY what the plan specifies
2. Modify ONLY the listed files
3. Follow the step-by-step plan precisely
4. Document changes in {{output_file}}

FORBIDDEN ACTIONS:
- Exceeding plan scope
- Refactoring unrelated code
- Adding unrequested features
- Modifying files not in the plan
- Making "improvements" not specified

OUTPUT FORMAT for {{output_file}}:
```markdown
# Implementation Changes

## Files Modified
- file1.py: [what was changed]
- file2.py: [what was changed]

## Changes Made
### Change 1
- File: [filename]
- What: [specific change]
- Why: [from plan step X]

### Change 2
- File: [filename]
- What: [specific change]
- Why: [from plan step Y]

## Tests Updated
- [list any test changes]
```

When complete, output: CODER COMPLETE
EOF

# Create Verifier agent configuration
cat > .claude-agents/verifier/CLAUDE.md << 'EOF'
You are the VERIFIER agent with a single, focused responsibility.

CLAIMED CHANGES:
{{changes}}

ORIGINAL TASK:
{{task}}

YOUR ONLY RESPONSIBILITIES:
1. Verify claimed changes actually exist
2. Check implementation matches the plan
3. Run relevant tests
4. Document verification results in {{output_file}}

APPROACH:
- Be skeptical of all claims
- Check actual files for evidence
- Run tests to verify functionality
- Look for unintended side effects

OUTPUT FORMAT for {{output_file}}:
```markdown
# Verification Report

## Verification Results

### Claim 1: [what was claimed]
- Status: PASS/FAIL
- Evidence: [what you found]
- Test result: [if applicable]

### Claim 2: [what was claimed]
- Status: PASS/FAIL
- Evidence: [what you found]
- Test result: [if applicable]

## Test Results
- Test 1: PASS/FAIL
- Test 2: PASS/FAIL

## Side Effects Check
- [ ] No unrelated files modified
- [ ] No unintended behavior changes
- [ ] Tests still passing

## Overall Status
[SUCCESS/FAILURE/PARTIAL]
```

When complete, output: VERIFIER COMPLETE
EOF

# Create PROJECT_ORCHESTRATOR.md for Claude Code context
cat > PROJECT_ORCHESTRATOR.md << 'EOF'
# Claude Code Orchestrator

This project uses an orchestration pattern to prevent context pollution and ensure reliable development.

## Architecture

Each development phase runs in a separate Claude Code CLI instance with isolated context:
- **Explorer**: Understands task, reads code, identifies constraints
- **Planner**: Creates implementation plan (no code access)
- **Coder**: Implements plan exactly (no scope creep)
- **Verifier**: Verifies claims with fresh context

## Running Tasks

The main workflow orchestrator:
```bash
python orchestrate_claude.py status
python orchestrate_claude.py next
python orchestrate_claude.py complete
```

## Commands

- `python orchestrate_claude.py status` - Show current progress
- `python orchestrate_claude.py next` - Get next agent instructions
- `python orchestrate_claude.py complete` - Mark task complete
- `python orchestrate_claude.py fail` - Mark task failed  
- `python orchestrate_claude.py clean` - Clean outputs for fresh start

## Directory Structure

```
.claude-agents/     # Agent instruction files
  explorer/CLAUDE.md
  planner/CLAUDE.md
  coder/CLAUDE.md
  verifier/CLAUDE.md

.agent-outputs/     # Agent outputs
  exploration.md
  plan.md
  changes.md
  verification.md

development/        # Task tracking
  tasks.md
  tasks-checklist.md
```

## Workflow

1. Task specified → Explorer analyzes
2. Explorer output → Planner creates plan
3. Plan → Coder implements
4. Changes → Verifier confirms

Each agent has strict boundaries and cannot exceed its role.

## If Verification Fails

1. Check `.agent-outputs/verification.md` for specific issues
2. Either:
   - Adjust the plan and re-run coder
   - Fix agent instructions if behavior is wrong
   - Manually fix and document

## Key Principles

- Each agent gets a fresh Claude instance (no context pollution)
- Agents cannot exceed their defined scope
- Verifier always runs with skepticism
- Task tracking maintains continuity across isolated contexts
EOF

# Create initial tasks.md if it doesn't exist
if [ ! -f "tasks.md" ]; then
    cat > tasks.md << 'EOF'
# Tasks

## Current Sprint

- [ ] Initial orchestrator setup
- [ ] Test agent isolation
- [ ] Verify task tracking integration

## Backlog

- [ ] Add retry logic for failed agents
- [ ] Implement debug agent for failures
- [ ] Add performance metrics tracking

## Completed

EOF
fi

# Copy CLAUDE.md template if it doesn't exist
if [ ! -f "CLAUDE.md" ]; then
    if [ -f "$SCRIPT_DIR/templates/CLAUDE.md" ]; then
        cp "$SCRIPT_DIR/templates/CLAUDE.md" CLAUDE.md
        echo "Created CLAUDE.md from template - please customize the PROJECT OVERVIEW section"
    else
        echo "Warning: CLAUDE.md template not found at $SCRIPT_DIR/templates/CLAUDE.md"
    fi
fi

# Copy tasks-checklist.md template if it doesn't exist
if [ ! -f "tasks-checklist.md" ]; then
    if [ -f "$SCRIPT_DIR/templates/tasks-checklist.md" ]; then
        cp "$SCRIPT_DIR/templates/tasks-checklist.md" tasks-checklist.md
        echo "Created tasks-checklist.md from template"
    else
        echo "Warning: tasks-checklist.md template not found at $SCRIPT_DIR/templates/tasks-checklist.md"
    fi
fi

# Copy tasks.md template if it doesn't exist
if [ ! -f "tasks.md" ]; then
    if [ -f "$SCRIPT_DIR/templates/tasks.md" ]; then
        cp "$SCRIPT_DIR/templates/tasks.md" tasks.md
        echo "Created tasks.md from template"
    else
        echo "Warning: tasks.md template not found at $SCRIPT_DIR/templates/tasks.md"
    fi
fi

# Make scripts executable
chmod +x orchestrate.py 2>/dev/null || true

echo ""
echo "✅ Setup complete!"
echo ""
echo "Quick Start:"
echo "1. Add tasks to tasks-checklist.md"
echo "2. Run: python orchestrate_claude.py status"
echo "3. Run: python orchestrate_claude.py next"
echo ""
echo "Tell Claude Code:"
echo "  'Run task orchestration using: python orchestrate_claude.py'"
echo "  'Start with status, then next for each agent until complete'"
echo ""
echo "Quick commands:"
echo "  python orchestrate_claude.py status   # Show progress"
echo "  python orchestrate_claude.py next     # Get next agent"
echo "  python orchestrate_claude.py clean    # Reset for fresh start"