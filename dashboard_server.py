#!/usr/bin/env python3
"""
Dashboard Server for Claude Orchestrator

Serves static files from the orchestrator directory on port 5678 with
port conflict handling. Integrates with ProcessManager for lifecycle management.
"""

import http.server
import socketserver
import os
import sys
import json
import socket
import time
from pathlib import Path
from datetime import datetime


class OrchestratorLogger:
    """Unified logging system for all orchestrator components"""
    
    def __init__(self, component_name: str, log_dir: Path = None):
        self.component_name = component_name
        self.log_dir = log_dir or Path.cwd()
        self.log_file = self.log_dir / f"{component_name}.log"
        
        # Ensure log directory exists
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize log file with startup message
        self._write_log(f"=== {component_name.upper()} STARTED ===")
    
    def _write_log(self, message: str, level: str = "INFO"):
        """Write message to log file with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            # Fallback to stderr if log file writing fails
            print(f"Log write failed: {e}", file=sys.stderr)
    
    def info(self, message: str):
        """Log info message"""
        self._write_log(message, "INFO")
        print(f"[{self.component_name}] {message}")
    
    def error(self, message: str):
        """Log error message"""
        self._write_log(message, "ERROR")
        print(f"[{self.component_name}] ERROR: {message}", file=sys.stderr)
    
    def warning(self, message: str):
        """Log warning message"""
        self._write_log(message, "WARNING")
        print(f"[{self.component_name}] WARNING: {message}")
    
    def debug(self, message: str):
        """Log debug message"""
        self._write_log(message, "DEBUG")
        print(f"[{self.component_name}] DEBUG: {message}")
    
    def shutdown(self):
        """Log shutdown message"""
        self._write_log(f"=== {self.component_name.upper()} SHUTDOWN ===")


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for serving dashboard files"""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from (project root)
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    
    def do_GET(self):
        """Handle GET requests with custom routing for dashboard"""
        try:
            if self.path == '/health':
                # Health check endpoint
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                health_data = {
                    'status': 'healthy',
                    'service': 'dashboard',
                    'timestamp': time.time()
                }
                self.wfile.write(json.dumps(health_data).encode())
                return
            elif self.path.endswith('.log'):
                # Serve log files from project root
                log_filename = self.path[1:]  # Remove leading slash
                log_file_path = Path.cwd() / log_filename
                
                if log_file_path.exists() and log_file_path.is_file():
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.wfile.write(content.encode('utf-8'))
                    return
                else:
                    # Log file not found
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f'Log file not found: {log_filename}'.encode())
                    return
            elif self.path == '/dashboard/index.html' or self.path == '/dashboard/':
                # Serve dashboard.html when dashboard path is requested
                self.path = '/dashboard.html'
            elif self.path == '/':
                # Redirect root to dashboard
                self.send_response(302)
                self.send_header('Location', '/dashboard.html')
                self.end_headers()
                return
            
            # Let the parent handler serve the file
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            # Client closed connection while we were sending data - ignore this
            pass
        except Exception as e:
            # Log other errors but don't crash
            print(f"[Dashboard] Error handling request {self.path}: {e}")
    
    
    def log_message(self, format, *args):
        """Log requests with timestamp"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def find_available_port(start_port, max_attempts=20):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    # If no ports in requested range, try fallback range
    if start_port == 5678:
        for port in range(6000, 6020):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('localhost', port))
                    return port
            except OSError:
                continue
    
    raise OSError(f"No available ports found starting from {start_port}")


def start_dashboard_server(port=5678, host='localhost'):
    """Start the dashboard server on specified port"""
    
    # Initialize logger
    dashboard_logger = OrchestratorLogger("dashboard-server")
    
    # Check if dashboard.html exists
    dashboard_file = Path(__file__).parent / 'dashboard.html'
    if not dashboard_file.exists():
        dashboard_logger.warning(f"dashboard.html not found at {dashboard_file}")
        dashboard_logger.info("Dashboard will serve other files from the project root")
    
    try:
        # Allow socket reuse to prevent "Address already in use" errors
        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
        
        with ReusableTCPServer((host, port), DashboardHandler) as httpd:
            dashboard_logger.info(f"Dashboard server started on {host}:{port}")
            dashboard_logger.info(f"Dashboard server registered (PID: {os.getpid()})")
            dashboard_logger.info(f"Dashboard available at: http://{host}:{port}")
            if dashboard_file.exists():
                dashboard_logger.info(f"Dashboard UI at: http://{host}:{port}/dashboard.html")
            dashboard_logger.info(f"Health check at: http://{host}:{port}/health")
            
            # Start serving
            httpd.serve_forever()
            
    except OSError as e:
        if "Address already in use" in str(e):
            dashboard_logger.error(f"Port {port} is already in use")
            return False
        else:
            dashboard_logger.error(f"Error starting server: {e}")
            return False
    except KeyboardInterrupt:
        dashboard_logger.info("Dashboard server stopped")
        dashboard_logger.shutdown()
        return True


def main():
    """Main entry point for the dashboard server"""
    
    # Parse command line arguments
    port = 5678
    host = 'localhost'
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Usage: python test_dashboard_server.py [port]")
            print("Example: python test_dashboard_server.py 5678")
            sys.exit(1)
    
    # Start the server
    success = start_dashboard_server(port, host)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()