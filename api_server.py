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


class StatusReader:
    """Reads and parses workflow status from orchestrator files"""
    
    def __init__(self):
        self.status_emoji_map = {
            '⏳': 'pending',
            '✅': 'completed', 
            '🔄': 'in-progress'
        }
        
    def read_status(self, mode='regular'):
        """Read workflow status from appropriate directory"""
        outputs_dir = '.agent-outputs-meta' if mode == 'meta' else '.agent-outputs'
        status_file = Path(outputs_dir) / 'current-status.md'
        
        try:
            if not status_file.exists():
                return self._get_default_status()
                
            with open(status_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return self._parse_status_content(content)
            
        except Exception as e:
            print(f"Error reading status file: {e}")
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
        self.status_reader = StatusReader()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/api/status':
            self._handle_status_request(parsed_url)
        else:
            self._send_error(404, 'Not Found')
    
    def _handle_status_request(self, parsed_url):
        """Handle /api/status endpoint"""
        try:
            # Parse query parameters
            query_params = parse_qs(parsed_url.query)
            mode = query_params.get('mode', ['regular'])[0]
            
            # Validate mode parameter
            if mode not in ['regular', 'meta']:
                self._send_error(400, 'Invalid mode parameter. Use "regular" or "meta".')
                return
            
            # Read status data
            status_data = self.status_reader.read_status(mode)
            
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
        self.send_header('Access-Control-Allow-Methods', 'GET')
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
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[{self.log_date_time_string()}] {format % args}")


class OrchestratorAPIServer:
    """Main API server class"""
    
    def __init__(self, port=8000, host='localhost'):
        self.port = port
        self.host = host
        self.server = None
        self.server_thread = None
        self._running = False
    
    def start(self):
        """Start the API server"""
        try:
            self.server = HTTPServer((self.host, self.port), StatusHandler)
            self._running = True
            
            print(f"Starting Claude Code Orchestrator API server on {self.host}:{self.port}")
            print(f"Status endpoint: http://{self.host}:{self.port}/api/status")
            print(f"With meta mode: http://{self.host}:{self.port}/api/status?mode=meta")
            print("Press Ctrl+C to stop the server")
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Start server
            self.server.serve_forever()
            
        except OSError as e:
            print(f"Error starting server: {e}")
            if "Address already in use" in str(e):
                print(f"Port {self.port} is already in use. Try a different port.")
            return False
        except KeyboardInterrupt:
            self.stop()
        
        return True
    
    def start_background(self):
        """Start server in background thread"""
        if self._running:
            print("Server is already running")
            return True
            
        self.server_thread = threading.Thread(target=self.start, daemon=True)
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