#!/bin/bash
# bootstrap.sh - Create complete claude-orchestrator repo in CURRENT directory

set -e  # Exit on error

echo "🚀 Setting up claude-orchestrator in current directory..."

# Create directory structure
mkdir -p templates/agents/{explorer,planner,coder,verifier}
mkdir -p templates/commands
mkdir -p examples/{web-app,data-science,devops}/.claude-agents
mkdir -p utils

echo "✓ Directory structure created"

# Create main orchestrator file
cat > orchestrate_claude.py << 'PYEOF'
#!/usr/bin/env python3
"""
Claude-Driven Orchestrator
Designed to be run BY Claude Code to orchestrate itself through agents
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import re
import sys

class ClaudeDrivenOrchestrator:
    def __init__(self):
        self.project_root = Path.cwd()
        self.agents_dir = self.project_root / ".claude-agents"
        self.outputs_dir = self.project_root / ".agent-outputs"
        
        # Task tracking files in root directory
        self.tasks_file = self.project_root / "tasks.md"
        self.checklist_file = self.project_root / "tasks-checklist.md"
        
        # Ensure directories exist
        self.agents_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        
    def get_next_agent(self) -> tuple[str, str]:
        """Get the next agent to run and its instructions"""
        
        # Check what outputs exist to determine next phase
        exploration_exists = (self.outputs_dir / "exploration.md").exists()
        plan_exists = (self.outputs_dir / "plan.md").exists()
        changes_exists = (self.outputs_dir / "changes.md").exists()
        verification_exists = (self.outputs_dir / "verification.md").exists()
        
        if not exploration_exists:
            return self._prepare_explorer()
        elif not plan_exists:
            return self._prepare_planner()
        elif not changes_exists:
            return self._prepare_coder()
        elif not verification_exists:
            return self._prepare_verifier()
        else:
            return "complete", "All agents have completed. Check .agent-outputs/verification.md for results."
            
    def _prepare_explorer(self) -> tuple[str, str]:
        """Prepare explorer agent instructions"""
        
        task = self._get_current_task()
        if not task:
            return "error", "No task found in tasks-checklist.md"
            
        self._update_task_status(task, "🔄 EXPLORER")
        
        instructions = f"""FIRST: Run /clear to reset context

Then execute as EXPLORER agent:

TASK: {task}

YOUR ONLY RESPONSIBILITIES:
1. Understand what needs to be done
2. Read relevant files (maximum 7)
3. Identify patterns and dependencies
4. Write findings to .agent-outputs/exploration.md

FORBIDDEN ACTIONS:
- Writing code
- Modifying files
- Creating tests

Output format for exploration.md:
# Task Exploration
## Task Understanding
## Relevant Files
## Current Implementation
## Constraints & Risks

When complete, say "EXPLORER COMPLETE" """
        
        return "explorer", instructions
        
    def _prepare_planner(self) -> tuple[str, str]:
        """Prepare planner agent instructions"""
        
        task = self._get_current_task()
        self._update_task_status(task, "🔄 PLANNER")
        
        instructions = """FIRST: Run /clear to reset context

Then execute as PLANNER agent:

Read .agent-outputs/exploration.md to understand the task.

YOUR ONLY RESPONSIBILITIES:
1. Create step-by-step implementation plan
2. List exact files to modify
3. Define success criteria
4. Write plan to .agent-outputs/plan.md

FORBIDDEN ACTIONS:
- Reading source code files directly
- Writing implementation code
- Adding unrequested features

Output format for plan.md:
# Implementation Plan
## Steps
## Files to Modify
## Success Criteria

When complete, say "PLANNER COMPLETE" """
        
        return "planner", instructions
        
    def _prepare_coder(self) -> tuple[str, str]:
        """Prepare coder agent instructions"""
        
        task = self._get_current_task()
        self._update_task_status(task, "🔄 CODER")
        
        instructions = """FIRST: Run /clear to reset context

Then execute as CODER agent:

Read .agent-outputs/plan.md to understand what to implement.

YOUR ONLY RESPONSIBILITIES:
1. Implement EXACTLY what the plan specifies
2. Modify only listed files
3. Document changes in .agent-outputs/changes.md

FORBIDDEN ACTIONS:
- Exceeding plan scope
- Refactoring unrelated code
- Adding unrequested features

Output format for changes.md:
# Implementation Changes
## Files Modified
## Changes Made
## Tests Updated

