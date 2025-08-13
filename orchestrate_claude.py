#!/usr/bin/env python3
"""
Claude-Driven Orchestrator with Automatic Response Detection
Designed to be run BY Claude Code to orchestrate itself through agents
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
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
        
    def get_next_agent(self) -> Tuple[str, str]:
        """Get the next agent to run and its instructions"""
        
        # Check what outputs exist to determine next phase
        exploration_exists = (self.outputs_dir / "exploration.md").exists()
        criteria_approved = (self.outputs_dir / "success-criteria.md").exists()
        plan_exists = (self.outputs_dir / "plan.md").exists()
        changes_exists = (self.outputs_dir / "changes.md").exists()
        verification_exists = (self.outputs_dir / "verification.md").exists()
        completion_approved = (self.outputs_dir / "completion-approved.md").exists()
        
        # Workflow: Explorer → Criteria Gate → Planner → Coder → Verifier → Completion Gate → Complete
        if not exploration_exists:
            return self._prepare_explorer()
        elif exploration_exists and not criteria_approved:
            return self._prepare_criteria_gate()
        elif not plan_exists:
            return self._prepare_planner()
        elif not changes_exists:
            return self._prepare_coder()
        elif not verification_exists:
            return self._prepare_verifier()
        elif verification_exists and not completion_approved:
            return self._prepare_completion_gate()
        else:
            return "complete", "All agents have completed successfully. Task marked complete."
            
    def _prepare_explorer(self) -> Tuple[str, str]:
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
5. Suggest objective success criteria for this task

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
## Suggested Success Criteria
- [Objective criterion 1 - e.g., specific files must exist]
- [Objective criterion 2 - e.g., no hanging processes]
- [Objective criterion 3 - e.g., specific output generated]

When complete, say "EXPLORER COMPLETE"

FINAL STEP: Run /clear to reset context, then run: source load_env.sh && python orchestrate_claude.py next"""
        
        return "explorer", instructions
        
    def _prepare_criteria_gate(self) -> Tuple[str, str]:
        """Prepare criteria approval gate"""
        
        task = self._get_current_task()
        self._update_task_status(task, "🚪 CRITERIA GATE")
        
        exploration_file = self.outputs_dir / "exploration.md"
        if not exploration_file.exists():
            return "error", "No exploration.md found for criteria approval"
        
        exploration_content = exploration_file.read_text()
        
        # Extract suggested criteria from exploration.md
        lines = exploration_content.split('\n')
        criteria_section = []
        in_criteria = False
        
        for line in lines:
            if "## Suggested Success Criteria" in line:
                in_criteria = True
                continue
            elif in_criteria and line.strip().startswith('##'):
                break
            elif in_criteria and line.strip():
                criteria_section.append(line.strip())
        
        criteria_text = '\n'.join(criteria_section) if criteria_section else "No criteria found in exploration.md"
        
        instructions = f"""HUMAN APPROVAL REQUIRED: Success Criteria Gate

The Explorer has suggested the following success criteria:

{criteria_text}

PLEASE REVIEW AND RESPOND:
1. **APPROVED** - Accept criteria and continue to Planner
2. **MODIFY: [your changes]** - Update criteria and continue  
3. **RETRY EXPLORER** - Restart from Explorer phase

I will now detect your response and process it automatically.

When you respond, I will:
- Parse your response (APPROVED/MODIFY/RETRY EXPLORER)
- Save the appropriate criteria to success-criteria.md
- Continue to the next phase automatically

Waiting for your response..."""
        
        return "criteria_gate", instructions
        
    def _prepare_planner(self) -> Tuple[str, str]:
        """Prepare planner agent instructions"""
        
        task = self._get_current_task()
        self._update_task_status(task, "🔄 PLANNER")
        
        instructions = """FIRST: Run /clear to reset context

Then execute as PLANNER agent:

Read .agent-outputs/exploration.md to understand the task.
Read .agent-outputs/success-criteria.md for the approved success criteria.

YOUR ONLY RESPONSIBILITIES:
1. Create step-by-step implementation plan
2. List exact files to modify
3. Define success criteria (from approved criteria)
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

When complete, say "PLANNER COMPLETE"

FINAL STEP: Run /clear to reset context, then run: source load_env.sh && python orchestrate_claude.py next"""
        
        return "planner", instructions
        
    def _prepare_coder(self) -> Tuple[str, str]:
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

