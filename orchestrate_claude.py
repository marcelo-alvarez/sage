#!/usr/bin/env python3
"""
Enhanced Claude-Driven Orchestrator with Better Gate Visibility
Addresses Claude Code's output truncation by using echo commands
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import re
import sys


# AGENT PROMPT TEMPLATES
AGENT_PROMPTS = {
    "explorer": {
        "work_section": """Then execute as EXPLORER agent:

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
- [Objective criterion 3 - e.g., specific output generated]""",
        "primary_objective": "After completing exploration work, run /clear then use the slash command /orchestrate next to advance the workflow",
        "completion_phrase": "EXPLORER COMPLETE"
    },
    
    "planner": {
        "work_section": """Then execute as PLANNER agent:

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
## Success Criteria""",
        "primary_objective": "After completing the plan, run /clear then use the slash command /orchestrate next to advance the workflow",
        "completion_phrase": "PLANNER COMPLETE"
    },
    
    "coder": {
        "work_section": """Then execute as CODER agent:

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
## Tests Updated""",
        "primary_objective": "After completing implementation, run /clear then use the slash command /orchestrate next to advance the workflow",
        "completion_phrase": "CODER COMPLETE"
    },
    
    "verifier": {
        "work_section": """Then execute as VERIFIER agent with fresh perspective:

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
## Overall Status: SUCCESS/FAILURE""",
        "primary_objective": "After completing verification, run /clear then use the slash command /orchestrate next to advance the workflow",
        "completion_phrase": "VERIFIER COMPLETE"
    }
}

GATE_OPTIONS = {
    "criteria": [
        "/orchestrate approve-criteria    - Accept and continue",
        "/orchestrate modify-criteria     - Modify criteria first",  
        "/orchestrate retry-explorer      - Restart exploration"
    ],
    
    "completion": [
        "/orchestrate approve-completion     - Mark complete",
        "/orchestrate retry-explorer         - Restart all",
        "/orchestrate retry-from-planner     - Restart from Planner",  
        "/orchestrate retry-from-coder       - Restart from Coder",
        "/orchestrate retry-from-verifier    - Re-verify only"
    ]
}


class AgentDefinitions:
    """Centralized agent role definitions using external prompts"""
    
    @staticmethod
    def get_work_agent_role(agent_type: str, **kwargs) -> dict:
        """Generic method for work agents (explorer, planner, coder, verifier)"""
        prompt = AGENT_PROMPTS[agent_type]
        
        # Handle template variables (like {task} for explorer)
        work_section = prompt["work_section"]
        if kwargs:
            work_section = work_section.format(**kwargs)
        
        return {
            "name": agent_type.upper(),
            "status": f"🔄 {agent_type.upper()}",
            "completion_phrase": prompt["completion_phrase"],
            "primary_objective": prompt["primary_objective"],
            "work_section": work_section,
            "auto_continue": True
        }
    
    @staticmethod
    def get_gate_role(gate_type: str, content: str) -> dict:
        """Generic method for gate agents"""
        return {
            "name": f"{gate_type.upper()}_GATE",
            "status": f"🚪 {gate_type.upper()} GATE",
            "content": content,
            "options": GATE_OPTIONS[gate_type],
            "auto_continue": False
        }


class AgentFactory:
    """Factory for creating agent instructions"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        
    def create_agent(self, agent_type: str, **kwargs) -> Tuple[str, str]:
        """Create agent instructions based on type"""
        
        if agent_type in ["explorer", "planner", "coder", "verifier"]:
            role = AgentDefinitions.get_work_agent_role(agent_type, **kwargs)
            
        elif agent_type == "criteria_gate":
            criteria_text = kwargs.get("criteria_text", "")
            content = f"""Success criteria suggested (see .agent-outputs/exploration.md for details):
{criteria_text[:200]}{'...' if len(criteria_text) > 200 else ''}"""
            role = AgentDefinitions.get_gate_role("criteria", content)
            
        elif agent_type == "completion_gate":
            status_line = kwargs.get("status_line", "")
            content = f"""Verification: {status_line}