When complete, say "CODER COMPLETE" """
        
        return "coder", instructions
        
    def _prepare_verifier(self) -> tuple[str, str]:
        """Prepare verifier agent instructions"""
        
        task = self._get_current_task()
        self._update_task_status(task, "🔄 VERIFIER")
        
        instructions = """FIRST: Run /clear to reset context

Then execute as VERIFIER agent with fresh perspective:

Read .agent-outputs/changes.md to see what was supposedly done.

YOUR ONLY RESPONSIBILITIES:
1. Verify all claimed changes actually exist
2. Check if implementation matches plan
3. Run tests if applicable
4. Write results to .agent-outputs/verification.md

Be skeptical. Check everything. Trust nothing.

Output format for verification.md:
# Verification Report
## Verification Results
- Claim 1: PASS/FAIL with evidence
- Claim 2: PASS/FAIL with evidence
## Overall Status: SUCCESS/FAILURE

When complete, say "VERIFIER COMPLETE" """
        
        return "verifier", instructions
        
    def mark_complete(self, success: bool = True):
        """Mark current task as complete or failed"""
        
        task = self._get_current_task()
        if not task:
            return
            
        if success:
            self._update_task_status(task, "✅ COMPLETE")
            self._update_checklist(task, completed=True)
            print(f"\n✅ Task marked complete: {task}")
        else:
            self._update_task_status(task, "⚠️ NEEDS REVIEW")
            print(f"\n⚠️ Task needs review: {task}")
            
    def clean_outputs(self):
        """Clean output directory for fresh run"""
        
        for file in self.outputs_dir.glob("*.md"):
            file.unlink()
        print("🧹 Cleaned .agent-outputs/ directory")
        
    def status(self):
        """Show current orchestration status"""
        
        print("\n📊 Orchestration Status:")
        print("-" * 40)
        
        files = [
            ("exploration.md", "Explorer"),
            ("plan.md", "Planner"),
            ("changes.md", "Coder"),
            ("verification.md", "Verifier")
        ]
        
        for filename, agent in files:
            filepath = self.outputs_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                print(f"✓ {agent:<12} complete ({size} bytes)")
            else:
                print(f"⏳ {agent:<12} pending")
                
        current_task = self._get_current_task()
        if current_task:
            print(f"\n📋 Current task: {current_task[:60]}")
            
    def _get_current_task(self) -> Optional[str]:
        """Extract next uncompleted task from tasks-checklist.md"""
        
        if self.checklist_file.exists():
            content = self.checklist_file.read_text()
            lines = content.split('\n')
            
            for line in lines:
                if re.match(r'^\s*-\s*\[\s*\]\s*', line):
                    task = re.sub(r'^\s*-\s*\[\s*\]\s*', '', line)
                    task = re.sub(r'\s*\(.*\)\s*$', '', task)
                    task = task.strip()
                    if task:
                        return task
        return None
        
    def _update_task_status(self, task: str, status: str):
        """Update task status in tasks.md"""
        
        if not task:
            return
            
        if not self.tasks_file.exists():
            self.tasks_file.write_text(f"# Tasks\n\n- [ ] {task} - {status}\n")
            return
            
        content = self.tasks_file.read_text()
        lines = content.split('\n')
        
        task_updated = False
        for i, line in enumerate(lines):
            if task[:30] in line:
                if '- [ ]' in line:
                    lines[i] = f"- [ ] {task} - {status}"
                elif '- [x]' in line:
                    if status == "✅ COMPLETE":
                        lines[i] = f"- [x] {task} - {status}"
                    else:
                        lines[i] = f"- [ ] {task} - {status}"
                task_updated = True
                break
                
        if not task_updated:
            lines.append(f"- [ ] {task} - {status}")
            
        self.tasks_file.write_text('\n'.join(lines))
        
    def _update_checklist(self, task: str, completed: bool):
        """Update task in checklist file"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if not self.checklist_file.exists():
            self.checklist_file.write_text("# Tasks Checklist\n\n")
            
        content = self.checklist_file.read_text()
        lines = content.split('\n')
        task_found = False
        
        for i, line in enumerate(lines):
            if task[:50] in line and '- [ ]' in line:
                if completed:
                    lines[i] = f"- [x] {task} (Completed: {timestamp})"
                else:
                    lines[i] = f"- [ ] {task} (Attempted: {timestamp})"
                task_found = True
                break
        
        if not task_found:
            if completed:
                new_line = f"- [x] {task} (Completed: {timestamp})"
            else:
                new_line = f"- [ ] {task} (Attempted: {timestamp})"
            lines.append(new_line)
        
        self.checklist_file.write_text('\n'.join(lines))


