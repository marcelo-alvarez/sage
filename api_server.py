#!/usr/bin/env python3
"""
API Server for Claude Code Orchestrator
Provides HTTP endpoint for workflow status retrieval
"""

import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import sys
import signal
import threading
import time
import subprocess
import os
import webbrowser


class StatusReader:
    """Reads and parses workflow status from orchestrator files"""
    
    def __init__(self):
        self.status_emoji_map = {
            '⏳': 'pending',
            '✅': 'completed',
            '✓': 'completed',
            '🔄': 'in-progress'
        }
        
    def read_status(self, mode='regular'):
        """Read workflow status from appropriate directory"""
        outputs_dir = '.agent-outputs-meta' if mode == 'meta' else '.agent-outputs'
        status_file = Path(outputs_dir) / 'current-status.md'
        
        print(f"[StatusReader] Reading status for mode '{mode}' from {status_file}")
        
        try:
            if not status_file.exists():
                print(f"[StatusReader] Status file does not exist: {status_file}")
                return self._get_default_status()
                
            with open(status_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"[StatusReader] Read {len(content)} characters from status file")
            
            if not content.strip():
                print(f"[StatusReader] Status file is empty, using default status")
                return self._get_default_status()
                
            parsed_status = self._parse_status_content(content)
            print(f"[StatusReader] Successfully parsed status with {len(parsed_status.get('workflow', []))} workflow items")
            return parsed_status
            
        except Exception as e:
            print(f"[StatusReader] Error reading status file {status_file}: {e}")
            return self._get_default_status()
    
    def _parse_status_content(self, content):
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
                    
                    # Determine agent type
                    agent_type = 'gate' if 'gate' in agent_name.lower() else 'agent'
                    
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
        
        return {
            'currentTask': current_task,
            'workflow': workflow,
            'agents': agents
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
    
    def _get_default_status(self):
        """Return default status when files are missing"""
        return {
            'currentTask': 'No active task',
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
            ]
        }


