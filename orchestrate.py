#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extensible Claude-Driven Orchestrator (Version 2)
Implements configurable agent types and workflow sequences
"""

import json
import os
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
import signal
import threading
import urllib.request
import urllib.error
from process_manager import ProcessManager


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
    
    def __init__(self, config_path: Path = None, enable_dashboard: bool = False, dashboard_port: int = 5678, api_port: int = 8000, no_browser: bool = False, process_manager=None):
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
        self.process_manager = process_manager
        self.health_check_thread = None
        self.health_check_running = False
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
                                    debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                                    if debug_mode:
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
                debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                if debug_mode:
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
            
            # Register API process with ProcessManager if available
            if self.process_manager:
                self.process_manager.register_process('api_server', self.api_process)
            print(f"API server started as subprocess (PID: {self.api_process.pid}) on port {self.api_port}")
            
            # Start dashboard server as subprocess
            self.dashboard_process = subprocess.Popen([
                sys.executable, 'dashboard_server.py', str(self.dashboard_port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Register dashboard process with ProcessManager if available
            if self.process_manager:
                self.process_manager.register_process('dashboard_server', self.dashboard_process)
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
                
                # Start health monitoring
                self.start_health_monitoring()
                
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
            # Stop health monitoring first
            self.stop_health_monitoring()
            
            # Use ProcessManager for clean shutdown if available
            if self.process_manager:
                dashboard_stopped = self.process_manager.terminate_process('dashboard_server')
                api_stopped = self.process_manager.terminate_process('api_server')
                
                if dashboard_stopped:
                    self.dashboard_process = None
                if api_stopped:
                    self.api_process = None
            else:
                # Fallback to direct process termination
                if self.dashboard_process:
                    self.dashboard_process.terminate()
                    self.dashboard_process = None
                if self.api_process:
                    self.api_process.terminate()
                    self.api_process = None
                
        except Exception as e:
            print(f"Error stopping servers: {e}")
    
    def start_health_monitoring(self):
        """Start health monitoring thread for server processes"""
        if self.health_check_running:
            return
            
        self.health_check_running = True
        self.health_check_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self.health_check_thread.start()
        print("Health monitoring started - checking every 30 seconds")
    
    def stop_health_monitoring(self):
        """Stop health monitoring thread"""
        self.health_check_running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
    
    def _health_monitor_loop(self):
        """Health monitoring loop that runs in background thread"""
        while self.health_check_running:
            try:
                time.sleep(30)  # 30-second intervals
                if not self.health_check_running:
                    break
                    
                self._check_server_health()
                
            except Exception as e:
                print(f"Health monitoring error: {e}")
    
    def _check_server_health(self):
        """Check health of dashboard and API servers"""
        if not self.dashboard_available:
            return
            
        # Check process health
        api_running = self.api_process and self.api_process.poll() is None
        dashboard_running = self.dashboard_process and self.dashboard_process.poll() is None
        
        # Check HTTP endpoint health
        api_responsive = self._check_http_health(f"http://localhost:{self.api_port}/health")
        dashboard_responsive = self._check_http_health(f"http://localhost:{self.dashboard_port}/")
        
        # Report issues
        if not api_running:
            print(f"Health check: API server process not running (PID check failed)")
        elif not api_responsive:
            print(f"Health check: API server unresponsive on port {self.api_port}")
            
        if not dashboard_running:
            print(f"Health check: Dashboard server process not running (PID check failed)")
        elif not dashboard_responsive:
            print(f"Health check: Dashboard server unresponsive on port {self.dashboard_port}")
    
    def _check_http_health(self, url: str, timeout: int = 5) -> bool:
        """Check if HTTP endpoint is responsive"""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return False
        except Exception:
            return False


# Legacy gate options - can be made configurable in future
GATE_OPTIONS = {
    "criteria": [
        "approve-criteria - Accept and continue",
        "modify-criteria - Modify criteria first",  
        "retry-explorer - Restart exploration",
        "exit - Exit and resume from this gate later"
    ],
    
    "completion": [
        "approve-completion - Mark complete",
        "retry-explorer - Restart all",
        "retry-from-planner - Restart from Planner",  
        "retry-from-coder - Restart from Coder",
        "retry-from-verifier - Re-verify only",
        "exit - Exit and resume from this gate later"
    ],
    
    "user_validation": [
        "user-approve - Tests passed, continue to next task",
        "new-task [description] - Create new task to fix validation failure",
        "retry-last-task - Previous implementation task needs fixing",
        "exit - Exit and resume from this gate later"
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


class AgentExecutor:
    """Handles agent execution in both headless and interactive modes"""
    
    def __init__(self, orchestrator, headless=False):
        self.orchestrator = orchestrator
        self.outputs_dir = orchestrator.outputs_dir
        # Check headless flag first, then environment variable, default to interactive
        if headless:
            self.use_interactive_mode = False
        else:
            mode = os.getenv('CLAUDE_ORCHESTRATOR_MODE', 'interactive')
            self.use_interactive_mode = (mode == 'interactive' or mode == 'prompt')
        
    def execute_agent(self, agent_type, instructions):
        """Routes to appropriate execution method"""
        try:
            if self.use_interactive_mode:
                return self._execute_via_interactive(agent_type, instructions)
            else:
                return self._execute_headless(agent_type, instructions)
        except FileNotFoundError:
            print("Claude CLI not found, falling back to interactive mode")
            return self._execute_via_interactive(agent_type, instructions)
        except subprocess.TimeoutExpired:
            return f"❌ {agent_type} timed out after 300 seconds"

    def _execute_headless(self, agent_type, instructions):
        """Execute agent using claude -p with headless automation and enhanced diagnostics"""
        timeout_seconds = 300
        debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        if debug_mode:
            print(f"[DEBUG] Starting headless execution for {agent_type}")
        
        # Ensure directory exists
        try:
            self.outputs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return f"❌ {agent_type.upper()} failed: Cannot create working directory {self.outputs_dir}: {str(e)}"
        
        # Instructions are now clean from generation (no stripping needed)
        clean_instructions = instructions
        
        
        # Validate Claude CLI availability
        claude_binary = 'claude'
        try:
            # Test if claude command is available
            claude_test = subprocess.run(['which', claude_binary], capture_output=True, text=True)
            if claude_test.returncode != 0:
                # Try alternative paths
                alternative_paths = ['/usr/local/bin/claude', '/opt/homebrew/bin/claude', '~/.local/bin/claude']
                claude_found = False
                for alt_path in alternative_paths:
                    expanded_path = os.path.expanduser(alt_path)
                    if os.path.exists(expanded_path) and os.access(expanded_path, os.X_OK):
                        claude_binary = expanded_path
                        claude_found = True
                        break
                if not claude_found:
                    raise FileNotFoundError("Claude CLI not found. Please install Claude CLI or add it to PATH. Checked locations: /usr/local/bin/claude, /opt/homebrew/bin/claude, ~/.local/bin/claude")
            else:
                pass
        except FileNotFoundError:
            # Let FileNotFoundError propagate to parent method
            raise
        except Exception as e:
            error_msg = self._sanitize_error_message(f"Claude CLI validation failed: {str(e)}")
            raise FileNotFoundError(error_msg)
        
        cmd = [
            claude_binary,
            '-p', clean_instructions,
            '--output-format', 'json',
            '--dangerously-skip-permissions'
        ]
        
        # Show command execution details only in debug mode
        if debug_mode:
            print(f"🔄 Executing: {claude_binary} -p '{clean_instructions}' --output-format json --dangerously-skip-permissions")
        
        # Create subprocess environment without CLAUDE_ORCHESTRATOR_MODE
        subprocess_env = dict(os.environ)
        subprocess_env.pop('CLAUDE_ORCHESTRATOR_MODE', None)
        
        # Add deterministic start timestamp to agent log file
        from datetime import datetime
        start_time = datetime.now()
        timestamp = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        log_file = self.outputs_dir / f"{agent_type}-log.txt"
        
        # Add start timestamp
        start_log = f"\n## {timestamp} - {agent_type.upper()} Agent Session\n\n"
        if log_file.exists():
            with open(log_file, 'a') as f:
                f.write(start_log)
        else:
            with open(log_file, 'w') as f:
                f.write(start_log)
        
        try:
            result_process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=str(self.orchestrator.project_root),
                env=subprocess_env
            )
            
            exit_code = result_process.returncode
            stdout_output = result_process.stdout
            stderr_output = result_process.stderr
            
            # Show captured output only in debug mode
            if debug_mode:
                if stdout_output and stdout_output.strip():
                    print(f"📤 Claude output: {stdout_output.strip()}")
                if stderr_output and stderr_output.strip():
                    print(f"⚠️  Claude stderr: {stderr_output.strip()}")
            
            if debug_mode:
                print(f"[DEBUG] Process completed with exit code: {exit_code}")
                if stderr_output and exit_code != 0:
                    print(f"[DEBUG] Error output: {stderr_output[:200]}...")
            
            # Add deterministic stop timestamp to agent log file
            end_time = datetime.now()
            end_timestamp = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            duration = (end_time - start_time).total_seconds()
            
            if exit_code == 0:
                stop_log = f"\n## {end_timestamp} - {agent_type.upper()} Agent Session Complete (Duration: {duration:.1f}s, Exit Code: {exit_code})\n"
                with open(log_file, 'a') as f:
                    f.write(stop_log)
                return f"✅ {agent_type.upper()} completed successfully"
            else:
                # Build detailed error report for better debugging
                detailed_error = self._build_detailed_agent_error(
                    agent_type, exit_code, stdout_output, stderr_output
                )
                stop_log = f"\n## {end_timestamp} - {agent_type.upper()} Agent Session Failed (Duration: {duration:.1f}s, Exit Code: {exit_code})\n"
                with open(log_file, 'a') as f:
                    f.write(stop_log)
                return f"❌ {agent_type.upper()} failed: {detailed_error}"
                
        except subprocess.TimeoutExpired:
            # Add stop timestamp for timeout
            end_time = datetime.now()
            end_timestamp = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            duration = (end_time - start_time).total_seconds()
            stop_log = f"\n## {end_timestamp} - {agent_type.upper()} Agent Session Timeout (Duration: {duration:.1f}s)\n"
            with open(log_file, 'a') as f:
                f.write(stop_log)
            
            error_message = f"Claude CLI execution timed out after {timeout_seconds} seconds. This may indicate a complex task requiring more time, network issues, or Claude CLI hanging. Consider increasing timeout or checking network connectivity."
            if debug_mode:
                print(f"[DEBUG] Timeout error: {error_message}")
            return f"❌ {agent_type.upper()} failed: {error_message}"
        except subprocess.CalledProcessError as e:
            # Add stop timestamp for process error
            end_time = datetime.now()
            end_timestamp = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            duration = (end_time - start_time).total_seconds()
            stop_log = f"\n## {end_timestamp} - {agent_type.upper()} Agent Session Error (Duration: {duration:.1f}s, CalledProcessError)\n"
            with open(log_file, 'a') as f:
                f.write(stop_log)
            
            error_message = f"Claude CLI process failed with return code {e.returncode}"
            if e.stderr and e.stderr.strip():
                stderr_truncated = e.stderr.strip()[:400]
                if len(e.stderr.strip()) > 400:
                    stderr_truncated += "..."
                error_message += f" | Stderr: {stderr_truncated}"
            return f"❌ {agent_type.upper()} failed: {self._sanitize_error_message(error_message)}"
        except PermissionError as e:
            # Add stop timestamp for permission error
            end_time = datetime.now()
            end_timestamp = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            duration = (end_time - start_time).total_seconds()
            stop_log = f"\n## {end_timestamp} - {agent_type.upper()} Agent Session Error (Duration: {duration:.1f}s, PermissionError)\n"
            with open(log_file, 'a') as f:
                f.write(stop_log)
            
            error_message = f"Permission denied accessing {getattr(e, 'filename', 'file')}. Check file permissions or run with appropriate privileges."
            return f"❌ {agent_type.upper()} failed: {error_message}"
        except OSError as e:
            # Add stop timestamp for OS error
            end_time = datetime.now()
            end_timestamp = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            duration = (end_time - start_time).total_seconds()
            stop_log = f"\n## {end_timestamp} - {agent_type.upper()} Agent Session Error (Duration: {duration:.1f}s, OSError)\n"
            with open(log_file, 'a') as f:
                f.write(stop_log)
            
            error_message = f"System error: {str(e)}. Check system resources and file system access."
            return f"❌ {agent_type.upper()} failed: {self._sanitize_error_message(error_message)}"

    def _execute_via_interactive(self, agent_type, instructions):
        """Legacy interactive mode - return instructions unchanged for Claude to execute"""
        return instructions

    def _build_detailed_agent_error(self, agent_type, exit_code, stdout_output, stderr_output):
        """Build comprehensive error report for agent failures"""
        error_parts = []
        
        # Basic failure info
        error_parts.append(f"Exit code {exit_code}")
        
        # Expected output files for this agent type
        expected_outputs = {
            "explorer": "exploration.md",
            "planner": "plan.md", 
            "coder": "changes.md",
            "verifier": "verification.md",
            "scribe": "orchestrator-log.md"
        }
        
        expected_file = expected_outputs.get(agent_type)
        if expected_file:
            expected_path = self.outputs_dir / expected_file
            if expected_path.exists():
                size = expected_path.stat().st_size
                error_parts.append(f"Expected output '{expected_file}' was created ({size} bytes)")
            else:
                error_parts.append(f"Expected output '{expected_file}' was NOT created")
        
        # Check input files exist (for agents that need them)
        if agent_type in ["planner", "coder", "verifier"]:
            input_files = {
                "planner": ["exploration.md", "success-criteria.md"],
                "coder": ["exploration.md", "success-criteria.md", "plan.md"],
                "verifier": ["exploration.md", "success-criteria.md", "plan.md", "changes.md"]
            }
            
            missing_inputs = []
            for input_file in input_files.get(agent_type, []):
                input_path = self.outputs_dir / input_file
                if not input_path.exists():
                    missing_inputs.append(input_file)
            
            if missing_inputs:
                error_parts.append(f"Missing required input files: {', '.join(missing_inputs)}")
            else:
                error_parts.append("All required input files present")
        
        # Working directory info
        error_parts.append(f"Working directory: {self.outputs_dir}")
        if not self.outputs_dir.exists():
            error_parts.append("ERROR: Working directory does not exist!")
        elif not self.outputs_dir.is_dir():
            error_parts.append("ERROR: Working directory path is not a directory!")
        
        # Claude CLI stdout (full output, not truncated)
        if stdout_output and stdout_output.strip():
            clean_stdout = stdout_output.strip()
            error_parts.append(f"Claude CLI stdout ({len(clean_stdout)} chars): {clean_stdout}")
        else:
            error_parts.append("No stdout output from Claude CLI")
        
        # Claude CLI stderr (full output, not truncated)  
        if stderr_output and stderr_output.strip():
            clean_stderr = stderr_output.strip()
            error_parts.append(f"Claude CLI stderr ({len(clean_stderr)} chars): {clean_stderr}")
        else:
            error_parts.append("No stderr output from Claude CLI")
        
        # Agent log file status for debugging
        log_file = self.outputs_dir / f"{agent_type}-log.txt"
        if log_file.exists():
            size = log_file.stat().st_size
            error_parts.append(f"Agent log file exists ({size} bytes): {log_file}")
        else:
            error_parts.append(f"No agent log file found: {log_file}")
        
        return " | ".join(error_parts)

    def _sanitize_error_message(self, message):
        """Sanitize error message to prevent None values and ensure reasonable length"""
        if message is None:
            return "Error occurred with no details available"
        
        # Convert to string and handle None values more precisely
        str_message = str(message)
        
        # Handle specific "failed: None" pattern
        if "failed: None" in str_message:
            str_message = str_message.replace("failed: None", "failed: Error details unavailable")
        
        # Replace standalone None/null values but preserve context
        import re
        # Replace "None" when it appears as a standalone value or at word boundaries
        str_message = re.sub(r'\bNone\b', 'unavailable', str_message)
        str_message = re.sub(r'\bnull\b', 'unavailable', str_message)
        
        # Ensure message is not empty
        if not str_message.strip():
            return "Error occurred but no details available"
        
        # Truncate to reasonable length
        if len(str_message) > 500:
            str_message = str_message[:497] + "..."
        
        return str_message.strip()


    def _process_instructions_internally(self, agent_type, instructions):
        """Process agent instructions by executing real Claude CLI processes"""
        try:
            # Execute agent using the real headless execution method
            return self._execute_headless(agent_type, instructions)
            
        except Exception as e:
            return f"❌ {agent_type.upper()} failed during execution: {str(e)}"
    
    



class WorkflowConfig:
    """Configuration manager for workflow definitions"""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path('.claude/workflow-config.json')
        self.sequence = ["explorer", "criteria_gate", "planner", "coder", "verifier", "scribe", "completion_gate"]
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
                
    def get_next_agent(self, current_outputs: Dict[str, bool], outputs_dir: Path = None) -> Optional[str]:
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
                
                # Special case for scribe: run after verifier if verification is newer than last scribe run
                if agent_type == "scribe" and outputs_dir:
                    if current_outputs.get("verification.md", False):
                        verification_file = outputs_dir / "verification.md"
                        scribe_file = outputs_dir / "orchestrator-log.md"
                        
                        # Run scribe if orchestrator-log doesn't exist or verification is newer
                        if not scribe_file.exists():
                            return agent_type
                        elif verification_file.exists():
                            verification_time = verification_file.stat().st_mtime
                            scribe_time = scribe_file.stat().st_mtime
                            if verification_time > scribe_time:
                                return agent_type
                else:
                    # Normal agents - check if output file exists
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
            return "orchestrator-log.md"
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


class ClaudeCodeOrchestrator:
    """Claude Code Orchestrator - Extensible agent workflow orchestration"""
    
    def __init__(self, enable_dashboard: bool = False, dashboard_port: int = 5678, api_port: int = 8000, no_browser: bool = False, headless: bool = False):
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
        self.headless = headless
        self.dashboard_process = None
        self.api_process = None
        self.dashboard = None
        
        # Initialize process manager for robust subprocess handling
        self.process_manager = ProcessManager(meta_mode=self.meta_mode)
        
        # Register main orchestrator process for tracking
        self.process_manager.register_main_process('orchestrator_main')
        
        # Initialize configuration systems
        self.agent_config = AgentConfig(enable_dashboard=self.enable_dashboard, dashboard_port=self.dashboard_port, api_port=self.api_port, no_browser=self.no_browser, process_manager=self.process_manager)
        self.workflow_config = WorkflowConfig()
        
        # Initialize agent factory with configuration
        self.agent_factory = AgentFactory(self, self.agent_config)
        
        # Initialize agent executor for headless/interactive mode execution
        self.agent_executor = AgentExecutor(self, headless=self.headless)
        
        # Dashboard is initialized through AgentConfig if enabled
        self.dashboard = self.agent_config.dashboard
        self.dashboard_available = getattr(self.agent_config, 'dashboard_available', False)
        
        # Install signal handlers for clean shutdown
        self._install_signal_handlers()
        
        # Ensure directories exist
        self.claude_dir.mkdir(exist_ok=True)
        self.agents_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        
        # Generate default configuration files if they don't exist
        self._ensure_config_files()

    def _install_signal_handlers(self):
        """Install signal handlers for clean shutdown"""
        def signal_handler(sig, frame):
            print(f"\nReceived signal {sig}. Cleaning up processes...")
            self.process_manager.cleanup_all_processes()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

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
        
        # Check if in headless mode and use appropriate instruction builder
        if self.headless:
            # In headless mode, use clean instructions without interactive artifacts
            clean_instructions = self._build_headless_agent_instructions(agent_name, primary_objective, work_section, completion_phrase)
            
            # In headless mode, only write to files - no need to print instructions since they're passed via -p
            command_file = self.outputs_dir / "next-command.txt"
            command_file.write_text(clean_instructions)
            
            # Also write to agent-specific file for reference
            work_file = self.outputs_dir / (agent_name + "-instructions.md")
            work_file.write_text(clean_instructions)
            
            # In headless mode, return the actual clean instructions for execution
            return clean_instructions
        
        # Interactive mode: include manual execution steps
        # Add meta flag to continue command if in meta mode
        meta_flag = ' meta' if self.meta_mode else ''
        
        # Add headless flag to continue command if in headless mode
        headless_flag = ' --headless' if self.headless else ''
        
        # Replace .agent-outputs/ paths with actual outputs directory for meta mode compatibility
        adjusted_work_section = work_section.replace('.agent-outputs/', f'{self.outputs_dir.name}/')
        
        # Build complete instructions that work without requiring /clear execution by Claude
        complete_instructions = "IMPORTANT: YOU MUST EXECUTE THE 'FINAL STEP' at the end of these instructions once you are done.\n\n" + \
                               "You are now the " + agent_name.upper() + " agent.\n\n" + \
                               adjusted_work_section + "\n\n" + \
                               "When complete, output: " + completion_phrase + "\n\n" + \
                               "FINAL STEP: Run the claude code command `/clear` to reset context, then run:\n" + \
                               "python3 ~/.claude-orchestrator/orchestrate.py continue" + headless_flag + meta_flag
        
        # Write complete instructions to next-command.txt
        self._write_and_execute_command(complete_instructions, "Reset context and start " + agent_name + " agent")
        
        # Also write to agent-specific file for reference
        work_file = self.outputs_dir / (agent_name + "-instructions.md")
        work_file.write_text(complete_instructions)
        
        # In interactive mode, return the actual instructions for Claude to execute
        return complete_instructions

    def _build_headless_agent_instructions(self, agent_name, primary_objective, work_section, completion_phrase):
        """Build headless agent instructions without interactive artifacts"""
        
        # Replace .agent-outputs/ paths with actual outputs directory for meta mode compatibility
        adjusted_work_section = work_section.replace('.agent-outputs/', f'{self.outputs_dir.name}/')
        
        # Add agent logging instructions for transparency
        log_file = f"{self.outputs_dir.name}/{agent_name}-log.txt"
        
        # Get current time for example
        current_time = datetime.now().strftime("%H:%M:%S")
        
        logging_instructions = f"""