When complete, say "CODER COMPLETE"

FINAL STEP: Run /clear to reset context, then run: source load_env.sh && python orchestrate_claude.py next"""
        
        return "coder", instructions
        
    def _prepare_verifier(self) -> Tuple[str, str]:
        """Prepare verifier agent instructions"""
        
        task = self._get_current_task()
        self._update_task_status(task, "🔄 VERIFIER")
        
        instructions = """FIRST: Run /clear to reset context

Then execute as VERIFIER agent with fresh perspective:

Read .agent-outputs/changes.md to see what was supposedly done.
Read .agent-outputs/success-criteria.md for the approved success criteria.

YOUR ONLY RESPONSIBILITIES:
1. Verify all claimed changes actually exist
2. Check if implementation matches plan
3. CHECK OBJECTIVE SUCCESS CRITERIA FIRST - These are mandatory
4. Run tests if applicable
5. Write results to .agent-outputs/verification.md

Be skeptical. Check everything. Trust nothing.
SUCCESS CRITERIA MUST BE MET - No partial credit for "progress" or "breakthroughs".

Output format for verification.md:
# Verification Report
## Success Criteria Verification
- Criterion 1: PASS/FAIL with evidence
- Criterion 2: PASS/FAIL with evidence
- Criterion 3: PASS/FAIL with evidence
## Code Changes Verification
- Claim 1: PASS/FAIL with evidence
- Claim 2: PASS/FAIL with evidence
## Overall Status: SUCCESS/FAILURE

When complete, say "VERIFIER COMPLETE"

FINAL STEP: Run /clear to reset context, then run: source load_env.sh && python orchestrate_claude.py next"""
        
        return "verifier", instructions
        
    def _prepare_completion_gate(self) -> Tuple[str, str]:
        """Prepare completion approval gate"""
        
        task = self._get_current_task()
        self._update_task_status(task, "🚪 COMPLETION GATE")
        
        verification_file = self.outputs_dir / "verification.md"
        if not verification_file.exists():
            return "error", "No verification.md found for completion approval"
        
        verification_content = verification_file.read_text()
        
        # Extract overall status
        status_line = "Status not found"
        for line in verification_content.split('\n'):
            if "Overall Status:" in line:
                status_line = line.strip()
                break
        
        instructions = f"""HUMAN APPROVAL REQUIRED: Completion Gate

The Verifier has completed with the following results:

{status_line}

Full verification details in .agent-outputs/verification.md

PLEASE REVIEW AND RESPOND:
1. **APPROVED** - Mark task complete and finish
2. **RETRY EXPLORER** - Restart entire workflow from Explorer
3. **RETRY PLANNER** - Restart from Planner (keep criteria)
4. **RETRY CODER** - Restart from Coder (keep plan)
5. **RETRY VERIFIER** - Restart just Verifier (keep changes)

I will now detect your response and process it automatically.

When you respond, I will:
- Parse your response (APPROVED/RETRY [PHASE])
- Either mark task complete or clean and restart from specified phase
- Continue the workflow automatically