class StatusHandler(BaseHTTPRequestHandler):
    """HTTP request handler for status endpoint"""
    
    def __init__(self, *args, **kwargs):
        try:
            self.status_reader = StatusReader()
            print(f"[API] StatusHandler initialized successfully")
        except Exception as e:
            print(f"[API] Error initializing StatusReader: {e}")
            # Create a minimal fallback reader
            self.status_reader = None
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/api/status':
            self._handle_status_request(parsed_url)
        elif parsed_url.path.startswith('/api/outputs/'):
            self._handle_outputs_request(parsed_url)
        else:
            self._send_error(404, 'Not Found')
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/api/gate-decision':
            self._handle_gate_decision_request(parsed_url)
        else:
            self._send_error(404, 'Not Found')
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _handle_status_request(self, parsed_url):
        """Handle /api/status endpoint"""
        try:
            print(f"[API] Processing status request: {parsed_url.path}?{parsed_url.query}")
            
            # Check if status reader is available
            if self.status_reader is None:
                self._send_error(500, 'StatusReader not initialized. Server may have startup issues.')
                return
            
            # Parse query parameters
            query_params = parse_qs(parsed_url.query)
            mode = query_params.get('mode', ['regular'])[0]
            
            # Validate mode parameter
            if mode not in ['regular', 'meta']:
                print(f"[API] Invalid mode parameter: {mode}")
                self._send_error(400, 'Invalid mode parameter. Use "regular" or "meta".')
                return
            
            # Read status data
            print(f"[API] Reading status data for mode: {mode}")
            status_data = self.status_reader.read_status(mode)
            
            # Validate response data
            if not status_data or not isinstance(status_data, dict):
                print(f"[API] Invalid status data returned: {type(status_data)}")
                self._send_error(500, 'Failed to read valid status data')
                return
            
            print(f"[API] Sending status response with {len(status_data)} fields")
            # Send JSON response
            self._send_json_response(status_data)
            
        except Exception as e:
            print(f"Error handling status request: {e}")
            self._send_error(500, 'Internal Server Error')
    
    def _send_json_response(self, data):
        """Send JSON response with appropriate headers"""
        response_body = json.dumps(data, indent=2).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        
        self.wfile.write(response_body)
    
    def _send_error(self, code, message):
        """Send error response"""
        error_data = {'error': message, 'code': code}
        response_body = json.dumps(error_data).encode('utf-8')
        
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        
        self.wfile.write(response_body)
    
    def _handle_gate_decision_request(self, parsed_url):
        """Handle /api/gate-decision endpoint"""
        try:
            # Parse query parameters for mode
            query_params = parse_qs(parsed_url.query)
            mode = query_params.get('mode', ['regular'])[0]
            
            # Validate mode parameter
            if mode not in ['regular', 'meta']:
                self._send_error(400, 'Invalid mode parameter. Use "regular" or "meta".')
                return
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error(400, 'Missing request body')
                return
            
            request_body = self.rfile.read(content_length).decode('utf-8')
            
            # Parse JSON body
            try:
                decision_data = json.loads(request_body)
            except json.JSONDecodeError:
                self._send_error(400, 'Invalid JSON in request body')
                return
            
            # Validate required fields
            decision_type = decision_data.get('decision_type')
            if not decision_type:
                self._send_error(400, 'Missing required field: decision_type')
                return
            
            # Validate decision type
            valid_decisions = [
                'approve-criteria', 'modify-criteria', 'retry-explorer',
                'approve-completion', 'retry-from-planner', 'retry-from-coder', 'retry-from-verifier'
            ]
            if decision_type not in valid_decisions:
                self._send_error(400, f'Invalid decision_type. Must be one of: {", ".join(valid_decisions)}')
                return
            
            # Process the gate decision
            result = self._process_gate_decision(decision_type, mode, decision_data)
            
            if result['success']:
                self._send_json_response(result)
            else:
                self._send_error(500, result['error'])
            
        except Exception as e:
            print(f"Error handling gate decision request: {e}")
            self._send_error(500, 'Internal Server Error')
    
    def _process_gate_decision(self, decision_type, mode, decision_data):
        """Process gate decision by calling orchestrate.py"""
        try:
            # Build command
            orchestrate_path = os.path.expanduser('~/.claude-orchestrator/orchestrate.py')
            cmd = ['python3', orchestrate_path, decision_type]
            
            if mode == 'meta':
                cmd.append('meta')
            
            # Add modification text if provided
            if decision_type == 'modify-criteria' and 'modifications' in decision_data:
                cmd.append(decision_data['modifications'])
            
            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Read updated status after decision processing
                status_data = self.status_reader.read_status(mode)
                
                return {
                    'success': True,
                    'decision_type': decision_type,
                    'mode': mode,
                    'message': 'Gate decision processed successfully',
                    'workflow_state': status_data,
                    'orchestrator_output': result.stdout.strip()
                }
            else:
                return {
                    'success': False,
                    'error': f'Orchestrator command failed: {result.stderr.strip() or result.stdout.strip()}'
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Gate decision processing timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing gate decision: {str(e)}'
            }
    
    def _handle_outputs_request(self, parsed_url):
        """Handle /api/outputs/{filename} endpoint"""
        try:
            # Extract filename from path
            path_parts = parsed_url.path.split('/')
            if len(path_parts) != 4 or path_parts[3] == '':
                self._send_error(400, 'Invalid URL format. Use /api/outputs/{filename}')
                return
            
            filename = path_parts[3]
            
            # Validate filename
            if not self._validate_output_filename(filename):
                self._send_error(400, 'Invalid filename. Only allowed agent output files can be accessed.')
                return
            
            # Parse query parameters for mode
            query_params = parse_qs(parsed_url.query)
            mode = query_params.get('mode', ['regular'])[0]
            
            # Validate mode parameter
            if mode not in ['regular', 'meta']:
                self._send_error(400, 'Invalid mode parameter. Use "regular" or "meta".')
                return
            
            # Get appropriate outputs directory
            outputs_dir = self._get_outputs_directory(mode)
            file_path = outputs_dir / filename
            
            # Check if file exists
            if not file_path.exists():
                self._send_error(404, f'File "{filename}" not found')
                return
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Send markdown response
                self._send_markdown_response(content)
                
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                self._send_error(500, 'Error reading file')
            
        except Exception as e:
            print(f"Error handling outputs request: {e}")
            self._send_error(500, 'Internal Server Error')
    
    def _validate_output_filename(self, filename):
        """Validate that filename is safe and allowed"""
        # Check for path separators and relative path components
        if '/' in filename or '\\' in filename or '..' in filename:
            return False
        
        # Check for absolute paths or hidden files
        if filename.startswith('/') or filename.startswith('.'):
            return False
        
        # Define allowlist of permitted agent output files
        allowed_files = {
            'exploration.md',
            'plan.md', 
            'changes.md',
            'verification.md',
            'current-status.md',
            'documentation.md',
            'success-criteria.md'
        }
        
        # Check if file is in allowlist
        if filename in allowed_files:
            return True
        
        # Check for instructions files pattern
        if filename.endswith('-instructions.md'):
            return True
        
        return False
    
    def _get_outputs_directory(self, mode):
        """Get appropriate outputs directory based on mode"""
        if mode == 'meta':
            return Path('.agent-outputs-meta')
        else:
            return Path('.agent-outputs')
    
    def _send_markdown_response(self, content):
        """Send markdown content response with appropriate headers"""
        response_body = content.encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/markdown; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        
        self.wfile.write(response_body)
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[{self.log_date_time_string()}] {format % args}")