AGENT LOGGING (for debugging transparency):
APPEND (do not overwrite) progress updates to {log_file} using this format:

FIRST: Add task header if this is a new log file or first session:
---
TASK: {primary_objective}
---

THEN: Add your session log entries (Python has already added session start timestamp):
[{current_time}] Starting {agent_name} agent work
[14:32:18] Reading required input files...
[14:32:25] [Describe what you found/understood]
[14:32:40] Beginning implementation...
[14:33:05] [Major steps or decisions]  
[14:33:20] Writing output files...
[14:33:25] {agent_name.title()} agent work complete

CRITICAL REQUIREMENTS:
- APPEND to the file (do not overwrite existing content)
- DO NOT add session start/end timestamps - Python handles those automatically
- DO NOT use the example times shown above (14:32:18, etc)
- Each time you write a log entry, check the current system time and use that
- Format: [HH:MM:SS] where HH:MM:SS is the ACTUAL time right now when you write each entry
- Examples: If it's 2:45 PM when you start, write [14:45:00]. If it's 2:47 PM when you finish reading, write [14:47:00]
- DO NOT use sequential numbers like [00:00:01], [00:00:02] - use real clock time
- Use Write tool with append mode or add content to existing file

"""
        
        # Build clean instructions without interactive commands
        headless_instructions = "You are now the " + agent_name.upper() + " agent.\n\n" + \
                               logging_instructions + \
                               adjusted_work_section + "\n\n" + \
                               "When complete, output: " + completion_phrase
        
        return headless_instructions

    def _build_gate_instructions(self, gate_name, content, options):
        """Build standardized gate instructions with improved visibility"""
        options_text = '\n'.join('• ' + option for option in options)
        
        # Write gate info to file for display
        gate_content = gate_name.upper() + " GATE: Human Review Required\n\n" + \
                      content + "\n\n" + \
                      "AVAILABLE OPTIONS:\n" + options_text + "\n\n" + \
                      "WORKFLOW PAUSED - Choose an option above\n"
        
        gate_filename = "current-" + gate_name.lower() + "-gate.md"
        gate_filepath = self.outputs_dir / gate_filename
        gate_filepath.write_text(gate_content)
        
        # Set dashboard gate information if dashboard is available
        if self.dashboard and getattr(self.agent_config, 'dashboard_available', False):
            self.dashboard.set_gate(gate_name, content, options)
        
        # In interactive mode, return minimal message since file will be displayed
        # In headless mode, return full gate content since it needs to be shown
        if self.headless:
            return gate_content
        else:
            return gate_name.upper() + " GATE: Human Review Required\n\n" + \
                   "STOP: I must wait for the human to choose one of the options displayed above. " + \
                   "I will not provide commentary, analysis, or summaries. The human will select an option."

    def _handle_interactive_gate(self, gate_type, gate_content):
        """Handle interactive gate input in persistent mode"""
        debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        if debug_mode:
            print("\n" + "="*60)
            print(gate_content)
            print("="*60)
        else:
            # Clean gate display for normal mode
            print(f"\n🚪 {gate_type.upper()} GATE: Human Review Required")
            if gate_type == "criteria":
                print("Review success criteria and choose:")
            elif gate_type == "completion":
                print("Review verification results and choose:")
            elif gate_type == "user_validation":
                print("Complete the validation testing and choose:")
            
            gate_options = GATE_OPTIONS.get(gate_type, [])
            for option in gate_options:
                print(f"  • {option}")
            print()
        
        gate_options = GATE_OPTIONS.get(gate_type, [])
        valid_commands = [opt.split(' - ')[0] for opt in gate_options]
        
        while True:
            try:
                user_input = input("\nEnter your choice: ").strip().lower()
                
                if user_input == "exit":
                    # Save gate state for resume
                    gate_state_file = self.outputs_dir / f"pending-{gate_type}-gate.md"
                    gate_state_file.write_text(gate_content)
                    print(f"Exiting. Run 'continue' to resume from {gate_type} gate.")
                    return "exit", "User chose to exit at gate"
                
                elif user_input.startswith("new-task"):
                    # Handle new-task command with optional description
                    if gate_type == "user_validation":
                        # Parse optional description after "new-task"
                        if len(user_input) > 8:  # "new-task" is 8 characters
                            description = user_input[8:].strip()
                        else:
                            description = input("Describe the issue found during validation: ").strip()
                        
                        # Generate and insert the fix task
                        current_user_task = self._get_current_user_validation_task()
                        if current_user_task:
                            fix_task = self._generate_fix_task(current_user_task, description)
                            success = self._insert_task_before_user_validation(fix_task)
                            
                            if success:
                                # Remove pending gate state
                                gate_state_file = self.outputs_dir / f"pending-{gate_type}-gate.md"
                                if gate_state_file.exists():
                                    gate_state_file.unlink()
                                return "new_task_created", f"Created fix task: {fix_task}"
                            else:
                                print("Failed to insert new task. Please try again.")
                                continue
                        else:
                            print("Could not find current USER validation task.")
                            continue
                    else:
                        print("new-task command only available for user validation gates.")
                        continue
                        
                elif user_input in valid_commands:
                    # Remove any pending gate state since we're proceeding
                    gate_state_file = self.outputs_dir / f"pending-{gate_type}-gate.md"
                    if gate_state_file.exists():
                        gate_state_file.unlink()
                    
                    # Execute the gate decision
                    if user_input == "approve-criteria":
                        print("Approving criteria...")
                        self.approve_criteria()
                        return "approved", "Criteria approved, continuing workflow"
                    elif user_input == "modify-criteria":
                        modification = input("Enter modification request: ").strip()
                        if modification:
                            print(f"Modifying criteria: {modification}")
                            self.modify_criteria(modification)
                            return "modified", "Criteria modified, continuing workflow"
                        else:
                            print("No modification provided, continuing...")
                            continue
                    elif user_input == "retry-explorer":
                        print("Restarting from explorer...")
                        self.retry_explorer()
                        return "retry", "Restarting from explorer"
                    elif user_input == "approve-completion":
                        print("Approving completion...")
                        self.approve_completion()
                        return "completed", "Task completion approved"
                    elif user_input == "retry-from-planner":
                        print("Restarting from planner...")
                        self.retry_from_planner()
                        return "retry", "Restarting from planner"
                    elif user_input == "retry-from-coder":
                        print("Restarting from coder...")
                        self.retry_from_coder()
                        return "retry", "Restarting from coder"
                    elif user_input == "retry-from-verifier":
                        print("Restarting from verifier...")
                        self.retry_from_verifier()
                        return "retry", "Restarting from verifier"
                    elif user_input == "user-approve":
                        print("User validation passed, marking task complete...")
                        self.approve_user_validation()
                        return "approved", "User validation passed, continuing workflow"
                    elif user_input == "retry-last-task":
                        print("Retrying last implementation task...")
                        success = self._retry_last_implementation_task()
                        if success:
                            return "retry", "Restarting previous implementation task"
                        else:
                            print("Could not find previous implementation task to retry.")
                            continue
                    else:
                        print(f"Command '{user_input}' not implemented yet")
                        continue
                        
                else:
                    print(f"Invalid option. Choose from: {', '.join(valid_commands)}")
                    continue
                    
            except KeyboardInterrupt:
                print("\nInterrupted. Use 'exit' to save state and quit gracefully.")
                continue
            except EOFError:
                print("\nEOF received. Exiting.")
                return "exit", "EOF received"

    def get_continue_agent(self):
        """Get the next agent to run and its instructions using configurable workflow"""
        
        # Check for pending gate state first (for resume functionality)
        pending_criteria_gate = self.outputs_dir / "pending-criteria-gate.md"
        pending_completion_gate = self.outputs_dir / "pending-completion-gate.md"
        pending_user_validation_gate = self.outputs_dir / "pending-user_validation-gate.md"
        
        if pending_criteria_gate.exists():
            gate_content = pending_criteria_gate.read_text()
            return self._handle_interactive_gate("criteria", gate_content)
        elif pending_completion_gate.exists():
            gate_content = pending_completion_gate.read_text()
            return self._handle_interactive_gate("completion", gate_content)
        elif pending_user_validation_gate.exists():
            gate_content = pending_user_validation_gate.read_text()
            return self._handle_interactive_gate("user_validation", gate_content)
        
        # Check for USER tasks before determining workflow phase
        if self.checklist_file.exists():
            current_task = self._get_current_task()
            if current_task is None and pending_user_validation_gate.exists():
                # A USER validation gate was just created, handle it
                gate_content = pending_user_validation_gate.read_text()
                return self._handle_interactive_gate("user_validation", gate_content)
        
        # Check what outputs exist to determine next phase
        current_outputs = {
            "exploration.md": (self.outputs_dir / "exploration.md").exists(),
            "success-criteria.md": (self.outputs_dir / "success-criteria.md").exists(),
            "plan.md": (self.outputs_dir / "plan.md").exists(),
            "changes.md": (self.outputs_dir / "changes.md").exists(),
            "orchestrator-log.md": (self.outputs_dir / "orchestrator-log.md").exists(),
            "verification.md": (self.outputs_dir / "verification.md").exists(),
            "completion-approved.md": (self.outputs_dir / "completion-approved.md").exists()
        }
        
        # Use workflow configuration to determine next agent
        next_agent = self.workflow_config.get_next_agent(current_outputs, self.outputs_dir)
        
        if next_agent is None:
            # Update status before returning completion
            self._update_status_file()
            return "complete", "All agents have completed successfully. Task marked complete."
        
        # Update status to reflect current workflow state
        self._update_status_file()
        
        # In headless mode, use workflow loop for automation
        if self.headless:
            # Show workflow header only once at the start of headless execution
            debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
            if not debug_mode and not hasattr(self, '_header_shown'):
                self._show_workflow_header()
                self._header_shown = True
            return self._execute_headless_workflow_loop()
        
        # Interactive mode: single agent execution
        agent_type, instructions = self._prepare_work_agent(next_agent)
        if agent_type in ["complete", "error"]:
            return agent_type, instructions
        result = self.agent_executor.execute_agent(agent_type, instructions)
        return agent_type, result

    def _show_workflow_header(self):
        """Show clean workflow header with task description"""
        task = self._get_current_task()
        if task:
            print(f"\nClaude Code Orchestrator running on task: {task}")
            print()
    
    def _show_agent_progress(self, agent_type, status="running"):
        """Show clean progress indicator for current agent"""
        debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        if not debug_mode:
            agent_display = {
                "explorer": "Exploring",
                "planner": "Planning", 
                "coder": "Coding",
                "verifier": "Verifying",
                "scribe": "Documenting"
            }
            
            if agent_type in agent_display:
                if status == "running":
                    print(f"{agent_display[agent_type]}...")
                elif status == "complete":
                    print(f"✓ {agent_display[agent_type]} complete")
                elif status == "failed":
                    print(f"✗ {agent_display[agent_type]} failed")

    def _show_verification_status(self):
        """Show verification pass/fail status"""
        debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        if not debug_mode:
            verification_file = self.outputs_dir / "verification.md"
            if verification_file.exists():
                try:
                    content = verification_file.read_text()
                    # Look for overall status line
                    for line in content.split('\n'):
                        if "Overall Status:" in line:
                            if "PASS" in line.upper():
                                print("✓ PASS - see verification.md for details")
                            elif "FAIL" in line.upper():
                                print("✗ FAIL - see verification.md for details")
                            else:
                                print("? NEEDS_REVIEW - see verification.md for details")
                            break
                    else:
                        print("? Status unclear - see verification.md for details")
                except Exception:
                    print("? Could not read verification status")

    def _execute_headless_workflow_loop(self):
        """Execute complete headless workflow until completion or gate"""
        max_iterations = 10  # Safety limit to prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Check what outputs exist to determine next phase
            current_outputs = {
                "exploration.md": (self.outputs_dir / "exploration.md").exists(),
                "success-criteria.md": (self.outputs_dir / "success-criteria.md").exists(),
                "plan.md": (self.outputs_dir / "plan.md").exists(),
                "changes.md": (self.outputs_dir / "changes.md").exists(),
                "orchestrator-log.md": (self.outputs_dir / "orchestrator-log.md").exists(),
                "verification.md": (self.outputs_dir / "verification.md").exists(),
                "completion-approved.md": (self.outputs_dir / "completion-approved.md").exists()
            }
            
            # Use workflow configuration to determine next agent
            next_agent = self.workflow_config.get_next_agent(current_outputs, self.outputs_dir)
            
            if next_agent is None:
                # Update status before returning completion
                self._update_status_file()
                debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                if not debug_mode:
                    print("✓ WORKFLOW COMPLETED SUCCESSFULLY")
                return "complete", "All agents have completed successfully. Task marked complete."
            
            # Check if this is a gate - handle interactively
            if next_agent.endswith('_gate'):
                gate_type = next_agent.replace('_gate', '')
                agent_type, gate_content = self._prepare_work_agent(next_agent)
                
                if agent_type == "error":
                    return agent_type, gate_content
                
                # Handle gate interactively
                result_type, result_message = self._handle_interactive_gate(gate_type, gate_content)
                
                if result_type == "exit":
                    return result_type, result_message
                elif result_type in ["approved", "modified", "retry", "completed", "new_task_created"]:
                    # Gate was handled, continue workflow
                    print(f"Gate decision: {result_message}")
                    continue
                else:
                    return "error", f"Unexpected gate result: {result_type}"
            
            # Update status to reflect current workflow state
            self._update_status_file()
            
            # Prepare and execute regular work agent internally
            agent_type, instructions = self._prepare_work_agent(next_agent)
            if agent_type == "error":
                return agent_type, instructions
            elif agent_type == "complete":
                # No more tasks to process
                debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                if not debug_mode:
                    print("✓ ALL TASKS COMPLETED SUCCESSFULLY")
                return agent_type, instructions
            elif agent_type == "user_checkpoint":
                # USER validation task encountered - halt headless execution
                return agent_type, instructions
            
            # Show agent progress
            self._show_agent_progress(agent_type, "running")
                
            # Execute agent instructions using real Claude CLI processes
            result = self.agent_executor._execute_headless(agent_type, instructions)
            
            if not result.startswith("✅"):
                # Agent failed
                self._show_agent_progress(agent_type, "failed")
                return agent_type, result
            else:
                # Agent succeeded
                self._show_agent_progress(agent_type, "complete")
                
                # Special handling for verifier to show pass/fail status
                if agent_type == "verifier":
                    self._show_verification_status()
                
        return "error", f"Headless workflow exceeded maximum iterations ({max_iterations})"

    def _prepare_work_agent(self, agent_type: str):
        """Dynamic agent preparation based on agent type"""
        
        if agent_type == "explorer":
            task = self._get_current_task()
            if not task:
                # Check if there are more tasks after this one
                if self._has_more_tasks():
                    return "user_checkpoint", "User validation checkpoint reached. Complete manual testing before continuing."
                else:
                    return "complete", "All tasks have been completed successfully! No more tasks in checklist."
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
                    if "## Testable Success Criteria" in line:
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
                    debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                    if debug_mode:
                        print("Unsupervised mode: Auto-approved criteria")
                    
                    # Continue to next agent
                    agent, instructions = self.get_continue_agent()
                    debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                    if debug_mode:
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
                if "## Testable Success Criteria" in line:
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
                verification_lower = verification_content.lower()
                
                # First check for explicit failure indicators - these BLOCK auto-approval
                failure_indicators = ["fail", "needs_review", "needs review", "error", "not ready", "incomplete"]
                if any(indicator in verification_lower for indicator in failure_indicators):
                    # Force interactive gate for failed verification
                    debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                    if debug_mode:
                        print("Unsupervised mode: Verification failed - forcing human review")
                    # Continue to interactive gate (don't auto-approve)
                    
                # Only auto-approve on explicit success indicators
                elif "pass" in verification_lower or "success" in verification_lower or "complete" in verification_lower:
                    # Auto-approve completion in unsupervised mode
                    debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                    if debug_mode:
                        print("Unsupervised mode: Verification passed - auto-approved completion")
                    self.approve_completion()
                    return "complete", "Task automatically completed in unsupervised mode"
                    
                else:
                    # Ambiguous verification - force human review
                    debug_mode = os.getenv('CLAUDE_ORCHESTRATOR_DEBUG', '').lower() in ('1', 'true', 'yes')
                    if debug_mode:
                        print("Unsupervised mode: Ambiguous verification - forcing human review")
                    # Continue to interactive gate
            
            verification_content = verification_file.read_text()
            
            # Extract overall status
            status_line = "Status not found"
            for line in verification_content.split('\n'):
                if "Overall Status:" in line:
                    status_line = line.strip()
                    break
                elif "Final Verification Status:" in line:
                    status_line = line.strip()
                    break
            
            return self.agent_factory.create_agent("completion_gate", status_line=status_line)
            
        else:
            # Generic agent preparation for work agents
            return self.agent_factory.create_agent(agent_type)

    def _get_current_task(self):
        """Extract current task from checklist, recognizing validation tasks"""
        
        if self.checklist_file.exists():
            content = self.checklist_file.read_text()
            lines = content.split('\n')
            
            for line in lines:
                if re.match(r'^\s*-\s*\[\s*\]\s*', line):
                    task = re.sub(r'^\s*-\s*\[\s*\]\s*', '', line)
                    task = re.sub(r'\s*\(.*\)\s*$', '', task)
                    task = task.strip()
                    
                    # Check if this is a USER task (validation, test, review, etc.)
                    if task.startswith('USER'):
                        # This is a human task - handle specially
                        return self._handle_user_validation(task)
                    elif task:
                        return task
        return None

    def _handle_user_validation(self, task):
        """Handle USER tasks by creating a user validation gate"""
        
        # Prevent multiple gate creation for the same validation
        validation_key = f"user_validation_{hash(task)}"
        if hasattr(self, '_current_validation_displayed') and self._current_validation_displayed == validation_key:
            return None
        self._current_validation_displayed = validation_key
        
        # Extract validation type and ID if present (e.g., "USER VALIDATION A", "USER TEST 3")
        import re
        match = re.match(r'USER\s+(\w+)\s*([A-Z0-9]*)', task)
        if match:
            validation_type = match.group(1)
            validation_id = match.group(2) if match.group(2) else ""
        else:
            validation_type = "TASK"
            validation_id = ""
        
        # Extract the task details after the colon if present  
        if ':' in task:
            colon_pos = task.find(':')
            task_details = task[colon_pos + 1:].strip()
        else:
            task_details = task
        
        # Create gate content for the USER validation
        from datetime import datetime
        gate_content = f"""# 🚪 USER VALIDATION GATE