Waiting for your response..."""
        
        return "completion_gate", instructions
        
    def detect_and_process_response(self, gate_type: str) -> bool:
        """Detect human response in conversation and process it automatically"""
        
        # This method will be called by Claude after showing the gate prompt
        # Claude should provide the human response as context
        
        # For criteria gate
        if gate_type == "criteria":
            # Claude should detect "APPROVED", "MODIFY: ...", or "RETRY EXPLORER" in conversation
            # and call the appropriate processing
            pass
            
        elif gate_type == "completion":
            # Claude should detect "APPROVED" or "RETRY [PHASE]" in conversation
            # and call the appropriate processing
            pass
            
        return False
        
    def process_criteria_approval(self, response: str):
        """Process criteria approval response"""
        
        response = response.strip().upper()
        
        if response == "APPROVED":
            # Extract criteria from exploration.md and save
            exploration_file = self.outputs_dir / "exploration.md"
            if exploration_file.exists():
                content = exploration_file.read_text()
                lines = content.split('\n')
                criteria_section = []
                in_criteria = False
                
                for line in lines:
                    if "## Suggested Success Criteria" in line:
                        in_criteria = True
                        continue
                    elif in_criteria and line.strip().startswith('##'):
                        break
                    elif in_criteria and line.strip():
                        criteria_section.append(line.strip())
                
                criteria_text = '\n'.join(criteria_section)
                criteria_file = self.outputs_dir / "success-criteria.md"
                criteria_file.write_text(f"# Approved Success Criteria\n\n{criteria_text}\n")
                print("✅ Success criteria approved and saved")
                return True
                
        elif response.startswith("MODIFY:"):
            # Save modified criteria
            modified_criteria = response[7:].strip()
            criteria_file = self.outputs_dir / "success-criteria.md"
            criteria_file.write_text(f"# Approved Success Criteria\n\n{modified_criteria}\n")
            print("✅ Modified success criteria saved")
            return True
            
        elif response == "RETRY EXPLORER":
            self._clean_from_phase("explorer")
            print("🔄 Restarting from Explorer phase")
            return True
            
        return False
        
    def process_completion_approval(self, response: str):
        """Process completion approval response"""
        
        response = response.strip().upper()
        
        if response == "APPROVED":
            task = self._get_current_task()
            if task:
                self._update_task_status(task, "✅ COMPLETE")
                self._update_checklist(task, completed=True)
                approval_file = self.outputs_dir / "completion-approved.md"
                approval_file.write_text(f"# Task Completion Approved\n\nTask: {task}\nApproved at: {datetime.now().isoformat()}\n")
                print(f"✅ Task marked complete: {task}")
                return True
                
        elif "RETRY" in response:
            phase = response.split()[-1].lower()
            self._clean_from_phase(phase)
            print(f"🔄 Restarting from {phase.title()} phase")
            return True
            
        return False
    
    def _clean_from_phase(self, phase: str):
        """Clean outputs from specified phase onwards"""
        
        phase_files = {
            "explorer": ["exploration.md", "success-criteria.md", "plan.md", "changes.md", "verification.md", "completion-approved.md"],
            "planner": ["plan.md", "changes.md", "verification.md", "completion-approved.md"],
            "coder": ["changes.md", "verification.md", "completion-approved.md"],
            "verifier": ["verification.md", "completion-approved.md"]
        }
        
        files_to_clean = phase_files.get(phase, [])
        for filename in files_to_clean:
            filepath = self.outputs_dir / filename
            if filepath.exists():
                filepath.unlink()
                
        task = self._get_current_task()
        if task:
            self._update_task_status(task, f"🔄 RETRY FROM {phase.upper()}")
        
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
        print("-" * 50)
        
        files = [
            ("exploration.md", "Explorer"),
            ("success-criteria.md", "Criteria Gate"),
            ("plan.md", "Planner"),
            ("changes.md", "Coder"),
            ("verification.md", "Verifier"),
            ("completion-approved.md", "Completion Gate")
        ]
        
        for filename, agent in files:
            filepath = self.outputs_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                print(f"✓ {agent:<15} complete ({size} bytes)")
            else:
                print(f"⏳ {agent:<15} pending")
                
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
        command = "next"  # Default to next when no arguments provided
    else:
        command = sys.argv[1]
    
    if command == "next":
        agent, instructions = orchestrator.get_next_agent()
        print(f"\n{'='*60}")
        print(f"AGENT: {agent.upper()}")
        print(f"{'='*60}")
        print(instructions)
        print(f"{'='*60}")
        
        # Special handling for gates - Claude should detect and process responses
        if agent == "criteria_gate":
            print("\nAfter you respond with APPROVED/MODIFY/RETRY EXPLORER:")
            print("I will automatically detect your response and:")
            print("1. Parse your approval/modification/retry request")
            print("2. Save the appropriate criteria to success-criteria.md")
            print("3. Continue to the next phase")
            print("\nNo additional commands needed - just respond with your decision.")
            
        elif agent == "completion_gate":
            print("\nAfter you respond with APPROVED/RETRY [PHASE]:")
            print("I will automatically detect your response and:")
            print("1. Parse your approval/retry request")
            print("2. Either mark complete or restart from specified phase")
            print("3. Continue the workflow")
            print("\nNo additional commands needed - just respond with your decision.")
        
    elif command == "status":
        orchestrator.status()
        
    elif command == "clean":
        orchestrator.clean_outputs()
        
    elif command == "complete":
        orchestrator.mark_complete(success=True)
        
    elif command == "fail":
        orchestrator.mark_complete(success=False)
        
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()