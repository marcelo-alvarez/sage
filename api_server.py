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
import socket
from workflow_status import StatusReader, get_workflow_status
# ClaudeCodeOrchestrator now run in separate process via subprocess

# Global state for concurrent operation tracking
OPERATION_STATE = {
    'current_operation': None,  # 'idle', 'starting', 'continuing', 'cleaning'
    'start_time': None,
    'pid': None
}

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
    
    # If no ports in requested range, try higher range for API server
    if start_port == 8000:
        for port in range(9000, 9020):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('localhost', port))
                    return port
            except OSError:
                continue
    
    raise OSError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")




class StatusHandler(BaseHTTPRequestHandler):
    """HTTP request handler for status endpoint"""
    
    def __init__(self, *args, **kwargs):
        try:
            # Get project root from current working directory (set by subprocess cwd parameter)
            project_root = Path(os.getcwd())
            self.project_root = project_root  # Store for later use
            self.status_reader = StatusReader(project_root=project_root)
            print(f"[API] StatusHandler initialized successfully with project_root: {project_root.absolute()}")
        except Exception as e:
            print(f"[API] Error initializing StatusReader: {e}")
            # Store project_root even if StatusReader fails
            self.project_root = Path(os.getcwd())
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
        elif parsed_url.path == '/api/execute':
            self._handle_execute_request(parsed_url)
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
            
            # Use fallback method if status reader is unavailable
            if self.status_reader is None:
                print(f"[API] StatusReader unavailable, using fallback method")
                try:
                    # Parse query parameters
                    query_params = parse_qs(parsed_url.query)
                    mode = query_params.get('mode', ['regular'])[0]
                    
                    # Use get_workflow_status as fallback
                    status_data = get_workflow_status(project_root=self.project_root, mode=mode)
                    self._send_json_response(status_data)
                    return
                except Exception as fallback_error:
                    print(f"[API] Fallback method also failed: {fallback_error}")
                    self._send_error(500, 'StatusReader not initialized and fallback failed. Server may have startup issues.')
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
            status_data = get_workflow_status(project_root=self.project_root, mode=mode)
            
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
                'approve-completion', 'retry-from-planner', 'retry-from-coder', 'retry-from-verifier',
                'user-approve', 'new-task', 'retry-last-task', 'exit'
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
            
            # Add task description for new-task decision
            if decision_type == 'new-task' and 'description' in decision_data:
                cmd.append(decision_data['description'])
            
            # Execute command with reduced timeout to prevent blocking
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                # Read updated status after decision processing
                status_data = get_workflow_status(project_root=self.project_root, mode=mode)
                
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
                'error': 'Gate decision processing timed out after 15 seconds. Try again or check orchestrator logs.'
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
            
            # Check if file exists in outputs directory, if not try claude directory for checklist files
            if not file_path.exists():
                if filename == 'tasks-checklist.md':
                    # Try .claude or .claude-meta directory for checklist files
                    claude_dir = Path('.claude-meta') if mode == 'meta' else Path('.claude')
                    claude_file_path = claude_dir / filename
                    if claude_file_path.exists():
                        file_path = claude_file_path
                    else:
                        self._send_error(404, f'File "{filename}" not found in either outputs or claude directories')
                        return
                else:
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
            'success-criteria.md',
            'pending-user_validation-gate.md',
            'tasks-checklist.md'
        }
        
        # Check if file is in allowlist
        if filename in allowed_files:
            return True
        
        # Check for instructions files pattern
        if filename.endswith('-instructions.md'):
            return True
        
        # Check for log files pattern
        if filename.endswith('-log.txt'):
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
    
    def _handle_execute_request(self, parsed_url):
        """Handle /api/execute endpoint for command execution"""
        try:
            # Read request body first
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error(400, 'Missing request body')
                return
            
            request_body = self.rfile.read(content_length).decode('utf-8')
            
            # Parse JSON body
            try:
                execute_data = json.loads(request_body)
            except json.JSONDecodeError:
                self._send_error(400, 'Invalid JSON in request body')
                return
            
            # Get mode from request body first, then query params as fallback
            query_params = parse_qs(parsed_url.query)
            mode = execute_data.get('mode') or query_params.get('mode', ['regular'])[0]
            
            # Validate mode parameter
            if mode not in ['regular', 'meta']:
                self._send_error(400, 'Invalid mode parameter. Use "regular" or "meta".')
                return
            
            # Validate required fields
            command = execute_data.get('command')
            if not command:
                self._send_error(400, 'Missing required field: command')
                return
            
            # Validate command against whitelist
            valid_commands = ['start', 'continue', 'status', 'clean']
            if command not in valid_commands:
                self._send_error(400, f'Invalid command. Must be one of: {", ".join(valid_commands)}')
                return
            
            # Check for concurrent operations
            global OPERATION_STATE
            if OPERATION_STATE['current_operation'] and OPERATION_STATE['current_operation'] != 'idle':
                if command not in ['status']:  # Status is always allowed
                    self._send_error(409, f'Operation in progress: {OPERATION_STATE["current_operation"]}')
                    return
            
            # Allow meta-mode commands to run in meta mode
            print(f"[API Execute] Executing {command} in {mode} mode")
            
            # Execute the command
            result = self._execute_orchestrator_command(command, mode, execute_data)
            
            if result['success']:
                self._send_json_response(result)
            else:
                self._send_error(500, result['error'])
            
        except Exception as e:
            print(f"Error handling execute request: {e}")
            self._send_error(500, 'Internal Server Error')
    
    def _execute_orchestrator_command(self, command, mode, execute_data):
        """Execute orchestrator command in separate process"""
        try:
            global OPERATION_STATE
            
            # Update operation state for non-status commands
            if command != 'status':
                OPERATION_STATE['current_operation'] = command
                OPERATION_STATE['start_time'] = time.time()
                OPERATION_STATE['pid'] = os.getpid()
            
            result_data = {
                'success': True,
                'command': command,
                'mode': mode,
                'pid': os.getpid(),
                'timestamp': time.time()
            }
            
            try:
                if command == 'start':
                    # Run orchestrator in separate process to avoid blocking API server
                    import subprocess
                    cmd = [sys.executable, 'orchestrate.py', 'start']
                    if mode == 'meta':
                        cmd.append('meta')
                    
                    # Start the process in background with shorter timeout handling
                    try:
                        process = subprocess.Popen(cmd, 
                                                   stdout=subprocess.PIPE, 
                                                   stderr=subprocess.PIPE,
                                                   cwd=os.getcwd(),
                                                   start_new_session=True)  # Prevent signal propagation
                    except Exception as start_error:
                        OPERATION_STATE['current_operation'] = 'idle'
                        result_data.update({
                            'success': False,
                            'error': f'Failed to start process: {str(start_error)}'
                        })
                        return result_data
                    
                    result_data.update({
                        'message': f'Workflow started in background process (PID: {process.pid})',
                        'process_pid': process.pid
                    })
                    
                elif command == 'continue':
                    # Run orchestrator continue in separate process
                    import subprocess
                    cmd = [sys.executable, 'orchestrate.py', 'continue']
                    if mode == 'meta':
                        cmd.append('--meta')
                    
                    try:
                        process = subprocess.Popen(cmd, 
                                                   stdout=subprocess.PIPE, 
                                                   stderr=subprocess.PIPE,
                                                   cwd=os.getcwd(),
                                                   start_new_session=True)  # Prevent signal propagation
                    except Exception as continue_error:
                        OPERATION_STATE['current_operation'] = 'idle'
                        result_data.update({
                            'success': False,
                            'error': f'Failed to start continue process: {str(continue_error)}'
                        })
                        return result_data
                    
                    result_data.update({
                        'message': f'Continue workflow started in background process (PID: {process.pid})',
                        'process_pid': process.pid
                    })
                    
                elif command == 'status':
                    # Status can be handled directly as it's read-only
                    result_data.update({
                        'message': 'Status retrieved successfully',
                        'operation_state': OPERATION_STATE.copy()
                    })
                    
                elif command == 'clean':
                    # Run clean in separate process
                    import subprocess
                    cmd = [sys.executable, 'orchestrate.py', 'clean']
                    if mode == 'meta':
                        cmd.append('--meta')
                    
                    process = subprocess.run(cmd, 
                                           capture_output=True, 
                                           text=True,
                                           cwd=os.getcwd())
                    
                    if process.returncode == 0:
                        result_data.update({
                            'message': 'Outputs cleaned successfully'
                        })
                    else:
                        result_data.update({
                            'success': False,
                            'message': f'Clean failed: {process.stderr}'
                        })
                
                # Read updated status after command execution
                if self.status_reader:
                    workflow_state = get_workflow_status(project_root=self.project_root, mode=mode)
                    result_data['workflow_state'] = workflow_state
                
                return result_data
                
            except Exception as cmd_error:
                result_data.update({
                    'success': False,
                    'error': f'Command execution failed: {str(cmd_error)}'
                })
                return result_data
                
            finally:
                # Reset operation state after completion (except for status)
                if command != 'status':
                    OPERATION_STATE['current_operation'] = 'idle'
                    OPERATION_STATE['start_time'] = None
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Error executing command: {str(e)}'
            }
        
        finally:
            # Ensure operation state is reset on any error
            if command != 'status':
                OPERATION_STATE['current_operation'] = 'idle'
    
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
            # Find available port
            try:
                self.port = find_available_port(self.port)
            except OSError as e:
                print(f"Error finding available port: {e}")
                return False
                
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
            print(f"Command execution endpoint: http://{self.host}:{self.port}/api/execute")
            print(f"With meta mode: http://{self.host}:{self.port}/api/status?mode=meta")
            print("Press Ctrl+C to stop the server")
            
            # Set up signal handlers for graceful shutdown (only in main thread)
            if self.setup_signals:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Open dashboard in browser (unless disabled)
            if not getattr(self, 'no_browser', False):
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
                print(f"Command execution endpoint: http://{self.host}:{self.port}/api/execute")
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
    parser.add_argument('--no-browser', action='store_true', help='Do not automatically open browser')
    
    args = parser.parse_args()
    
    server = OrchestratorAPIServer(port=args.port, host=args.host)
    
    # Set browser preference
    server.no_browser = args.no_browser
    
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