## Validation Required: {validation_type} {validation_id}

### Task Description
{task}

### Validation Instructions
{task_details}

### What You Need to Do
1. Execute the validation steps described above
2. Test all functionality as specified
3. Document any issues found
4. Choose your decision below based on results

### Decision Required
- If ALL tests PASS: Choose `user-approve`
- If tests FAIL: Choose appropriate retry option
- To exit and resume later: Choose `exit`

### Started
{datetime.now().isoformat()}
"""
        
        # Create pending gate file
        pending_gate_file = self.outputs_dir / "pending-user_validation-gate.md"
        pending_gate_file.write_text(gate_content)
        
        # Return None to trigger gate handling in workflow
        return None

    def _generate_fix_task(self, validation_task, user_description):
        """Generate a fix task based on validation failure and user input"""
        
        # Extract validation context
        validation_type = "VALIDATION"
        validation_id = ""
        
        import re
        match = re.match(r'USER\s+(\w+)\s*([A-Z0-9]*)', validation_task)
        if match:
            validation_type = match.group(1)
            validation_id = match.group(2) if match.group(2) else ""
        
        # Extract what was being validated
        if ':' in validation_task:
            colon_pos = validation_task.find(':')
            validation_instructions = validation_task[colon_pos + 1:].strip()
        else:
            validation_instructions = validation_task
        
        # Generate contextual task description
        if user_description and user_description.strip():
            # User provided specific description
            fix_description = user_description.strip()
        else:
            # Generate generic fix task
            fix_description = f"Fix issues found during {validation_type} {validation_id}".strip()
        
        # Create comprehensive task description
        task_description = f"Fix validation failure: {fix_description}. This addresses issues found during {validation_type} {validation_id} where the test was: {validation_instructions}. Ensure all validation criteria are met before proceeding."
        
        return task_description

    def _insert_task_before_user_validation(self, new_task_description):
        """Insert a new task before the current USER validation task in the checklist"""
        
        if not self.checklist_file.exists():
            return False
        
        content = self.checklist_file.read_text()
        lines = content.split('\n')
        
        # Find the first incomplete USER validation task
        user_task_line_index = None
        user_task = None
        
        for i, line in enumerate(lines):
            if re.match(r'^\s*-\s*\[\s*\]\s*', line):
                task = re.sub(r'^\s*-\s*\[\s*\]\s*', '', line)
                task = re.sub(r'\s*\(.*\)\s*$', '', task)
                task = task.strip()
                
                if task.startswith('USER'):
                    user_task_line_index = i
                    user_task = task
                    break
        
        if user_task_line_index is None:
            print("No incomplete USER validation task found")
            return False
        
        # Create new task line with same indentation as USER task
        user_line = lines[user_task_line_index]
        indent_match = re.match(r'^(\s*-\s*\[\s*\]\s*)', user_line)
        indent = indent_match.group(1) if indent_match else '- [ ] '
        
        new_task_line = f"{indent}{new_task_description}"
        
        # Insert new task before the USER validation task
        lines.insert(user_task_line_index, new_task_line)
        
        # Write back to checklist
        self.checklist_file.write_text('\n'.join(lines))
        
        # Also add to tasks.md if it exists
        if self.tasks_file.exists():
            tasks_content = self.tasks_file.read_text()
            new_task_entry = f"\n## {new_task_description}\n[Added to fix validation failure]\n"
            
            # Find a good place to insert in tasks.md - before USER validation section
            if f"USER {user_task.split()[1]}" in tasks_content:
                # Insert before the USER validation section
                insertion_point = tasks_content.find(f"## USER {user_task.split()[1]}")
                if insertion_point != -1:
                    tasks_content = tasks_content[:insertion_point] + new_task_entry + tasks_content[insertion_point:]
                    self.tasks_file.write_text(tasks_content)
                else:
                    # Append at end if can't find specific section
                    self.tasks_file.write_text(tasks_content + new_task_entry)
            else:
                # Append at end
                self.tasks_file.write_text(tasks_content + new_task_entry)
        
        print(f"✅ Inserted new task: {new_task_description}")
        print(f"📍 Positioned before: {user_task}")
        return True

    def _get_current_user_validation_task(self):
        """Get the current USER validation task that triggered the gate"""
        
        if not self.checklist_file.exists():
            return None
        
        content = self.checklist_file.read_text()
        lines = content.split('\n')
        
        # Find the first incomplete USER validation task
        for line in lines:
            if re.match(r'^\s*-\s*\[\s*\]\s*', line):
                task = re.sub(r'^\s*-\s*\[\s*\]\s*', '', line)
                task = re.sub(r'\s*\(.*\)\s*$', '', task)
                task = task.strip()
                
                if task.startswith('USER'):
                    return task
        
        return None

    def _retry_last_implementation_task(self):
        """Mark the previous implementation task (non-USER) as incomplete to retry it"""
        
        if not self.checklist_file.exists():
            return False
        
        content = self.checklist_file.read_text()
        lines = content.split('\n')
        
        # Find the last completed non-USER task before current USER validation
        user_task_found = False
        last_impl_task_line = None
        
        for i, line in enumerate(lines):
            # Check if this is the current USER validation task
            if re.match(r'^\s*-\s*\[\s*\]\s*', line):
                task = re.sub(r'^\s*-\s*\[\s*\]\s*', '', line)
                task = re.sub(r'\s*\(.*\)\s*$', '', task).strip()
                if task.startswith('USER'):
                    user_task_found = True
                    break
            
            # Look for completed implementation tasks
            if re.match(r'^\s*-\s*\[x\]\s*', line):
                task = re.sub(r'^\s*-\s*\[x\]\s*', '', line)
                task = re.sub(r'\s*\(.*\)\s*$', '', task).strip()
                if not task.startswith('USER'):
                    last_impl_task_line = i
        
        if not user_task_found or last_impl_task_line is None:
            return False
        
        # Mark the last implementation task as incomplete
        old_line = lines[last_impl_task_line]
        new_line = old_line.replace('[x]', '[ ]')
        lines[last_impl_task_line] = new_line
        
        # Write back to checklist
        self.checklist_file.write_text('\n'.join(lines))
        
        # Extract task description for logging
        task_desc = re.sub(r'^\s*-\s*\[\s*\]\s*', '', new_line)
        task_desc = re.sub(r'\s*\(.*\)\s*$', '', task_desc).strip()
        
        print(f"🔄 Marked for retry: {task_desc}")
        return True

    def _has_more_tasks(self):
        """Check if there are any uncompleted tasks in the checklist"""
        if self.checklist_file.exists():
            content = self.checklist_file.read_text()
            lines = content.split('\n')
            for line in lines:
                if re.match(r'^\s*-\s*\[\s*\]\s*', line):
                    return True
        return False
        
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
                if "## Testable Success Criteria" in line:
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
                
                # Show workflow header with next task
                self._show_workflow_header()
                
                agent, instructions = self.get_continue_agent()
                print("\n" + "="*60)
                print("AUTO-STARTING - AGENT: " + agent.upper())
                print("="*60)
                print(instructions)
                print("="*60)
            else:
                print("Execute the slash-command `/orchestrate clean` to prepare for continue task")
                print("="*60)
        
    def approve_user_validation(self):
        """Approve USER validation and mark task complete"""
        task = self._get_current_task()
        if task and task.startswith('USER'):
            # Mark the USER task as complete in the checklist
            self._update_checklist(task, completed=True)
            
            # Log the approval
            from datetime import datetime
            approval_file = self.outputs_dir / "user-validation-approved.md"
            approval_content = f"""# User Validation Approved