(Full details in .agent-outputs/verification.md)"""
            role = AgentDefinitions.get_gate_role("completion", content)
            
        else:
            return "error", f"Unknown agent type: {agent_type}"
        
        # Update task status
        self.orchestrator._update_task_status(
            self.orchestrator._get_current_task(), 
            role["status"]
        )
        
        # Build instructions based on agent type
        if role["auto_continue"]:
            instructions = self.orchestrator._build_agent_instructions(
                role["name"].lower(),
                role["primary_objective"], 
                role["work_section"],
                role["completion_phrase"]
            )
        else:
            instructions = self.orchestrator._build_gate_instructions(
                role["name"].split("_")[0],  # "CRITERIA" from "CRITERIA_GATE"
                role["content"],
                role["options"] 
            )
            
        return role["name"].lower(), instructions


class ClaudeDrivenOrchestrator:
    def __init__(self):
        self.project_root = Path.cwd()
        self.agents_dir = self.project_root / ".claude-agents"
        self.outputs_dir = self.project_root / ".agent-outputs"
        
        # Task tracking files in root directory
        self.tasks_file = self.project_root / "tasks.md"
        self.checklist_file = self.project_root / "tasks-checklist.md"
        
        # Initialize agent factory
        self.agent_factory = AgentFactory(self)
        
        # Ensure directories exist
        self.agents_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)

    def _echo_visible_message(self, message: str):
        """Print message that will be immediately visible to Claude without truncation"""
        print("\n" + "=" * 80)
        print(message)
        print("=" * 80)

    def _build_agent_instructions(self, agent_name: str, primary_objective: str, work_section: str, completion_phrase: str) -> str:
        """Build standardized agent instructions with primary objective framing"""
        return f"""PRIMARY OBJECTIVE: {primary_objective}

WORK TO COMPLETE FIRST:

FIRST: Run /clear to reset context

{work_section}

When complete, say "{completion_phrase}"

FINAL STEP: After completing all verification work above, use /orchestrate next

REMEMBER: Complete all verification work FIRST, then advance the workflow."""

    def _build_gate_instructions(self, gate_name: str, content: str, options: list) -> str:
        """Build standardized gate instructions with improved visibility"""
        options_text = '\n'.join(f"• {option}" for option in options)
        
        # Echo the gate info immediately for visibility
        self._echo_visible_message(f"""{gate_name.upper()} GATE: Human Review Required

{content}

AVAILABLE OPTIONS:
{options_text}

WORKFLOW PAUSED - Choose an option above""")
        
        return f"""{gate_name.upper()} GATE: Human Review Required

{content}

OPTIONS:
{options_text}

Paused - choose option above

Show the full output of last bash tool call

STOP: My instructions end here. I must wait for the human to choose one of the options above. I will not provide commentary, analysis, or summaries. The human will select an option."""

    def _retry_from_phase(self, phase_name: str, display_name: str = None):
        """Generic retry method for any phase"""
        if not display_name:
            display_name = phase_name.title()
            
        self._clean_from_phase(phase_name)
        print(f"Restarting from {display_name} phase")
        
        # Continue to next agent
        agent, instructions = self.get_next_agent()
        print(f"\n{'='*60}")
        print(f"RESTARTING FROM {agent.upper()}")
        print(f"{'='*60}")
        print(instructions)
        print(f"{'='*60}")
        
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
        return self.agent_factory.create_agent("explorer", task=task)
        
    def _prepare_criteria_gate(self) -> Tuple[str, str]:
        """Prepare criteria approval gate"""
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
            elif in_criteria and line.strip().startswith('##') and not line.strip().startswith('###'):
                break
            elif in_criteria:
                criteria_section.append(line)
        
        criteria_text = '\n'.join(criteria_section) if criteria_section else "No criteria found in exploration.md"
        return self.agent_factory.create_agent("criteria_gate", criteria_text=criteria_text)
        
    def _prepare_planner(self) -> Tuple[str, str]:
        """Prepare planner agent instructions"""
        return self.agent_factory.create_agent("planner")
        
    def _prepare_coder(self) -> Tuple[str, str]:
        """Prepare coder agent instructions"""
        return self.agent_factory.create_agent("coder")
        
    def _prepare_verifier(self) -> Tuple[str, str]:
        """Prepare verifier agent instructions"""
        return self.agent_factory.create_agent("verifier")
        
    def _prepare_completion_gate(self) -> Tuple[str, str]:
        """Prepare completion approval gate"""
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
        
        return self.agent_factory.create_agent("completion_gate", status_line=status_line)

    # GATE APPROVAL COMMANDS
    
    def approve_criteria(self):
        """Approve criteria and continue to Planner"""
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
                elif in_criteria and line.strip().startswith('##') and not line.strip().startswith('###'):
                    break
                elif in_criteria:
                    criteria_section.append(line)
            
            criteria_text = '\n'.join(criteria_section)
            criteria_file = self.outputs_dir / "success-criteria.md"
            criteria_file.write_text(f"# Approved Success Criteria\n\n{criteria_text}\n")
            
            print("Success criteria approved and saved")
            
            # Continue to next agent
            agent, instructions = self.get_next_agent()
            print(f"\n{'='*60}")
            print(f"CRITERIA APPROVED - CONTINUING TO {agent.upper()}")
            print(f"{'='*60}")
            print(instructions)
            print(f"{'='*60}")
            
    def modify_criteria(self, modification_request=None):
        """Set up criteria modification task for Claude and continue workflow"""
        if not modification_request:
            print("No modification request provided")
            print("Usage: /orchestrate modify-criteria \"your modification instructions\"")
            return
            
        # Read the current exploration results
        exploration_file = self.outputs_dir / "exploration.md"
        if not exploration_file.exists():
            print("No exploration.md found. Run the Explorer first.")
            return
            
        # Save the modification request for Claude to process
        modification_file = self.outputs_dir / "criteria-modification-request.md"
        modification_file.write_text(f"# Criteria Modification Request\n\n{modification_request}\n")
        
        # Set up a special "criteria modifier" agent task
        task = self._get_current_task()
        self._update_task_status(task, "MODIFYING CRITERIA")
        
        instructions = f"""FIRST: Run /clear to reset context