class OrchestratorAPIServer:
    """Main API server class"""
    
    def __init__(self, port=8000, host='localhost', setup_signals=True):
        self.port = port
        self.host = host
        self.setup_signals = setup_signals
        self.server = None
        self.server_thread = None
        self._running = False
    
    def start(self):
        """Start the API server"""
        try:
            print(f"[API Server] Initializing HTTPServer on {self.host}:{self.port}")
            self.server = HTTPServer((self.host, self.port), StatusHandler)
            
            # Validate server was created successfully
            if not self.server:
                print(f"[API Server] Failed to create HTTPServer instance")
                return False
            
            print(f"[API Server] HTTPServer created successfully")
            self._running = True
            
            print(f"Starting Claude Code Orchestrator API server on {self.host}:{self.port}")
            print(f"Status endpoint: http://{self.host}:{self.port}/api/status")
            print(f"Gate decision endpoint: http://{self.host}:{self.port}/api/gate-decision")
            print(f"With meta mode: http://{self.host}:{self.port}/api/status?mode=meta")
            print("Press Ctrl+C to stop the server")
            
            # Set up signal handlers for graceful shutdown (only in main thread)
            if self.setup_signals:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Open dashboard in browser
            try:
                webbrowser.open('http://localhost:5678/dashboard/index.html')
            except Exception as e:
                print(f"Failed to open dashboard in browser: {e}")
            
            # Start server
            print(f"[API Server] Starting serve_forever() on {self.host}:{self.port}")
            self.server.serve_forever()
            
        except OSError as e:
            print(f"[API Server] OSError starting server: {e}")
            if "Address already in use" in str(e):
                print(f"Port {self.port} is already in use. Try a different port.")
            self._running = False
            return False
        except Exception as e:
            print(f"[API Server] Unexpected error starting server: {e}")
            self._running = False
            return False
        except KeyboardInterrupt:
            self.stop()
        
        return True
    
    def start_background(self):
        """Start server in background thread"""
        if self._running:
            print("Server is already running")
            return True
            
        # Create a separate start method for background that doesn't use signals
        def start_without_signals():
            try:
                print(f"[API Server Background] Initializing HTTPServer on {self.host}:{self.port}")
                self.server = HTTPServer((self.host, self.port), StatusHandler)
                
                # Validate server was created successfully
                if not self.server:
                    print(f"[API Server Background] Failed to create HTTPServer instance")
                    self._running = False
                    return
                
                print(f"[API Server Background] HTTPServer created successfully")
                self._running = True
                
                print(f"Starting Claude Code Orchestrator API server on {self.host}:{self.port}")
                print(f"Status endpoint: http://{self.host}:{self.port}/api/status")
                print(f"Gate decision endpoint: http://{self.host}:{self.port}/api/gate-decision")
                print(f"With meta mode: http://{self.host}:{self.port}/api/status?mode=meta")
                
                # Start server without signal handlers (background mode)
                print(f"[API Server Background] Starting serve_forever() on {self.host}:{self.port}")
                self.server.serve_forever()
                
            except OSError as e:
                print(f"[API Server Background] OSError starting server: {e}")
                if "Address already in use" in str(e):
                    print(f"Port {self.port} is already in use. Try a different port.")
                self._running = False
            except Exception as e:
                print(f"[API Server Background] Unexpected error starting server: {e}")
                self._running = False
            
        self.server_thread = threading.Thread(target=start_without_signals, daemon=True)
        self.server_thread.start()
        
        # Give server time to start
        time.sleep(0.5)
        
        return self._running
    
    def stop(self):
        """Stop the API server"""
        if self.server:
            print("\nShutting down server...")
            self._running = False
            self.server.shutdown()
            self.server.server_close()
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=2)
            
            print("Server stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stop()
        sys.exit(0)
    
    def is_running(self):
        """Check if server is running"""
        return self._running


def main():
    """Main entry point for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude Code Orchestrator API Server')
    parser.add_argument('--port', type=int, default=8000, help='Port to run server on (default: 8000)')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--background', action='store_true', help='Run server in background')
    
    args = parser.parse_args()
    
    server = OrchestratorAPIServer(port=args.port, host=args.host)
    
    if args.background:
        if server.start_background():
            print(f"Server started in background on {args.host}:{args.port}")
        else:
            print("Failed to start server in background")
            sys.exit(1)
    else:
        server.start()


if __name__ == '__main__':
    main()