## Task
{task}

## Status
APPROVED - Tests passed

## Approved At
{datetime.now().isoformat()}

## Next Steps
Continuing to next task in workflow
"""
            approval_file.write_text(approval_content)
            
            print(f"✅ USER VALIDATION APPROVED")
            print(f"Task marked complete: {task}")
            print(f"Continuing to next task...")
        
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
            "criteria-modification-request.md",
            "pending-criteria-gate.md",
            "pending-completion-gate.md",
            "pending-user_validation-gate.md"
            # Note: orchestrator-log.md is preserved across cycles for historical record
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
BOOTSTRAP MODE: Generate human-in-the-loop task structure for the project

CRITICAL REQUIREMENTS:
1. Generate THREE files: tasks-checklist.md, tasks.md, and concept.md
2. Each task must be ONE PARAGRAPH on a SINGLE LINE (no line breaks within tasks)
3. Create 10-15 tasks MAXIMUM per taskset
4. Balance tasks for roughly equal complexity and likelihood of success
5. Embed USER validation checkpoints directly in the task sequence
6. USER tasks must start with "USER" (e.g., USER VALIDATION, USER TEST, USER REVIEW)

FILE STRUCTURE TO CREATE:

## .claude/concept.md
High-level design document that:
- Describes the overall goal and architecture
- Defines success criteria for the entire taskset
- Explains key design decisions and trade-offs
- Provides context for all tasks
- Self-contained reference (doesn't reference other files)

## .claude/tasks.md
Detailed task descriptions where:
- Each task is a comprehensive single paragraph
- Tasks frequently reference concept.md for design rationale
- USER tasks are clearly marked and detailed
- USER tasks specify exact commands/tests to run
- Each task ~500-1000 characters for adequate detail

## .claude/tasks-checklist.md
Actionable checklist where:
- Each line is one task (matching tasks.md)
- Tasks reference both tasks.md and concept.md
- Format: - [ ] Brief description referencing details in tasks.md and concept in concept.md
- USER tasks clearly start with "USER" keyword

TASK STRUCTURE PATTERN:
1. Implementation task (agents do work)
2. USER VALIDATION task (human tests and verifies)
3. Implementation task (agents continue)
4. USER TEST task (human tests again)
[Repeat pattern throughout]

USER TASK FORMAT:
"USER [TYPE] [ID]: [Description of what to test] by executing these specific commands: (1) [command], (2) [command], (3) [verification step], checking that [expected outcome], and documenting results in [location] before proceeding - DO NOT CONTINUE if [failure condition]"

Types can be: VALIDATION, TEST, REVIEW, CHECK, VERIFY, etc.

ANALYSIS TO PERFORM:
1. Examine project structure and existing code
2. Identify the primary objective/problem to solve
3. Break down into logical implementation chunks
4. Insert USER checkpoints after each major feature
5. Ensure each task is independently testable

QUESTIONS TO ASK USER:
1. "What is the primary goal for this taskset?"
2. "What constitutes success for this work?"
3. "Are there specific areas that need extra validation?"
4. "What's your risk tolerance for this implementation?"
5. "Should this be production-ready or prototype?"

TASK BALANCING:
- Each task should take roughly 1-3 agent cycles
- USER tasks should take 5-15 minutes of human time
- Complex features split across multiple tasks with validation between
- No task should be a single line of code change
- No task should be a complete rewrite

Begin by analyzing the current directory and asking about the goal.
"""
        
        print("\n" + "="*60)
        print("BOOTSTRAP MODE: Generating Initial Tasks")
        print("="*60)
        print(bootstrap_instructions)
        print("="*60)

    def bootstrap_with_validation(self):
        """Enhanced bootstrap that generates human-in-the-loop task structure"""
        
        # Check if bootstrap files already exist
        concept_file = self.claude_dir / "concept.md"
        if concept_file.exists():
            print("Warning: concept.md already exists. Rename or remove existing files first.")
            return
        
        # Set bootstrap mode flag for agents
        bootstrap_flag = self.claude_dir / ".bootstrap-mode"
        bootstrap_flag.write_text("active")
        
        # Provide enhanced instructions with validation pattern
        print("\n" + "="*60)
        print("HUMAN-IN-THE-LOOP BOOTSTRAP MODE")
        print("="*60)
        print("This will generate three files with embedded validation:")
        print("1. concept.md - Overall design and architecture")
        print("2. tasks.md - Detailed task descriptions") 
        print("3. tasks-checklist.md - Actionable checklist")
        print()
        print("USER tasks (starting with 'USER') will halt the orchestrator")
        print("for manual validation/testing before continuing.")
        print("="*60)
        
        # Call the main bootstrap method
        self.bootstrap_tasks()
        
        # Clean up bootstrap flag after completion
        if bootstrap_flag.exists():
            bootstrap_flag.unlink()
        
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