CRITERIA MODIFICATION TASK:

1. Read .agent-outputs/exploration.md to see the original suggested criteria
2. Read .agent-outputs/criteria-modification-request.md for the modification request
3. Apply the requested modifications to create updated success criteria
4. Write the final modified criteria to .agent-outputs/success-criteria.md

MODIFICATION REQUEST: {modification_request}

Output format for success-criteria.md:
# Approved Success Criteria

[Your modified criteria here - apply the modification request to the original suggestions]

When complete, say "CRITERIA MODIFICATION COMPLETE"

FINAL STEP: Run /clear to reset context, then run: /orchestrate next"""
        
        print(f"\n{'='*60}")
        print(f"CRITERIA MODIFICATION TASK READY")
        print(f"{'='*60}")
        print(instructions)
        print(f"{'='*60}")
        
        return "criteria_modifier", instructions
        
    def retry_explorer(self):
        """Restart from Explorer phase"""
        self._retry_from_phase("explorer")
        
    def approve_completion(self):
        """Approve completion and mark task done"""
        task = self._get_current_task()
        if task:
            self._update_task_status(task, "COMPLETE")
            self._update_checklist(task, completed=True)
            approval_file = self.outputs_dir / "completion-approved.md"
            approval_file.write_text(f"# Task Completion Approved\n\nTask: {task}\nApproved at: {datetime.now().isoformat()}\n")
            
            print(f"\n{'='*60}")
            print("TASK COMPLETED SUCCESSFULLY!")
            print(f"{'='*60}")
            print(f"Task marked complete: {task}")
            print("Updated tasks.md and tasks-checklist.md")
            print("Check .agent-outputs/verification.md for final results")
            print("Run /orchestrate clean to prepare for next task")
            print(f"{'='*60}")
            
    def retry_from_planner(self):
        """Restart from Planner phase (keep criteria)"""
        self._retry_from_phase("planner", "Planner (keeping criteria)")
        
    def retry_from_coder(self):
        """Restart from Coder phase (keep plan)"""
        self._retry_from_phase("coder", "Coder (keeping plan)")
        
    def retry_from_verifier(self):
        """Restart just Verifier phase (keep changes)"""
        self._retry_from_phase("verifier", "Verifier (keeping changes)")
        
    # UTILITY METHODS
    
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
            self._update_task_status(task, f"RETRY FROM {phase.upper()}")
        
    def mark_complete(self, success: bool = True):
        """Mark current task as complete or failed"""
        
        task = self._get_current_task()
        if not task:
            return
            
        if success:
            self._update_task_status(task, "COMPLETE")
            self._update_checklist(task, completed=True)
            print(f"\nTask marked complete: {task}")
        else:
            self._update_task_status(task, "NEEDS REVIEW")
            print(f"\nTask needs review: {task}")
            
    def clean_outputs(self):
        """Clean output directory for fresh run"""
        
        # Only clean known orchestrator files
        orchestrator_files = [
            "exploration.md",
            "success-criteria.md", 
            "plan.md",
            "changes.md", 
            "verification.md",
            "completion-approved.md",
            "criteria-modification-request.md"
        ]
        
        cleaned_count = 0
        for filename in orchestrator_files:
            filepath = self.outputs_dir / filename
            if filepath.exists():
                filepath.unlink()
                cleaned_count += 1
                
        print(f"Cleaned {cleaned_count} orchestrator files from .agent-outputs/")
        
    def status(self):
        """Show current orchestration status by writing to file and calling showstatus"""
        
        status_info = "Orchestration Status:\n"
        status_info += "-" * 50 + "\n"
        
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
                status_info += f"✓ {agent:<15} complete ({size} bytes)\n"
            else:
                status_info += f"⏳ {agent:<15} pending\n"
                
        current_task = self._get_current_task()
        if current_task:
            status_info += f"\nCurrent task: {current_task[:60]}"
            
        # Write status to file
        status_file = self.outputs_dir / "current-status.md"
        status_file.write_text(f"# Current Orchestration Status\n\n{status_info}\n")
        
        print("Status written to .agent-outputs/current-status.md")
        print("/orchestrate showstatus")
            
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
                    if status == "COMPLETE":
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
        command = "start"  # Default to start when no arguments provided
    else:
        command = sys.argv[1]
    
    # Basic workflow commands
    if command == "start":
        # Start fresh: clean outputs then begin
        orchestrator.clean_outputs()
        agent, instructions = orchestrator.get_next_agent()
        print(f"\n{'='*60}")
        print(f"STARTING FRESH - AGENT: {agent.upper()}")
        print(f"{'='*60}")
        print(instructions)
        print(f"{'='*60}")
        
    elif command == "next":
        agent, instructions = orchestrator.get_next_agent()
        print(f"\n{'='*60}")
        print(f"AGENT: {agent.upper()}")
        print(f"{'='*60}")
        print(instructions)
        print(f"{'='*60}")
        
    elif command == "status":
        orchestrator.status()
        
    elif command == "showstatus":
        status_file = orchestrator.outputs_dir / "current-status.md"
        if status_file.exists():
            content = status_file.read_text()
            print(content)
        else:
            print("No status file found. Run /orchestrate status first.")
            
    elif command == "showcriteria":
        criteria_file = orchestrator.outputs_dir / "current-criteria-gate.md"
        if criteria_file.exists():
            content = criteria_file.read_text()
            print(content)
        else:
            print("No criteria gate file found. No criteria gate currently active.")
            
    elif command == "showcompletion":
        completion_file = orchestrator.outputs_dir / "current-completion-gate.md"
        if completion_file.exists():
            content = completion_file.read_text()
            print(content)
        else:
            print("No completion gate file found. No completion gate currently active.")
        
    elif command == "clean":
        orchestrator.clean_outputs()
        
    elif command == "complete":
        orchestrator.mark_complete(success=True)
        
    elif command == "fail":
        orchestrator.mark_complete(success=False)
        
    # Gate approval commands
    elif command == "approve-criteria":
        orchestrator.approve_criteria()
        
    elif command == "modify-criteria":
        # Get modification request from remaining arguments
        if len(sys.argv) > 2:
            modification_request = " ".join(sys.argv[2:])
            orchestrator.modify_criteria(modification_request)
        else:
            orchestrator.modify_criteria()
        
    elif command == "retry-explorer":
        orchestrator.retry_explorer()
        
    elif command == "approve-completion":
        orchestrator.approve_completion()
        
    elif command == "retry-from-planner":
        orchestrator.retry_from_planner()
        
    elif command == "retry-from-coder":
        orchestrator.retry_from_coder()
        
    elif command == "retry-from-verifier":
        orchestrator.retry_from_verifier()
        
    else:
        print(f"Unknown command: {command}")
        print("\nAvailable commands:")
        print("  Workflow: start, next, status, clean, complete, fail")
        print("  Gates: approve-criteria, modify-criteria, retry-explorer")
        print("         approve-completion, retry-from-planner, retry-from-coder, retry-from-verifier")


if __name__ == "__main__":
    main()