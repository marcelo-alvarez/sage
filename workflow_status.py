#!/usr/bin/env python3
"""
Shared Workflow Status Module for Claude Code Orchestrator
Provides consistent workflow state reading and parsing for both CLI and web UI
"""

import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any


class StatusReader:
    """Reads and parses workflow status from orchestrator files"""
    
    def __init__(self, project_root: Path = None):
        self.status_emoji_map = {
            '⏳': 'pending',
            '✅': 'completed',
            '✓': 'completed',
            '🔄': 'in-progress'
        }
        # Use provided project_root or fall back to current working directory
        self.project_root = project_root if project_root is not None else Path(os.getcwd())
        # File lock for thread-safe operations  
        self._file_lock = threading.RLock()

    def __del__(self):
        """Clean up resources on destruction"""
        pass

    def _get_current_mode(self) -> str:
        """Detect current mode by checking for .agent-outputs-meta directory existence"""
        meta_dir = self.project_root / '.agent-outputs-meta'
        return 'meta' if meta_dir.exists() else 'regular'

    def _get_outputs_dir(self, mode: str = None) -> Path:
        """Get appropriate outputs directory based on mode"""
        if mode is None:
            mode = self._get_current_mode()
        return self.project_root / ('.agent-outputs-meta' if mode == 'meta' else '.agent-outputs')

    def _get_claude_dir(self, mode: str = None) -> Path:
        """Get appropriate claude directory based on mode"""
        if mode is None:
            mode = self._get_current_mode()
        return self.project_root / ('.claude-meta' if mode == 'meta' else '.claude')

    def _read_file_safely(self, file_path: Path, encoding='utf-8') -> str:
        """Thread-safe file reading with proper error handling"""
        # Use direct file read instead of ThreadPoolExecutor to avoid deadlocks
        # when multiple API servers are competing for resources
        try:
            if not file_path.exists():
                return None
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f"[StatusReader] Error reading file {file_path}: {e}")
            return None
        
    def read_status(self, mode=None):
        """Read workflow status from appropriate directory"""
        if mode is None:
            mode = self._get_current_mode()
        outputs_dir = self._get_outputs_dir(mode)
        status_file = outputs_dir / 'current-status.md'
        
        print(f"[StatusReader] Reading status for mode '{mode}' from {status_file}")
        
        try:
            # Use thread-safe file reading
            content = self._read_file_safely(status_file)
            
            if content is None:
                print(f"[StatusReader] Status file does not exist or failed to read: {status_file}")
                return self._get_default_status(mode)
            
            print(f"[StatusReader] Read {len(content)} characters from status file")
            
            if not content.strip():
                print(f"[StatusReader] Status file is empty, using default status")
                return self._get_default_status(mode)
                
            parsed_status = self._parse_status_content(content, mode)
            print(f"[StatusReader] Successfully parsed status with {len(parsed_status.get('workflow', []))} workflow items")
            return parsed_status
            
        except Exception as e:
            print(f"[StatusReader] Error reading status file {status_file}: {e}")
            return self._get_default_status(mode)
    
    def _parse_status_content(self, content, mode='regular'):
        """Parse markdown status content into structured data"""
        lines = content.strip().split('\n')
        
        # Extract current task (last non-empty line usually)
        current_task = "No task specified"
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('⏳') and not line.startswith('✅') and not line.startswith('🔄'):
                if line.startswith('Current task:'):
                    current_task = line.replace('Current task:', '').strip()
                    break
                elif not any(emoji in line for emoji in self.status_emoji_map.keys()):
                    current_task = line
                    break
        
        # Parse workflow steps
        workflow = []
        agents = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Look for status lines with emojis
            for emoji, status in self.status_emoji_map.items():
                if line.startswith(emoji):
                    agent_name = line.replace(emoji, '').strip()
                    
                    # Clean up agent name by removing status info and file sizes
                    # Format: "Explorer        complete (2727 bytes)" -> "Explorer"
                    if ' complete (' in agent_name:
                        agent_name = agent_name.split(' complete (')[0].strip()
                    elif ' pending' in agent_name:
                        agent_name = agent_name.split(' pending')[0].strip()
                    elif ' running' in agent_name:
                        agent_name = agent_name.split(' running')[0].strip()
                    elif ' active' in agent_name:
                        agent_name = agent_name.split(' active')[0].strip()
                    
                    # Determine agent type
                    agent_type = 'gate' if 'gate' in agent_name.lower() else 'agent'
                    
                    # Special logic for Completion Gate: check if it should be active
                    if agent_name == "Completion Gate" and status == 'pending':
                        # Check if all previous steps are complete
                        if self._is_completion_gate_active(workflow):
                            status = 'in-progress'  # Change to active
                    
                    # Special logic for Criteria Gate: if User Validation Gate exists or all agents are complete, Criteria Gate should not be active
                    if agent_name == "Criteria Gate" and status == 'in-progress':
                        if self._has_user_validation_gate(mode):
                            # User Validation supersedes Criteria Gate activity
                            status = 'completed'
                        else:
                            # Check if all required agents are complete by looking at the original file content
                            required_agents = ['Explorer', 'Planner', 'Coder', 'Verifier']
                            all_agents_complete = True
                            for required_agent in required_agents:
                                agent_found = False
                                # Check in the original lines, not the partially built workflow
                                for check_line in lines:
                                    check_line = check_line.strip()
                                    if (required_agent.lower() in check_line.lower() and 
                                        ('✅' in check_line or '✓' in check_line or 'complete' in check_line.lower())):
                                        agent_found = True
                                        break
                                if not agent_found:
                                    all_agents_complete = False
                                    break
                            
                            if all_agents_complete:
                                # If all agents are complete, Criteria Gate should be complete and Completion Gate should be active
                                status = 'completed'
                    
                    # Add to workflow
                    workflow_item = {
                        'name': agent_name,
                        'status': status,
                        'type': agent_type,
                        'icon': self._get_agent_icon(agent_name)
                    }
                    workflow.append(workflow_item)
                    
                    # Add to agents if not a gate
                    if agent_type == 'agent':
                        agent_item = {
                            'name': agent_name,
                            'status': status,
                            'description': self._get_agent_description(agent_name, status)
                        }
                        agents.append(agent_item)
                    
                    break
        
        # Add User Validation Gate as separate item if it exists
        if self._has_user_validation_gate(mode):
            user_validation_item = {
                'name': 'User Validation Gate',
                'status': 'in-progress',
                'type': 'gate', 
                'icon': '👤'
            }
            workflow.append(user_validation_item)
        
        # Check for workflow completion
        is_complete = self._is_workflow_complete(mode)
        
        return {
            'currentTask': current_task,
            'workflow': workflow,
            'agents': agents,
            'workflowComplete': is_complete
        }
    
    def _is_completion_gate_active(self, workflow):
        """Check if Completion Gate should be active based on previous steps"""
        required_agents = ['Explorer', 'Planner', 'Coder', 'Verifier']
        
        for required_agent in required_agents:
            # Find this agent in workflow
            agent_found = False
            for item in workflow:
                if required_agent.lower() in item['name'].lower() and item['status'] == 'completed':
                    agent_found = True
                    break
            
            # If any required agent is not complete, Completion Gate should not be active
            if not agent_found:
                return False
        
        return True
    
    def _has_user_validation_gate(self, mode: str = None):
        """Check if pending-user_validation-gate.md exists"""
        if mode is None:
            mode = self._get_current_mode()
        outputs_dir = self._get_outputs_dir(mode)
        validation_file = outputs_dir / 'pending-user_validation-gate.md'
        return validation_file.exists()
    
    def has_pending_gate(self, gate_type: str, mode: str = None) -> bool:
        """Check if a specific pending gate file exists"""
        if mode is None:
            mode = self._get_current_mode()
        outputs_dir = self._get_outputs_dir(mode)
        pending_gate_file = outputs_dir / f'pending-{gate_type}-gate.md'
        return pending_gate_file.exists()
    
    def get_pending_gates(self, mode: str = None) -> List[str]:
        """Get list of all pending gate types"""
        if mode is None:
            mode = self._get_current_mode()
        gate_types = ['criteria', 'completion', 'user_validation']
        pending_gates = []
        
        for gate_type in gate_types:
            if self.has_pending_gate(gate_type, mode):
                pending_gates.append(gate_type)
        
        return pending_gates
    
    def _is_workflow_complete(self, mode=None):
        """Check if workflow has been completed (completion approved or all checklist tasks done)"""        
        if mode is None:
            mode = self._get_current_mode()
        # Use mode-specific directories with absolute paths based on project_root
        outputs_dir = self._get_outputs_dir(mode)
        claude_dir = self._get_claude_dir(mode)
        
        # Check for standard completion approval
        completion_file = outputs_dir / 'completion-approved.md'
        if completion_file.exists():
            return True
        
        # Check if all checklist tasks are complete
        checklist_file = claude_dir / 'tasks-checklist.md'
        print(f"[DEBUG] StatusReader project_root: {self.project_root.absolute()}")
        print(f"[DEBUG] Checking checklist file: {checklist_file.absolute()}")
        print(f"[DEBUG] File exists: {checklist_file.exists()}")
        if checklist_file.exists():
            content = self._read_file_safely(checklist_file)
            if content is None:
                return False
            lines = content.split('\n')
            
            # Find all task lines
            has_tasks = False
            all_complete = True
            
            print(f"[DEBUG] Checking checklist completion: {checklist_file}")
            for line in lines:
                # Look for task lines: - [ ] or - [x]
                if re.match(r'^\s*-\s*\[[x ]\]', line):
                    has_tasks = True
                    print(f"[DEBUG] Found task: {line.strip()[:60]}...")
                    if not re.match(r'^\s*-\s*\[x\]', line):
                        all_complete = False
                        print(f"[DEBUG] Task not complete")
                        break
            
            print(f"[DEBUG] has_tasks: {has_tasks}, all_complete: {all_complete}")
            # If we have tasks and they're all complete, workflow is done
            if has_tasks and all_complete:
                print(f"[DEBUG] Workflow complete via checklist!")
                return True
        
        return False
    
    def get_current_outputs_status(self, mode=None) -> Dict[str, bool]:
        """Get current outputs status dict (used by orchestrate.py completion detection)"""
        if mode is None:
            mode = self._get_current_mode()
        outputs_dir = self._get_outputs_dir(mode)
        
        return {
            "exploration.md": (outputs_dir / "exploration.md").exists(),
            "success-criteria.md": (outputs_dir / "success-criteria.md").exists(),
            "plan.md": (outputs_dir / "plan.md").exists(),
            "changes.md": (outputs_dir / "changes.md").exists(),
            "orchestrator-log.md": (outputs_dir / "orchestrator-log.md").exists(),
            "verification.md": (outputs_dir / "verification.md").exists(),
            "scribe.md": (outputs_dir / "scribe.md").exists() or (outputs_dir / "scribe-fallback.md").exists(),
            "completion-approved.md": (outputs_dir / "completion-approved.md").exists()
        }
    
    def _get_agent_icon(self, agent_name):
        """Get appropriate icon for agent"""
        icon_map = {
            'explorer': '🔍',
            'criteria gate': '🚪', 
            'planner': '📋',
            'coder': '💻',
            'scribe': '📝',
            'verifier': '✅',
            'completion gate': '🏁'
        }
        return icon_map.get(agent_name.lower(), '⚙️')
    
    def _get_agent_description(self, agent_name, status):
        """Get description for agent based on name and status"""
        base_descriptions = {
            'explorer': 'Analyzes task requirements and identifies patterns, dependencies, and constraints.',
            'planner': 'Creates detailed implementation plan with step-by-step approach and success criteria.',
            'coder': 'Implements the planned changes according to specifications.',
            'scribe': 'Documents the implementation and creates usage instructions.',
            'verifier': 'Tests functionality and verifies all success criteria are met.'
        }
        
        base = base_descriptions.get(agent_name.lower(), f'Handles {agent_name.lower()} responsibilities.')
        
        if status == 'completed':
            return base.replace('Creates', 'Created').replace('Analyzes', 'Analyzed').replace('Implements', 'Implemented').replace('Documents', 'Documented').replace('Tests', 'Tested')
        elif status == 'in-progress':
            return f'Currently working: {base}'
        else:
            return f'Will handle: {base}'
    
    def _get_current_task_from_checklist(self, mode=None):
        """Extract the first uncompleted task from checklist as current task"""
        if mode is None:
            mode = self._get_current_mode()
        claude_dir = self._get_claude_dir(mode)
        checklist_file = claude_dir / 'task-checklist.md'  # Fixed: removed 's' from tasks
        
        if not checklist_file.exists():
            # If checklist doesn't exist, check for alternative task sources
            return self._get_current_task_from_alternatives(mode)
        
        content = self._read_file_safely(checklist_file)
        if content is None:
            return self._get_current_task_from_alternatives(mode)
        
        lines = content.split('\n')
        for line in lines:
            # Look for incomplete task lines: - [ ]
            if re.match(r'^\s*-\s*\[\s\]', line):
                # Extract task text and clean it up
                task_text = re.sub(r'^\s*-\s*\[\s\]\s*', '', line).strip()
                if task_text:
                    # Return full text without truncation
                    return task_text
        
        return self._get_current_task_from_alternatives(mode)
    
    def _get_current_task_from_alternatives(self, mode=None):
        """Get current task from alternative sources when checklist doesn't exist or has no tasks"""
        if mode is None:
            mode = self._get_current_mode()
        # Check for current task in status file first
        outputs_dir = self._get_outputs_dir(mode)
        status_file = outputs_dir / 'current-status.md'
        
        if status_file.exists():
            content = self._read_file_safely(status_file)
            if content:
                lines = content.strip().split('\n')
                # Look for explicit current task lines
                for line in lines:
                    line = line.strip()
                    if line.startswith('Current task:') or line.startswith('**Current task:**'):
                        task_text = re.sub(r'^(\*\*)?Current task:(\*\*)?\s*', '', line).strip()
                        if task_text and len(task_text) > 3:  # Avoid very short/empty tasks
                            return task_text
        
        # Check for active tasks in output files
        task_sources = [
            ('plan.md', 'Planning phase in progress'),
            ('changes.md', 'Implementation phase in progress'), 
            ('verification.md', 'Verification phase in progress'),
            ('exploration.md', 'Exploration phase in progress')
        ]
        
        for filename, default_task in task_sources:
            file_path = outputs_dir / filename
            if file_path.exists():
                content = self._read_file_safely(file_path)
                if content and len(content.strip()) > 10:  # File has substantial content
                    # Try to extract a meaningful task description from the file
                    lines = content.strip().split('\n')[:10]  # Check first 10 lines
                    for line in lines:
                        line = line.strip()
                        # Look for task-like lines (not just headers or metadata)
                        if (line and not line.startswith('#') and not line.startswith('**') 
                            and len(line) > 20 and not line.startswith('---')):
                            # Clean up and use this line as task
                            clean_line = re.sub(r'^\d+\.\s*', '', line)  # Remove numbered list prefix
                            clean_line = re.sub(r'^[-*]\s*', '', clean_line)  # Remove bullet points
                            if len(clean_line) > 15:  # Ensure it's substantial
                                return clean_line
                    
                    # If no good line found, use the default task for this phase
                    return default_task
        
        # Final fallback - check if we're in a workflow state by examining any .agent-outputs files
        if any(f.exists() for f in outputs_dir.glob('*.md') if f.name != 'current-status.md'):
            return f"Workflow in progress ({mode} mode)"
        
        return 'No active task'
    
    def _get_default_status(self, mode=None):
        """Return default status when files are missing"""
        if mode is None:
            mode = self._get_current_mode()
        # Check for uncompleted checklist tasks first
        current_task = self._get_current_task_from_checklist(mode)
        
        return {
            'currentTask': current_task,
            'workflow': [
                {'name': 'Explorer', 'status': 'pending', 'type': 'agent', 'icon': '🔍'},
                {'name': 'Criteria Gate', 'status': 'pending', 'type': 'gate', 'icon': '🚪'},
                {'name': 'Planner', 'status': 'pending', 'type': 'agent', 'icon': '📋'},
                {'name': 'Coder', 'status': 'pending', 'type': 'agent', 'icon': '💻'},
                {'name': 'Scribe', 'status': 'pending', 'type': 'agent', 'icon': '📝'},
                {'name': 'Verifier', 'status': 'pending', 'type': 'agent', 'icon': '✅'},
                {'name': 'Completion Gate', 'status': 'pending', 'type': 'gate', 'icon': '🏁'}
            ],
            'agents': [
                {'name': 'Explorer', 'status': 'pending', 'description': 'Will analyze task requirements and identify patterns, dependencies, and constraints.'},
                {'name': 'Planner', 'status': 'pending', 'description': 'Will create detailed implementation plan with step-by-step approach and success criteria.'},
                {'name': 'Coder', 'status': 'pending', 'description': 'Will implement the planned changes according to specifications.'},
                {'name': 'Scribe', 'status': 'pending', 'description': 'Will document the implementation and create usage instructions.'},
                {'name': 'Verifier', 'status': 'pending', 'description': 'Will test functionality and verify all success criteria are met.'}
            ],
            'workflowComplete': False
        }


def get_workflow_status(project_root: Path = None, mode: str = None) -> Dict[str, Any]:
    """
    Unified function to get workflow status - used by both orchestrate.py and api_server.py
    
    Args:
        project_root: Project root directory (defaults to current working directory)
        mode: 'regular' or 'meta' mode (defaults to auto-detection based on directory state)
    
    Returns:
        Dict containing currentTask, workflow, agents, workflowComplete, and additional state info
    """
    reader = StatusReader(project_root)
    if mode is None:
        mode = reader._get_current_mode()
    status = reader.read_status(mode)
    
    # Add additional state information for consistency
    status['pendingGates'] = reader.get_pending_gates(mode)
    status['currentOutputs'] = reader.get_current_outputs_status(mode)
    
    return status