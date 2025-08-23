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
    
    # Check if dashboard.html exists
    dashboard_file = Path(__file__).parent / 'dashboard.html'
    if not dashboard_file.exists():
        print(f"Warning: dashboard.html not found at {dashboard_file}")
        print("Dashboard will serve other files from the project root")
    
    try:
        # Allow socket reuse to prevent "Address already in use" errors
        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
        
        with ReusableTCPServer((host, port), DashboardHandler) as httpd:
            print(f"Dashboard server started on {host}:{port}")
            print(f"Dashboard server registered (PID: {os.getpid()})")
            print(f"Dashboard available at: http://{host}:{port}")
            if dashboard_file.exists():
                print(f"Dashboard UI at: http://{host}:{port}/dashboard.html")
            print(f"Health check at: http://{host}:{port}/health")
            
            # Start serving
            httpd.serve_forever()
            
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {port} is already in use")
            return False
        else:
            print(f"Error starting server: {e}")
            return False
    except KeyboardInterrupt:
        print("\nDashboard server stopped")
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