def main():
    """CLI entry point - designed for Claude to run"""
    
    orchestrator = ClaudeDrivenOrchestrator()
    
    if len(sys.argv) < 2:
        print("""
Claude-Driven Orchestrator Commands:

  python orchestrate_claude.py next      - Get next agent to run
  python orchestrate_claude.py complete   - Mark task complete
  python orchestrate_claude.py fail       - Mark task failed
  python orchestrate_claude.py status     - Show progress
  python orchestrate_claude.py clean      - Clean outputs for fresh start
        """)
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "next":
        agent, instructions = orchestrator.get_next_agent()
        print(f"\n{'='*60}")
        print(f"AGENT: {agent.upper()}")
        print(f"{'='*60}")
        print(instructions)
        print(f"{'='*60}")
        
    elif command == "complete":
        orchestrator.mark_complete(success=True)
        
    elif command == "fail":
        orchestrator.mark_complete(success=False)
        
    elif command == "status":
        orchestrator.status()
        
    elif command == "clean":
        orchestrator.clean_outputs()
        
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
PYEOF

echo "✓ Created orchestrate_claude.py"

# Create setup.sh
cat > setup.sh << 'SETUPEOF'
#!/bin/bash
# setup.sh - Initialize orchestrator in any project

echo "🚀 Setting up Claude Orchestrator..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in a git repo (optional)
if [ -d .git ]; then
    echo "✓ Git repository detected"
fi

# Create directory structure
mkdir -p .claude-agents/{explorer,planner,coder,verifier}
mkdir -p .agent-outputs
mkdir -p .claude/commands

# Copy orchestrator
cp "$SCRIPT_DIR/orchestrate_claude.py" .

# Copy default agent templates if they exist
if [ -d "$SCRIPT_DIR/templates/agents" ]; then
    cp -r "$SCRIPT_DIR/templates/agents"/* .claude-agents/
fi

# Copy slash commands if they exist
if [ -d "$SCRIPT_DIR/templates/commands" ]; then
    cp "$SCRIPT_DIR/templates/commands"/* .claude/commands/ 2>/dev/null || true
fi

# Create task files if they don't exist
if [ ! -f tasks-checklist.md ]; then
    echo "# Tasks Checklist" > tasks-checklist.md
    echo "" >> tasks-checklist.md
fi

if [ ! -f tasks.md ]; then
    echo "# Tasks" > tasks.md
    echo "" >> tasks.md
    echo "## Current Sprint" >> tasks.md
fi

# Add to .gitignore
if [ -f .gitignore ]; then
    grep -q "Claude Orchestrator" .gitignore || {
        echo "" >> .gitignore
        echo "# Claude Orchestrator" >> .gitignore
        echo ".agent-outputs/" >> .gitignore
        echo ".claude-agents/**/*.md" >> .gitignore
    }
fi

echo "✅ Setup complete!"
echo ""
echo "Quick start:"
echo "1. Add tasks to tasks-checklist.md"
echo "2. Run: claude"
echo "3. Tell Claude: 'Run orchestration with: python orchestrate_claude.py'"
SETUPEOF

chmod +x setup.sh
echo "✓ Created setup.sh"

# Create agent templates
mkdir -p templates/agents/{explorer,planner,coder,verifier}

cat > templates/agents/explorer/CLAUDE.md << 'AGENTEOF'
You are the EXPLORER agent.

TASK: {{task}}

YOUR ONLY RESPONSIBILITIES:
1. Understand what needs to be done
2. Read relevant files (maximum 7)
3. Identify patterns, dependencies, and constraints
4. Document existing tests
5. Write findings to .agent-outputs/exploration.md

FORBIDDEN ACTIONS:
- Writing any code
- Modifying any files
- Creating tests
- Making implementation decisions

When complete, output: EXPLORER COMPLETE
AGENTEOF

cat > templates/agents/planner/CLAUDE.md << 'AGENTEOF'
You are the PLANNER agent.

Read .agent-outputs/exploration.md to understand the task.