def serve_command(args):
    """Start dashboard and API servers with health monitoring"""
    
    # Health check function
    def check_server_health(host, port, endpoint="/", timeout=5):
        try:
            url = f"http://{host}:{port}{endpoint}"
            response = urllib.request.urlopen(url, timeout=timeout)
            return response.getcode() == 200
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            return False
    
    # Find available ports
    dashboard_port = find_available_port(5678, 20)
    if dashboard_port == 5678:
        print(f"Dashboard server will use port {dashboard_port}")
    else:
        print(f"Port 5678 busy, using fallback port {dashboard_port}")
    
    api_port = find_available_port(8000, 20)
    if api_port == 8000:
        print(f"API server will use port {api_port}")
    else:
        print(f"Port 8000 busy, using fallback port {api_port}")
    
    # Initialize process manager (check for meta mode via environment)
    meta_mode = os.getenv('CLAUDE_ORCHESTRATOR_META_MODE') == '1'
    process_manager = ProcessManager(meta_mode=meta_mode)
    
    # Health monitoring state
    health_monitoring_active = True
    health_check_thread = None
    
    def health_monitor():
        """Periodic health check for both servers"""
        while health_monitoring_active:
            try:
                time.sleep(30)  # Check every 30 seconds
                if not health_monitoring_active:
                    break
                    
                # Check dashboard health
                if not check_server_health('localhost', dashboard_port):
                    print(f"Warning: Dashboard server on port {dashboard_port} is unresponsive")
                
                # Check API server health if it's running
                running_processes = process_manager.get_running_processes()
                if 'api_server' in running_processes:
                    if not check_server_health('localhost', api_port, '/health'):
                        print(f"Warning: API server on port {api_port} is unresponsive")
                        
            except Exception as e:
                if health_monitoring_active:
                    print(f"Health check error: {e}")
    
    def cleanup_and_exit(signal_num=None, frame=None):
        """Cleanup function for graceful shutdown"""
        nonlocal health_monitoring_active, health_check_thread
        
        print("\nShutting down servers...")
        health_monitoring_active = False
        
        # Wait for health check thread to finish
        if health_check_thread and health_check_thread.is_alive():
            health_check_thread.join(timeout=2)
        
        # Cleanup all processes
        success = process_manager.cleanup_all_processes()
        if success:
            print("All servers stopped successfully")
        else:
            print("Warning: Some processes may not have terminated properly")
        
        sys.exit(0 if success else 1)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    
    try:
        # Start API server as subprocess
        print(f"Starting API server on port {api_port}...")
        api_cmd = [sys.executable, "-c", f"""
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({{'status': 'healthy', 'port': {api_port}}}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[API Server] {{format % args}}")

try:
    server = HTTPServer(('localhost', {api_port}), APIHandler)
    print(f"API server started on port {api_port}")
    server.serve_forever()
except KeyboardInterrupt:
    print("API server stopped")
except Exception as e:
    print(f"API server error: {{e}}")
    sys.exit(1)
"""]
        
        api_process = subprocess.Popen(api_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process_manager.register_process('api_server', api_process)
        
        # Give API server time to start
        time.sleep(2)
        
        # Verify API server started
        if check_server_health('localhost', api_port, '/health'):
            print(f"API server healthy on http://localhost:{api_port}")
        else:
            print(f"Warning: API server may not have started properly on port {api_port}")
        
        # Start health monitoring in background
        health_check_thread = threading.Thread(target=health_monitor, daemon=True)
        health_check_thread.start()
        
        # Open browser unless --no-browser flag is set
        dashboard_url = f"http://localhost:{dashboard_port}"
        if not args.no_browser:
            print(f"Opening browser to {dashboard_url}")
            try:
                webbrowser.open(dashboard_url)
            except Exception as e:
                print(f"Could not open browser: {e}")
        else:
            print(f"Dashboard available at: {dashboard_url}")
        
        # Start dashboard server (this will block)
        print(f"Starting dashboard server on port {dashboard_port}...")
        print("Press Ctrl+C to stop all servers")
        print("-" * 50)
        
        # Import and start dashboard server
        import dashboard_server
        success = dashboard_server.start_dashboard_server(dashboard_port, 'localhost')
        
        # If dashboard server exits, cleanup
        cleanup_and_exit()
        
    except KeyboardInterrupt:
        cleanup_and_exit()
    except Exception as e:
        print(f"Error starting servers: {e}")
        cleanup_and_exit()


def show_help():
    """Display help information about available commands"""
    print("\nAvailable commands:")
    print("  Workflow: start, continue, interactive, status, clean, complete, fail, bootstrap")
    print("  Gates: approve-criteria, modify-criteria, retry-explorer")
    print("         approve-completion, retry-from-planner, retry-from-coder, retry-from-verifier")
    print("  Mode: unsupervised, supervised")
    print("  Interactive mode: Runs persistent workflow with interactive gates")

def main():
    """CLI entry point - designed for actual workflow operations"""
    
    parser = argparse.ArgumentParser(description='Claude Code Orchestrator')
    parser.add_argument('command', nargs='?', default='continue',
                       help='Command to execute (default: continue)')
    parser.add_argument('--no-browser', action='store_true',
                       help='Suppress browser opening for CI/CD environments')
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive mode (default is headless)')
    parser.add_argument('modification_text', nargs='*',
                       help='Modification text for modify-criteria command')
    
    args = parser.parse_args()
    command = args.command
    
    # If command is "meta", treat it as "continue" but keep "meta" in sys.argv for mode detection
    # Also handle empty string when in meta mode (when $ARGUMENTS is empty in slash command)
    if command == "meta" or (command == "" and "meta" in sys.argv):
        command = "continue"
    
    orchestrator = ClaudeCodeOrchestrator(no_browser=args.no_browser, headless=not args.interactive)
    
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
        
    elif command == "interactive":
        # Start persistent interactive workflow
        print("\n" + "="*60)
        print("STARTING INTERACTIVE WORKFLOW")
        print("="*60)
        print("Running persistent workflow with interactive gates...")
        print("Use 'exit' at any gate to save state and quit gracefully.")
        print("="*60)
        
        while True:
            try:
                agent, result = orchestrator.get_continue_agent()
                
                if agent == "complete":
                    print("\n" + "="*60)
                    print("WORKFLOW COMPLETED SUCCESSFULLY!")
                    print("="*60)
                    print(result)
                    break
                elif agent == "exit":
                    print("\n" + "="*60)
                    print("WORKFLOW PAUSED")
                    print("="*60)
                    print(result)
                    break
                elif agent == "error":
                    print("\n" + "="*60)
                    print("WORKFLOW ERROR")
                    print("="*60)
                    print(result)
                    break
                else:
                    # Continue workflow automatically
                    continue
                    
            except KeyboardInterrupt:
                print("\n\nWorkflow interrupted. Use 'continue' to resume or 'clean' to start fresh.")
                break
            except Exception as e:
                print(f"\nUnexpected error: {e}")
                print("Use 'continue' to resume or 'clean' to start fresh.")
                break
        
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
        # Check for bootstrap mode flag
        if "--with-validation" in sys.argv or "--hil" in sys.argv:
            orchestrator.bootstrap_with_validation()
        else:
            # Legacy bootstrap
            orchestrator.bootstrap_tasks()
        
    elif command == "unsupervised":
        orchestrator.enable_unsupervised_mode()
        
    elif command == "supervised":
        orchestrator.disable_unsupervised_mode()
        
    elif command == "stop":
        # Stop all orchestrator processes system-wide
        # Check if running in meta mode
        meta_mode = 'meta' in sys.argv
        process_manager = ProcessManager(meta_mode=meta_mode)
        success = process_manager.cleanup_system_wide()
        if success:
            print("All orchestrator processes have been stopped.")
            sys.exit(0)
        else:
            print("Warning: Some processes may not have been terminated properly.")
            sys.exit(1)
        
    elif command == "serve":
        serve_command(args)
        
    elif command == "help":
        show_help()
        
    else:
        print("Unknown command: " + command)
        show_help()


if __name__ == "__main__":
    main()