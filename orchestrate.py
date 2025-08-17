#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extensible Claude-Driven Orchestrator (Version 2)
Implements configurable agent types and workflow sequences
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import re
import sys
import atexit
import subprocess
import webbrowser
import time
import socket
import argparse


def find_available_port(start_port: int, max_attempts: int = 20) -> int:
    """Find an available port starting from start_port"""
    # Try the requested range first
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    # If no ports in requested range, try higher ranges
    if start_port == 8000:
        # Try higher range for API server
        for port in range(9000, 9020):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('localhost', port))
                    return port
            except OSError:
                continue
    elif start_port == 5678:
        # Try higher range for dashboard server
        for port in range(6000, 6020):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('localhost', port))
                    return port
            except OSError:
                continue
    
    raise OSError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")


class OrchestratorDashboard:
    """Web dashboard for workflow visualization and gate control"""
    
    def __init__(self):
        self.current_gate = None
        self.gate_decision = None
        
    def set_gate(self, gate_name: str, content: str, options: List[str]):
        """Set current gate information for dashboard display"""
        self.current_gate = {
            'gate_name': gate_name,
            'content': content,
            'options': options
        }
    
    def set_gate_decision(self, decision):
        """Set the gate decision value"""
        self.gate_decision = decision
    
    def wait_for_gate_decision(self, timeout=30):
        """Poll for gate decision with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.gate_decision is not None:
                return self.gate_decision
            time.sleep(1)
        
        return None


@dataclass
class AgentTemplate:
    """Template for agent definitions"""
    name: str
    work_section: str
    completion_phrase: str
    primary_objective: str
    auto_continue: bool = True
    variables: List[str] = None
    description: str = ""
    capabilities: List[str] = None
    requirements: List[str] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []
        if self.capabilities is None:
            self.capabilities = []
        if self.requirements is None:
            self.requirements = []


@dataclass
class AgentRole:
    """Role-based agent framework"""
    template: AgentTemplate
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
            
    def validate_requirements(self) -> bool:
        """Validate that all requirements are met"""
        # Basic validation - can be extended
        return True
        
    def substitute_variables(self, **kwargs) -> str:
        """Substitute template variables with provided values"""
        work_section = self.template.work_section
        for var_name, var_value in kwargs.items():
            # Handle both {var} and {{var}} formats
            work_section = work_section.replace('{{' + var_name + '}}', str(var_value))
            work_section = work_section.replace('{' + var_name + '}', str(var_value))
        return work_section


class AgentConfig:
    """Configuration manager for agent definitions"""
    
    def __init__(self, config_path: Path = None, enable_dashboard: bool = True, dashboard_port: int = 5678, api_port: int = 8000, no_browser: bool = False):
        self.config_path = config_path or Path('.claude/agent-config.json')
        self.templates_dir = Path('templates/agents')
        self.agents = {}
        self.enable_dashboard = enable_dashboard
        self.dashboard_port = dashboard_port
        self.api_port = api_port
        self.no_browser = no_browser
        self.dashboard_process = None
        self.api_process = None
        self.dashboard = None
        self.dashboard_available = False
        self._load_config()
        
        if self.enable_dashboard:
            self.dashboard = OrchestratorDashboard()
            self.start_dashboard()
        
    def _load_config(self):
        """Load agent configuration from JSON file and template files"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    self._parse_config(config_data)
                # Always load template files in addition to config file
                self._load_from_templates()
            except Exception as e:
                print(f"Warning: Failed to load agent config: {e}")
                self._load_defaults()
        else:
            self._load_defaults()
            
    def _parse_config(self, config_data: Dict[str, Any]):
        """Parse configuration data into AgentTemplate objects"""
        agents_data = config_data.get('agents', {})
        
        for agent_name, agent_data in agents_data.items():
            template = AgentTemplate(
                name=agent_name,
                work_section=agent_data.get('work_section', ''),
                completion_phrase=agent_data.get('completion_phrase', f'{agent_name.upper()} COMPLETE'),
                primary_objective=agent_data.get('primary_objective', ''),
                auto_continue=agent_data.get('auto_continue', True),
                variables=agent_data.get('variables', []),
                description=agent_data.get('description', ''),
                capabilities=agent_data.get('capabilities', []),
                requirements=agent_data.get('requirements', [])
            )
            self.agents[agent_name] = template
            
    def _load_defaults(self):
        """Load default agent configurations as fallback"""
        # Load from template files if available
        self._load_from_templates()
        
    def _load_from_templates(self):
        """Load agent definitions from template files"""
        # Scan all subdirectories in templates/agents/ for custom agents
        if self.templates_dir.exists():
            for agent_dir in self.templates_dir.iterdir():
                if agent_dir.is_dir():
                    agent_type = agent_dir.name
                    template_path = agent_dir / 'CLAUDE.md'
                    if template_path.exists():
                        try:
                            content = template_path.read_text()
                            template = self._parse_template_file(agent_type, content)
                            # Validate template before adding
                            if self.validate_template(template):
                                # Only add if not already loaded from config file (config takes precedence)
                                if agent_type not in self.agents:
                                    self.agents[agent_type] = template
                                else:
                                    print(f"Info: Skipping template {agent_type} - already loaded from config")
                            else:
                                print(f"Warning: Template validation failed for {agent_type}")
                        except Exception as e:
                            print(f"Warning: Failed to load template for {agent_type}: {e}")
                    
    def _parse_template_file(self, agent_name: str, content: str) -> AgentTemplate:
        """Parse template file content into AgentTemplate"""
        # Extract all variables from template content using regex
        variables = []
        import re
        
        # Find all {{variable}} patterns
        double_brace_vars = re.findall(r'\{\{([^}]+)\}\}', content)
        # Find all {variable} patterns (excluding double braces)
        single_brace_vars = re.findall(r'(?<!\{)\{([^{}]+)\}(?!\})', content)
        
        # Combine and deduplicate variables
        all_vars = list(set(double_brace_vars + single_brace_vars))
        variables = [var.strip() for var in all_vars if var.strip()]
            
        # Extract completion phrase if present - look for multiple patterns
        completion_phrase = f'{agent_name.upper()} COMPLETE'
        for line in content.split('\n'):
            line_lower = line.lower()
            # Look for "When complete, output:" or "When complete, say"
            if ('complete' in line_lower and ('output:' in line_lower or 'say' in line_lower)):
                # Extract completion phrase from lines like "When complete, output: EXPLORER COMPLETE"
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        phrase = parts[1].strip().strip('"').strip("'")
                        if phrase:
                            completion_phrase = phrase
                            break
                    
        return AgentTemplate(
            name=agent_name,
            work_section=content,
            completion_phrase=completion_phrase,
            primary_objective=f"Complete {agent_name} work according to responsibilities",
            auto_continue=True,
            variables=variables,
            description=f"{agent_name.title()} agent for orchestrated workflows",
            capabilities=[f"{agent_name}_operations"],
            requirements=[]
        )
        
    def validate_template(self, template: AgentTemplate) -> bool:
        """Validate that template has required fields and proper structure"""
        try:
            # Check required fields are not empty
            if not template.name or not template.name.strip():
                print(f"Template validation failed: Missing agent name")
                return False
                
            if not template.work_section or not template.work_section.strip():
                print(f"Template validation failed: Missing work_section for {template.name}")
                return False
                
            if not template.completion_phrase or not template.completion_phrase.strip():
                print(f"Template validation failed: Missing completion_phrase for {template.name}")
                return False
            
            # Check that work_section contains some basic structure
            work_section = template.work_section.lower()
            if 'responsibilities' not in work_section and 'responsibility' not in work_section:
                print(f"Warning: Template for {template.name} may be missing responsibilities section")
            
            # Check for forbidden actions section (good practice but not required)
            if 'forbidden' not in work_section:
                print(f"Info: Template for {template.name} doesn't specify forbidden actions")
            
            # Validate completion phrase format
            if template.completion_phrase.upper() != template.completion_phrase:
                print(f"Warning: Completion phrase for {template.name} should be uppercase: {template.completion_phrase}")
            
            return True
            
        except Exception as e:
            print(f"Template validation error for {template.name}: {e}")
            return False
        
    def get_agent_template(self, agent_type: str) -> Optional[AgentTemplate]:
        """Get agent template by type"""
        return self.agents.get(agent_type)
        
    def get_available_agents(self) -> List[str]:
        """Get list of available agent types"""
        return list(self.agents.keys())
        
    def save_config(self):
        """Save current configuration to JSON file"""
        config_data = {
            'agents': {}
        }
        
        for agent_name, template in self.agents.items():
            config_data['agents'][agent_name] = {
                'work_section': template.work_section,
                'completion_phrase': template.completion_phrase,
                'primary_objective': template.primary_objective,
                'auto_continue': template.auto_continue,
                'variables': template.variables,
                'description': template.description,
                'capabilities': template.capabilities,
                'requirements': template.requirements
            }
            
        # Ensure directory exists
        self.config_path.parent.mkdir(exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def start_dashboard(self):
        """Start dashboard and API servers as subprocesses"""
        try:
            # Find available ports
            try:
                self.api_port = find_available_port(self.api_port)
                self.dashboard_port = find_available_port(self.dashboard_port)
            except OSError as e:
                print(f"Warning: Dashboard unavailable - {e}")
                print("Orchestrator will continue without web dashboard")
                self.dashboard_available = False
                return
                
            # Start API server as subprocess (without --background since subprocess IS the background)
            self.api_process = subprocess.Popen([
                sys.executable, 'api_server.py', 
                '--port', str(self.api_port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print(f"API server started as subprocess (PID: {self.api_process.pid}) on port {self.api_port}")
            
            # Start dashboard server as subprocess
            self.dashboard_process = subprocess.Popen([
                sys.executable, 'test_dashboard_server.py', str(self.dashboard_port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print(f"Dashboard server started as subprocess (PID: {self.dashboard_process.pid}) on port {self.dashboard_port}")
            
            # Give servers time to start
            time.sleep(2)
            
            # Check if processes are still running
            api_running = self.api_process.poll() is None
            dashboard_running = self.dashboard_process.poll() is None
            
            if api_running and dashboard_running:
                # Always display dashboard URL
                print(f"Dashboard: http://localhost:{self.dashboard_port}/dashboard/index.html")
                self.dashboard_available = True
                
                # Open dashboard in browser if not suppressed
                if not self.no_browser:
                    try:
                        webbrowser.open(f'http://localhost:{self.dashboard_port}/dashboard/index.html')
                    except Exception as e:
                        print(f"Failed to open dashboard in browser: {e}")
                    
                # Register cleanup
                atexit.register(self.stop_dashboard)
                
            else:
                print("Warning: Dashboard servers failed to start properly")
                print("Orchestrator will continue without web dashboard")
                self.dashboard_available = False
                if not api_running:
                    # Non-blocking stderr read with timeout
                    try:
                        stderr_output = self.api_process.stderr.read(1000) if self.api_process.stderr else "No stderr"
                        print(f"API server failed - stderr: {stderr_output}")
                    except Exception as e:
                        print(f"API server failed - Could not read stderr: {e}")
                if not dashboard_running:
                    # Non-blocking stderr read with timeout  
                    try:
                        stderr_output = self.dashboard_process.stderr.read(1000) if self.dashboard_process.stderr else "No stderr"
                        print(f"Dashboard server failed - stderr: {stderr_output}")
                    except Exception as e:
                        print(f"Dashboard server failed - Could not read stderr: {e}")
                
        except Exception as e:
            print(f"Warning: Dashboard startup failed - {e}")
            print("Orchestrator will continue without web dashboard")
            self.dashboard_available = False
    
    def stop_dashboard(self):
        """Stop dashboard and API server subprocesses"""
        try:
            if self.dashboard_process:
                try:
                    self.dashboard_process.terminate()
                    self.dashboard_process.wait(timeout=5)
                    print("Dashboard server stopped")
                except:
                    try:
                        self.dashboard_process.kill()
                        print("Dashboard server force-killed")
                    except:
                        pass
                self.dashboard_process = None
                
            if self.api_process:
                try:
                    self.api_process.terminate()
                    self.api_process.wait(timeout=5)
                    print("API server stopped")
                except:
                    try:
                        self.api_process.kill()
                        print("API server force-killed")
                    except:
                        pass
                self.api_process = None
                
        except Exception as e:
            print(f"Error stopping servers: {e}")


# Legacy gate options - can be made configurable in future
GATE_OPTIONS = {
    "criteria": [
        "Execute the slash-command `/orchestrate approve-criteria` - Accept and continue",
        "Execute the slash-command `/orchestrate modify-criteria` - Modify criteria first",  
        "Execute the slash-command `/orchestrate retry-explorer` - Restart exploration"
    ],
    
    "completion": [
        "Execute the slash-command `/orchestrate approve-completion` - Mark complete",
        "Execute the slash-command `/orchestrate retry-explorer` - Restart all",
        "Execute the slash-command `/orchestrate retry-from-planner` - Restart from Planner",  
        "Execute the slash-command `/orchestrate retry-from-coder` - Restart from Coder",
        "Execute the slash-command `/orchestrate retry-from-verifier` - Re-verify only"
    ]
}



class AgentDefinitions:
    """Centralized agent role definitions using external configuration"""
    
    def __init__(self, agent_config: AgentConfig):
        self.agent_config = agent_config
    
    def get_work_agent_role(self, agent_type, **kwargs):
        """Generic method for work agents using configuration"""
        # Try to get from configuration first
        template = self.agent_config.get_agent_template(agent_type)
        
        if template:
            # Use configuration-based template
            role = AgentRole(template=template, context=kwargs)
            work_section = role.substitute_variables(**kwargs)
            
            return {
                "name": agent_type.upper(),
                "status": "🔄 " + agent_type.upper(),
                "completion_phrase": template.completion_phrase,
                "primary_objective": template.primary_objective,
                "work_section": work_section,
                "auto_continue": template.auto_continue
            }
        else:
            # Unknown agent type
            return None
    
    def get_gate_role(self, gate_type, content):
        """Generic method for gate agents"""
        return {
            "name": gate_type.upper() + "_GATE",
            "status": "🚪 " + gate_type.upper() + " GATE",
            "content": content,
            "options": GATE_OPTIONS[gate_type],
            "auto_continue": False
        }


class AgentFactory:
    """Factory for creating agent instructions with extensible agent support"""
    
    def __init__(self, orchestrator, agent_config: AgentConfig):
        self.orchestrator = orchestrator
        self.agent_config = agent_config
        self.agent_definitions = AgentDefinitions(agent_config)
        
    def get_available_agents(self) -> List[str]:
        """Get list of all available agent types"""
        config_agents = self.agent_config.get_available_agents()
        gate_agents = ["criteria_gate", "completion_gate"]
        
        # Combine and deduplicate
        all_agents = list(set(config_agents + gate_agents))
        return sorted(all_agents)
        
    def validate_agent_type(self, agent_type: str) -> bool:
        """Validate if agent type is supported"""
        return agent_type in self.get_available_agents()
        
    def create_agent(self, agent_type, **kwargs):
        """Create agent instructions based on type with validation"""
        
        # Validate agent type
        if not self.validate_agent_type(agent_type):
            available = ", ".join(self.get_available_agents())
            return "error", f"Unknown agent type: {agent_type}. Available types: {available}"
        
        # Handle work agents (explorer, planner, coder, verifier, and any custom agents)
        if agent_type in self.agent_config.get_available_agents():
            role = self.agent_definitions.get_work_agent_role(agent_type, **kwargs)
            
            if role is None:
                return "error", f"Failed to create agent role for type: {agent_type}"
            
        elif agent_type == "criteria_gate":
            criteria_text = kwargs.get("criteria_text", "")
            content = f"Success criteria suggested (see {self.orchestrator.outputs_dir}/exploration.md for details):\n" + \
                     (criteria_text[:200] + ('...' if len(criteria_text) > 200 else ''))
            role = self.agent_definitions.get_gate_role("criteria", content)
            
        elif agent_type == "completion_gate":
            status_line = kwargs.get("status_line", "")
            content = "Verification: " + status_line + f"\n(Full details in {self.orchestrator.outputs_dir}/verification.md)"
            role = self.agent_definitions.get_gate_role("completion", content)
            
        else:
            return "error", f"Unsupported agent type: {agent_type}"
        
        # Update task status
        self.orchestrator._update_task_status(
            self.orchestrator._get_current_task(), 
            role["status"]
        )
        
        # Update status file to reflect current workflow state
        self.orchestrator._update_status_file()
        
        # Build instructions based on agent type
        if role.get("auto_continue", True):
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


class WorkflowConfig:
    """Configuration manager for workflow definitions"""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path('.claude/workflow-config.json')
        self.sequence = ["explorer", "criteria_gate", "planner", "coder", "scribe", "verifier", "completion_gate"]
        self.gates = {
            "criteria": {
                "after": "explorer",
                "options": [
                    "Execute the slash-command `/orchestrate approve-criteria` - Accept and continue",
                    "Execute the slash-command `/orchestrate modify-criteria` - Modify criteria first",
                    "Execute the slash-command `/orchestrate retry-explorer` - Restart exploration"
                ]
            },
            "completion": {
                "after": "verifier",
                "options": [
                    "Execute the slash-command `/orchestrate approve-completion` - Mark complete",
                    "Execute the slash-command `/orchestrate retry-explorer` - Restart all",
                    "Execute the slash-command `/orchestrate retry-from-planner` - Restart from Planner",
                    "Execute the slash-command `/orchestrate retry-from-coder` - Restart from Coder",
                    "Execute the slash-command `/orchestrate retry-from-verifier` - Re-verify only"
                ]
            }
        }
        self._load_config()
        
    def _load_config(self):
        """Load workflow configuration from JSON file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    self.sequence = config_data.get('sequence', self.sequence)
                    self.gates = config_data.get('gates', self.gates)
            except Exception as e:
                print(f"Warning: Failed to load workflow config: {e}")
                
    def get_next_agent(self, current_outputs: Dict[str, bool]) -> Optional[str]:
        """Get next agent in sequence based on current outputs"""
        for agent_type in self.sequence:
            if agent_type.endswith('_gate'):
                gate_name = agent_type.replace('_gate', '')
                if gate_name in self.gates:
                    # Check if prerequisite is complete but gate not approved
                    prerequisite = self.gates[gate_name].get('after')
                    if prerequisite:
                        # Map agent type to output file
                        prereq_file = self._get_output_file(prerequisite)
                        if current_outputs.get(prereq_file, False):
                            approval_file = f"{gate_name}-approved.md" if gate_name == "completion" else "success-criteria.md"
                            if not current_outputs.get(approval_file, False):
                                return agent_type
            else:
                # Regular agent - check if output file exists
                output_file = self._get_output_file(agent_type)
                if not current_outputs.get(output_file, False):
                    return agent_type
                    
        return None  # All complete
        
    def _get_output_file(self, agent_type: str) -> str:
        """Map agent type to its output file"""
        if agent_type == "explorer":
            return "exploration.md"
        elif agent_type == "planner":
            return "plan.md"
        elif agent_type == "coder":
            return "changes.md"
        elif agent_type == "scribe":
            return "documentation.md"
        elif agent_type == "verifier":
            return "verification.md"
        else:
            return f"{agent_type}.md"
        
    def save_config(self):
        """Save current configuration to JSON file"""
        config_data = {
            'sequence': self.sequence,
            'gates': self.gates
        }
        
        # Ensure directory exists
        self.config_path.parent.mkdir(exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)


class ExtensibleClaudeDrivenOrchestrator:
    """Extensible version of the Claude-Driven Orchestrator"""
    
    def __init__(self, enable_dashboard: bool = True, dashboard_port: int = 5678, api_port: int = 8000, no_browser: bool = False):
        # Check for meta mode
        self.meta_mode = 'meta' in sys.argv
        
        self.project_root = Path.cwd()
        
        # Set directories with -meta suffix if in meta mode
        if self.meta_mode:
            self.claude_dir = self.project_root / ".claude-meta"
            self.outputs_dir = self.project_root / ".agent-outputs-meta"
        else:
            self.claude_dir = self.project_root / ".claude"
            self.outputs_dir = self.project_root / ".agent-outputs"
        
        self.agents_dir = Path.home() / ".claude-orchestrator" / "agents"
        
        # Task tracking files in .claude directory
        self.tasks_file = self.claude_dir / "tasks.md"
        self.checklist_file = self.claude_dir / "tasks-checklist.md"
        
        # Dashboard configuration
        self.enable_dashboard = enable_dashboard
        self.dashboard_port = dashboard_port
        self.api_port = api_port
        self.no_browser = no_browser
        self.dashboard_process = None
        self.api_process = None
        self.dashboard = None
        
        # Initialize configuration systems
        self.agent_config = AgentConfig(enable_dashboard=self.enable_dashboard, dashboard_port=self.dashboard_port, api_port=self.api_port, no_browser=self.no_browser)
        self.workflow_config = WorkflowConfig()
        
        # Initialize agent factory with configuration
        self.agent_factory = AgentFactory(self, self.agent_config)
        
        # Dashboard is initialized through AgentConfig if enabled
        self.dashboard = self.agent_config.dashboard
        self.dashboard_available = getattr(self.agent_config, 'dashboard_available', False)
        
        # Ensure directories exist
        self.claude_dir.mkdir(exist_ok=True)
        self.agents_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        
        # Generate default configuration files if they don't exist
        self._ensure_config_files()

    def _test_api_endpoint(self):
        """Test if API server HTTP endpoint is responding"""
        try:
            import urllib.request
            import urllib.error
            
            url = f'http://localhost:{self.api_port}/api/status?mode=meta'
            print(f"[Orchestrator] Testing API endpoint: {url}")
            
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print(f"[Orchestrator] API endpoint test passed")
                    return True
                else:
                    print(f"[Orchestrator] API endpoint returned status {response.status}")
                    return False
        except urllib.error.URLError as e:
            print(f"[Orchestrator] API endpoint test failed: {e}")
            return False
        except Exception as e:
            print(f"[Orchestrator] API endpoint test error: {e}")
            return False
    
    def _test_dashboard_endpoint(self):
        """Test if dashboard server HTTP endpoint is responding"""
        try:
            import urllib.request
            import urllib.error
            
            url = f'http://localhost:{self.dashboard_port}/dashboard.html'
            print(f"[Orchestrator] Testing dashboard endpoint: {url}")
            
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print(f"[Orchestrator] Dashboard endpoint test passed")
                    return True
                else:
                    print(f"[Orchestrator] Dashboard endpoint returned status {response.status}")
                    return False
        except urllib.error.URLError as e:
            print(f"[Orchestrator] Dashboard endpoint test failed: {e}")
            return False
        except Exception as e:
            print(f"[Orchestrator] Dashboard endpoint test error: {e}")
            return False

    def _ensure_config_files(self):
        """Generate default configuration files if they don't exist"""
        # Generate agent configuration
        if not self.agent_config.config_path.exists():
            self.agent_config.save_config()
            
        # Generate workflow configuration  
        if not self.workflow_config.config_path.exists():
            self.workflow_config.save_config()

    def _display_file_contents(self, filepath, description="file"):
        """Helper method to display file contents without truncation"""
        print("INSTRUCTION TO CLAUDE:")
        print("Read the file " + str(filepath))
        print("Then type out its complete contents verbatim as your response text.")
        print("Do not use any tools. Just type the " + description + " contents as your reply.")
        
    def _write_and_display(self, content, filename, description="status"):
        """Write content to file and instruct Claude to display it"""
        filepath = self.outputs_dir / filename
        filepath.write_text(content)
        self._display_file_contents(filepath, description)
        
    def _write_and_execute_command(self, command, description=""):
        """Write instructions to file and instruct Claude to follow them"""
        command_file = self.outputs_dir / "next-command.txt"
        command_file.write_text(command)
        
        print("INSTRUCTION TO CLAUDE:")
        print("Read the file " + str(self.outputs_dir / "next-command.txt"))
        print("Then follow the instructions it contains exactly.")
        if description:
            print("Purpose: " + description)
        print("Do not analyze or explain. Just follow the instructions from the file.")

    def _build_agent_instructions(self, agent_name, primary_objective, work_section, completion_phrase):
        """Build standardized agent instructions with primary objective framing"""
        
        # Add meta flag to continue command if in meta mode
        meta_flag = ' meta' if self.meta_mode else ''
        
        # Build complete instructions that work without requiring /clear execution by Claude
        complete_instructions = "IMPORTANT: YOU MUST EXECUTE THE 'FINAL STEP' at the end of these instructions once you are done.\n\n" + \
                               "You are now the " + agent_name.upper() + " agent.\n\n" + \
                               work_section + "\n\n" + \
                               "When complete, output: " + completion_phrase + "\n\n" + \
                               "FINAL STEP: Run the claude code command `/clear` to reset context, then run:\n" + \
                               "python3 ~/.claude-orchestrator/orchestrate.py continue" + meta_flag
        
        # Write complete instructions to next-command.txt
        self._write_and_execute_command(complete_instructions, "Reset context and start " + agent_name + " agent")
        
        # Also write to agent-specific file for reference
        work_file = self.outputs_dir / (agent_name + "-instructions.md")
        work_file.write_text(complete_instructions)
        
        return "AGENT ACTIVATED: " + agent_name.upper() + "\n\n" + \
               f"Complete instructions written to {self.outputs_dir}/next-command.txt"

    def _build_gate_instructions(self, gate_name, content, options):
        """Build standardized gate instructions with improved visibility"""
        options_text = '\n'.join('• ' + option for option in options)
        
        # Determine mode for API integration
        mode = 'meta' if self.meta_mode else 'regular'
        
        # Add API integration section
        api_section = f"\nPROGRAMMATIC OPTIONS (via Dashboard API):\n" + \
                     f"POST http://localhost:8000/api/gate-decision?mode={mode}\n" + \
                     "Content-Type: application/json\n\n" + \
                     "Request format:\n" + \
                     '{\n' + \
                     '  "decision_type": "approve-criteria|modify-criteria|retry-explorer",\n' + \
                     '  "modifications": "text for modify-criteria only"\n' + \
                     '}\n\n' + \
                     "Dashboard can poll status and make decisions programmatically.\n"
        
        # Write gate info to file for display
        gate_content = gate_name.upper() + " GATE: Human Review Required\n\n" + \
                      content + "\n\n" + \
                      "AVAILABLE OPTIONS:\n" + options_text + api_section + "\n" + \
                      "WORKFLOW PAUSED - Choose an option above\n"
        
        gate_filename = "current-" + gate_name.lower() + "-gate.md"
        self._write_and_display(gate_content, gate_filename, "gate options")
        
        # Set dashboard gate information if dashboard is available
        if self.dashboard and getattr(self.agent_config, 'dashboard_available', False):
            self.dashboard.set_gate(gate_name, content, options)
        
        return gate_name.upper() + " GATE: Human Review Required\n\n" + \
               "STOP: I must wait for the human to choose one of the options displayed above. " + \
               "I will not provide commentary, analysis, or summaries. The human will select an option."

    def get_continue_agent(self):
        """Get the next agent to run and its instructions using configurable workflow"""
        
        # Check what outputs exist to determine next phase
        current_outputs = {
            "exploration.md": (self.outputs_dir / "exploration.md").exists(),
            "success-criteria.md": (self.outputs_dir / "success-criteria.md").exists(),
            "plan.md": (self.outputs_dir / "plan.md").exists(),
            "changes.md": (self.outputs_dir / "changes.md").exists(),
            "documentation.md": (self.outputs_dir / "documentation.md").exists(),
            "verification.md": (self.outputs_dir / "verification.md").exists(),
            "completion-approved.md": (self.outputs_dir / "completion-approved.md").exists()
        }
        
        # Use workflow configuration to determine next agent
        next_agent = self.workflow_config.get_next_agent(current_outputs)
        
        if next_agent is None:
            # Update status before returning completion
            self._update_status_file()
            return "complete", "All agents have completed successfully. Task marked complete."
        
        # Update status to reflect current workflow state
        self._update_status_file()
        
        # Prepare the next agent using dynamic preparation
        return self._prepare_work_agent(next_agent)

    def _prepare_work_agent(self, agent_type: str):
        """Dynamic agent preparation based on agent type"""
        
        if agent_type == "explorer":
            task = self._get_current_task()
            if not task:
                return "error", "No task found in tasks-checklist.md"
            return self.agent_factory.create_agent("explorer", task=task)
            
        elif agent_type == "criteria_gate":
            exploration_file = self.outputs_dir / "exploration.md"
            if not exploration_file.exists():
                return "error", "No exploration.md found for criteria approval"
            
            # Check for unsupervised mode
            unsupervised_file = self.claude_dir / "unsupervised"
            if unsupervised_file.exists():
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
                
                if criteria_section:
                    # Auto-approve criteria in unsupervised mode
                    criteria_text = '\n'.join(criteria_section)
                    criteria_file = self.outputs_dir / "success-criteria.md"
                    criteria_file.write_text("# Approved Success Criteria\n\n" + criteria_text + "\n")
                    print("Unsupervised mode: Auto-approved criteria")
                    
                    # Continue to next agent
                    agent, instructions = self.get_continue_agent()
                    print("\n" + "="*60)
                    print("AUTO-CONTINUING TO " + agent.upper())
                    print("="*60)
                    print(instructions)
                    print("="*60)
                    return agent, instructions
            
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
            
        elif agent_type == "completion_gate":
            verification_file = self.outputs_dir / "verification.md"
            if not verification_file.exists():
                return "error", "No verification.md found for completion approval"
            
            # Check for unsupervised mode
            unsupervised_file = self.claude_dir / "unsupervised"
            if unsupervised_file.exists():
                verification_content = verification_file.read_text()
                
                # Check if verification recommends approval
                verification_lower = verification_content.lower()
                if "recommend approval" in verification_lower or "ready for approval" in verification_lower or "approve" in verification_lower:
                    # Auto-approve completion in unsupervised mode
                    print("Unsupervised mode: Auto-approved completion")
                    self.approve_completion()
                    return "complete", "Task automatically completed in unsupervised mode"
            
            verification_content = verification_file.read_text()
            
            # Extract overall status
            status_line = "Status not found"
            for line in verification_content.split('\n'):
                if "Overall Status:" in line:
                    status_line = line.strip()
                    break
            
            return self.agent_factory.create_agent("completion_gate", status_line=status_line)
            
        else:
            # Generic agent preparation for work agents
            return self.agent_factory.create_agent(agent_type)

    def _get_current_task(self):
        """Extract continue uncompleted task from tasks-checklist.md"""
        
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
        
    def _update_task_status(self, task, status):
        """Update task status in tasks.md"""
        
        if not task:
            return
            
        if not self.tasks_file.exists():
            self.tasks_file.write_text("# Tasks\n\n- [ ] " + task + " - " + status + "\n")
            return
            
        content = self.tasks_file.read_text()
        lines = content.split('\n')
        
        task_updated = False
        for i, line in enumerate(lines):
            if task[:30] in line:
                if '- [ ]' in line:
                    lines[i] = "- [ ] " + task + " - " + status
                elif '- [x]' in line:
                    if status == "COMPLETE":
                        lines[i] = "- [x] " + task + " - " + status
                    else:
                        lines[i] = "- [ ] " + task + " - " + status
                task_updated = True
                break
                
        if not task_updated:
            lines.append("- [ ] " + task + " - " + status)
            
        self.tasks_file.write_text('\n'.join(lines))

    def status(self):
        """Show current orchestration status by writing to file and commanding display"""
        
        status_info = "# Orchestration Status\n\n"
        
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
                status_info += "✓ " + agent.ljust(15) + " complete (" + str(size) + " bytes)\n"
            else:
                status_info += "⏳ " + agent.ljust(15) + " pending\n"
                
        current_task = self._get_current_task()
        if current_task:
            status_info += "\nCurrent task: " + current_task[:60] + "\n"
            
        # Write and display status
        self._write_and_display(status_info, "current-status.md", "status")

    def _update_status_file(self):
        """Update current-status.md file immediately without displaying"""
        status_info = "# Orchestration Status\n\n"
        
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
                status_info += "✓ " + agent.ljust(15) + " complete (" + str(size) + " bytes)\n"
            else:
                status_info += "⏳ " + agent.ljust(15) + " pending\n"
                
        current_task = self._get_current_task()
        if current_task:
            status_info += "\nCurrent task: " + current_task[:60] + "\n"
            
        # Write status to file without displaying
        status_filepath = self.outputs_dir / "current-status.md"
        status_filepath.write_text(status_info)

    def modify_criteria(self, modification_request=None):
        """Set up criteria modification task for Claude and continue workflow"""
        if not modification_request:
            print("No modification request provided")
            print("Usage: Execute the slash-command `/orchestrate modify-criteria` \"your modification instructions\"")
            return
            
        # Read the current exploration results
        exploration_file = self.outputs_dir / "exploration.md"
        if not exploration_file.exists():
            print("No exploration.md found. Run the Explorer first.")
            return
            
        # Save the modification request for Claude to process
        modification_file = self.outputs_dir / "criteria-modification-request.md"
        modification_file.write_text("# Criteria Modification Request\n\n" + modification_request + "\n")
        
        # Set up a special "criteria modifier" agent task
        task = self._get_current_task()
        self._update_task_status(task, "MODIFYING CRITERIA")
        
        instructions = "FIRST: Execute the slash-command `/clear` to reset context\n\n" + \
                      "CRITERIA MODIFICATION TASK:\n\n" + \
                      f"1. Read {self.outputs_dir}/exploration.md to see the original suggested criteria\n" + \
                      f"2. Read {self.outputs_dir}/criteria-modification-request.md for the modification request\n" + \
                      "3. Apply the requested modifications to create updated success criteria\n" + \
                      f"4. Write the final modified criteria to {self.outputs_dir}/success-criteria.md\n\n" + \
                      "MODIFICATION REQUEST: " + modification_request + "\n\n" + \
                      "Output format for success-criteria.md:\n" + \
                      "# Approved Success Criteria\n\n" + \
                      "[Your modified criteria here - apply the modification request to the original suggestions]\n\n" + \
                      "When complete, say \"CRITERIA MODIFICATION COMPLETE\"\n\n" + \
                      "FINAL STEP: Execute the slash-command `/clear` to reset context, then execute the slash-command `/orchestrate continue`"
        
        print("\n" + "="*60)
        print("CRITERIA MODIFICATION TASK READY")
        print("="*60)
        print(instructions)
        print("="*60)
        
    def retry_explorer(self):
        """Restart from Explorer phase"""
        self._retry_from_phase("explorer")
        
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
            criteria_file.write_text("# Approved Success Criteria\n\n" + criteria_text + "\n")
            
            print("Success criteria approved and saved")
            
            # Update status file after criteria approval
            self._update_status_file()
            
            # Continue to continue agent
            agent, instructions = self.get_continue_agent()
            print("\n" + "="*60)
            print("CRITERIA APPROVED - CONTINUING TO " + agent.upper())
            print("="*60)
            print(instructions)
            print("="*60)
            
    def approve_completion(self):
        """Approve completion and mark task done"""
        task = self._get_current_task()
        if task:
            self._update_task_status(task, "COMPLETE")
            self._update_checklist(task, completed=True)
            approval_file = self.outputs_dir / "completion-approved.md"
            approval_file.write_text("# Task Completion Approved\n\nTask: " + task + 
                                    "\nApproved at: " + datetime.now().isoformat() + "\n")
            
            # Update status file after completion approval
            self._update_status_file()
            
            print("\n" + "="*60)
            print("TASK COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("Task marked complete: " + task)
            print("Updated tasks.md and tasks-checklist.md")
            print(f"Check {self.outputs_dir}/verification.md for final results")
            
            # Check for unsupervised mode and auto-continue
            unsupervised_file = self.claude_dir / "unsupervised"
            if unsupervised_file.exists():
                print("Unsupervised mode detected - auto-continuing workflow")
                self.clean_outputs()
                agent, instructions = self.get_continue_agent()
                print("\n" + "="*60)
                print("AUTO-STARTING - AGENT: " + agent.upper())
                print("="*60)
                print(instructions)
                print("="*60)
            else:
                print("Execute the slash-command `/orchestrate clean` to prepare for continue task")
                print("="*60)
        
    def retry_from_planner(self):
        """Restart from Planner phase (keep criteria)"""
        self._retry_from_phase("planner", "Planner (keeping criteria)")
        
    def retry_from_coder(self):
        """Restart from Coder phase (keep plan)"""
        self._retry_from_phase("coder", "Coder (keeping plan)")
        
    def retry_from_verifier(self):
        """Restart just Verifier phase (keep changes)"""
        self._retry_from_phase("verifier", "Verifier (keeping changes)")
        
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
                
        print(f"Cleaned {cleaned_count} orchestrator files from {self.outputs_dir}/")
        
    def mark_complete(self, success=True):
        """Mark current task as complete or failed"""
        
        task = self._get_current_task()
        if not task:
            return
            
        if success:
            self._update_task_status(task, "COMPLETE")
            self._update_checklist(task, completed=True)
            print("\nTask marked complete: " + task)
        else:
            self._update_task_status(task, "NEEDS REVIEW")
            print("\nTask needs review: " + task)
            
    def bootstrap_tasks(self):
        """Interactive bootstrap to help users generate initial tasks"""
        
        bootstrap_instructions = """
BOOTSTRAP MODE: Help the user create initial tasks for their project

TASK: Analyze the current project and guide the user through creating meaningful tasks

YOUR RESPONSIBILITIES:
1. Analyze the current codebase and project structure
2. Ask the user about their goals and priorities  
3. Suggest specific, actionable tasks based on the analysis
4. Create both tasks.md and tasks-checklist.md files
5. Explain the next steps for using the orchestrator

ANALYSIS TO PERFORM:
- Examine package.json, requirements.txt, or similar dependency files
- Look at README.md and documentation
- Identify main source code directories and files
- Check for existing tests, build scripts, CI/CD
- Note any obvious issues (missing tests, outdated deps, TODO comments)

QUESTIONS TO ASK USER:
1. "What are the main goals for this project?"
2. "What problems are you currently facing?"
3. "What would you like to work on first - bugs, features, or improvements?"
4. "Are there any specific areas of the code that need attention?"

TASK GENERATION APPROACH:
- Create 3-5 specific, actionable tasks
- Mix of different types: bug fixes, features, tests, docs, refactoring
- Start with smaller tasks that can build momentum
- Include acceptance criteria for each task

OUTPUT FORMAT:
Create both .claude/tasks.md and .claude/tasks-checklist.md with:

tasks.md:
```markdown
# Project Tasks

## Current Sprint
- [ ] [Generated task 1 with clear acceptance criteria]
- [ ] [Generated task 2 with clear acceptance criteria]

## Backlog  
- [ ] [Future task 1]
- [ ] [Future task 2]

## Completed
[Empty initially]
```

tasks-checklist.md:
```markdown
# Tasks Checklist

- [ ] [Same tasks as above but in simple checklist format]
```

FINAL STEP: 
After creating the files, tell the user:
"Bootstrap complete! Your tasks are ready. Execute the slash-command `/orchestrate start` to begin your first workflow."

Begin by analyzing the current directory and asking the user about their goals.
"""
        
        print("\n" + "="*60)
        print("BOOTSTRAP MODE: Generating Initial Tasks")
        print("="*60)
        print(bootstrap_instructions)
        print("="*60)
        
    def _retry_from_phase(self, phase_name, display_name=None):
        """Generic retry method for any phase"""
        if not display_name:
            display_name = phase_name.title()
            
        self._clean_from_phase(phase_name)
        print("Restarting from " + display_name + " phase")
        
        # Update status file after cleaning phase
        self._update_status_file()
        
        # Continue to continue agent
        next_agent_result = self.get_continue_agent()
        if next_agent_result:
            if isinstance(next_agent_result, tuple):
                next_agent_type, result = next_agent_result
                print("\n" + "="*60)
                print("RESTARTING FROM " + next_agent_type.upper())
                print("="*60)
                print(result)
                print("="*60)
            else:
                print("\n" + "="*60)
                print("RESTARTING FROM " + next_agent_result.upper())
                print("="*60)
                
    def _clean_from_phase(self, phase):
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
            self._update_task_status(task, f"RESTARTING FROM {phase.upper()}")
            
    def _update_checklist(self, task, completed):
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
                    lines[i] = "- [x] " + task + " (Completed: " + timestamp + ")"
                else:
                    lines[i] = "- [ ] " + task + " (Attempted: " + timestamp + ")"
                task_found = True
                break
                
        if not task_found and completed:
            lines.append("- [x] " + task + " (Completed: " + timestamp + ")")
        elif not task_found and not completed:
            lines.append("- [ ] " + task + " (Attempted: " + timestamp + ")")
            
        self.checklist_file.write_text('\n'.join(lines))
    
    def enable_unsupervised_mode(self):
        """Enable unsupervised mode by creating .claude/unsupervised file"""
        unsupervised_file = self.claude_dir / "unsupervised"
        unsupervised_file.write_text("# Unsupervised Mode Active\n\nAutomatically approves gates when criteria are met.\n")
        print(f"Unsupervised mode enabled - created {unsupervised_file}")
        
    def disable_unsupervised_mode(self):
        """Disable unsupervised mode by removing .claude/unsupervised file"""
        unsupervised_file = self.claude_dir / "unsupervised"
        if unsupervised_file.exists():
            unsupervised_file.unlink()
            print(f"Supervised mode enabled - removed {unsupervised_file}")
        else:
            print("Already in supervised mode - no unsupervised file found")


def main():
    """CLI entry point - designed for actual workflow operations"""
    
    parser = argparse.ArgumentParser(description='Claude Code Orchestrator')
    parser.add_argument('command', nargs='?', default='start',
                       help='Command to execute (default: start)')
    parser.add_argument('--no-browser', action='store_true',
                       help='Suppress browser opening for CI/CD environments')
    parser.add_argument('modification_text', nargs='*',
                       help='Modification text for modify-criteria command')
    
    args = parser.parse_args()
    command = args.command
    
    orchestrator = ExtensibleClaudeDrivenOrchestrator(no_browser=args.no_browser)
    
    # Basic workflow commands
    if command == "start":
        # Start workflow with existing state
        agent, instructions = orchestrator.get_continue_agent()
        print("\n" + "="*60)
        print("STARTING - AGENT: " + agent.upper())
        print("="*60)
        print(instructions)
        print("="*60)
        
    elif command == "continue":
        agent, instructions = orchestrator.get_continue_agent()
        print("\n" + "="*60)
        print("AGENT: " + agent.upper())
        print("="*60)
        print(instructions)
        print("="*60)
        
    elif command == "status":
        orchestrator.status()
        
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
        # Get modification request from parsed arguments
        if args.modification_text:
            modification_request = " ".join(args.modification_text)
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
        
    elif command == "bootstrap":
        orchestrator.bootstrap_tasks()
        
    elif command == "unsupervised":
        orchestrator.enable_unsupervised_mode()
        
    elif command == "supervised":
        orchestrator.disable_unsupervised_mode()
        
    else:
        print("Unknown command: " + command)
        print("\nAvailable commands:")
        print("  Workflow: start, continue, status, clean, complete, fail, bootstrap")
        print("  Gates: approve-criteria, modify-criteria, retry-explorer")
        print("         approve-completion, retry-from-planner, retry-from-coder, retry-from-verifier")
        print("  Mode: unsupervised, supervised")


if __name__ == "__main__":
    main()