YOUR ONLY RESPONSIBILITIES:
1. Create step-by-step implementation plan
2. List exact files to modify
3. Define success criteria
4. Write plan to .agent-outputs/plan.md

FORBIDDEN ACTIONS:
- Reading source files directly
- Writing implementation code
- Adding improvements not in task

When complete, output: PLANNER COMPLETE
AGENTEOF

cat > templates/agents/coder/CLAUDE.md << 'AGENTEOF'
You are the CODER agent.

Read .agent-outputs/plan.md to understand what to implement.

YOUR ONLY RESPONSIBILITIES:
1. Implement EXACTLY what the plan specifies
2. Modify only listed files
3. Document changes in .agent-outputs/changes.md

FORBIDDEN ACTIONS:
- Exceeding plan scope
- Refactoring unrelated code
- Adding unrequested features

When complete, output: CODER COMPLETE
AGENTEOF

cat > templates/agents/verifier/CLAUDE.md << 'AGENTEOF'
You are the VERIFIER agent.

Read .agent-outputs/changes.md to see what was supposedly done.

YOUR ONLY RESPONSIBILITIES:
1. Verify claimed changes actually exist
2. Check implementation matches the plan
3. Run relevant tests
4. Document verification results in .agent-outputs/verification.md

Be skeptical. Check everything.

When complete, output: VERIFIER COMPLETE
AGENTEOF

echo "✓ Created agent templates"

# Create README
cat > README.md << 'READMEEOF'
# Claude Orchestrator

A reusable orchestration system for Claude Code that provides:
- 🎯 Focused agent-based task execution
- 📊 Task tracking and management  
- 🔄 Context isolation between phases
- 👁️ Full visibility into Claude's process

## Quick Start

### 1. Setup in Your Project

```bash
# From your project directory
/path/to/claude-orchestrator/setup.sh
```

### 2. Add Tasks

Edit `tasks-checklist.md`:
```markdown
- [ ] Fix authentication bug
- [ ] Add user profile feature
- [ ] Optimize database queries
```

### 3. Run in Claude Code

Tell Claude:
```
Run the task orchestration. Always use: python orchestrate_claude.py
Start with "status", then "next" for each agent until complete.
```

## How It Works

The orchestrator runs Claude through four focused agents:

1. **Explorer** - Understands the task and explores the codebase
2. **Planner** - Creates an implementation plan
3. **Coder** - Implements the plan exactly
4. **Verifier** - Verifies all changes with fresh context

Each agent:
- Starts with `/clear` to reset context
- Has a single, focused responsibility
- Cannot exceed its defined scope
- Passes outputs to the next agent via files

## Commands

- `python orchestrate_claude.py status` - Show current progress
- `python orchestrate_claude.py next` - Get next agent instructions
- `python orchestrate_claude.py complete` - Mark task complete
- `python orchestrate_claude.py fail` - Mark task failed
- `python orchestrate_claude.py clean` - Clean outputs for fresh start

## License

MIT
READMEEOF

echo "✓ Created README.md"

# Create .gitignore
cat > .gitignore << 'GITIGNOREEOF'
# Claude Orchestrator
.agent-outputs/
*.pyc
__pycache__/
.DS_Store
GITIGNOREEOF

echo "✓ Created .gitignore"

# Copy template files from templates directory
cp templates/tasks.md tasks.md
echo "✓ Created tasks.md from template"

cp templates/tasks-checklist.md tasks-checklist.md
echo "✓ Created tasks-checklist.md from template"

cp templates/CLAUDE.md CLAUDE.md
echo "✓ Created CLAUDE.md from template"

# Git operations
if [ -d .git ]; then
    git add .
    git commit -m "Initial commit: Claude Orchestrator system

- Core orchestrator (orchestrate_claude.py)
- Setup script for easy installation
- Agent templates (explorer, planner, coder, verifier)
- Comprehensive README"
    
    echo "✓ Git commit complete"
else
    echo "⚠️  No .git directory - skipping git commit"
fi

echo ""
echo "🎉 Bootstrap complete!"
echo ""
echo "Next steps:"
echo "1. Push to GitHub: git push -u origin main"
echo ""
echo "To use in a project:"
echo "  cd /your/project"
echo "  $(pwd)/setup.sh"
echo ""
echo "Then in Claude Code:"
echo "  'Run orchestration with: python orchestrate_claude.py'"
