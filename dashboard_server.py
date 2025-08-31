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
import threading
import hashlib
import base64
import struct
from pathlib import Path
from datetime import datetime
from orchestrator_logger import OrchestratorLogger
from ptyprocess import PtyProcessUnicode


class WebSocketTerminalSession:
    """Manages a terminal session over WebSocket connection"""
    
    def __init__(self, connection):
        self.connection = connection
        self.pty_process = None
        self.output_thread = None
        self.running = False
        
    def start(self):
        """Start terminal session and PTY process"""
        try:
            # Spawn Claude CLI process
            self.pty_process = PtyProcessUnicode.spawn(['claude'])
            self.running = True
            
            # Start output thread for non-blocking I/O
            self.output_thread = threading.Thread(target=self._read_pty_output)
            self.output_thread.daemon = True
            self.output_thread.start()
            
        except Exception as e:
            error_msg = f"Failed to spawn Claude CLI process: {str(e)}"
            print(f"[Dashboard] {error_msg}")
            self._send_websocket_message(error_msg)
            raise
    
    def send_to_terminal(self, data):
        """Send data to the terminal process"""
        if self.pty_process and self.running:
            try:
                self.pty_process.write(data)
            except Exception as e:
                print(f"[Dashboard] Error writing to terminal: {e}")
    
    def _read_pty_output(self):
        """Read output from PTY process and send to WebSocket"""
        while self.running and self.pty_process:
            try:
                output = self.pty_process.read(timeout=0.1)
                if output:
                    self._send_websocket_message(output)
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    print(f"[Dashboard] Error reading PTY output: {e}")
                break
    
    def _send_websocket_message(self, message):
        """Send message to WebSocket client"""
        if self.connection:
            try:
                frame = self._create_websocket_frame(message)
                self.connection.send(frame)
            except Exception as e:
                print(f"[Dashboard] Error sending WebSocket message: {e}")
    
    def _create_websocket_frame(self, message):
        """Create outgoing WebSocket frame for text message"""
        message_bytes = message.encode('utf-8')
        length = len(message_bytes)
        
        frame = bytearray()
        frame.append(0x81)  # FIN=1, opcode=1 (text)
        
        if length <= 125:
            frame.append(length)
        elif length <= 65535:
            frame.append(126)
            frame.extend(struct.pack('>H', length))
        else:
            frame.append(127)
            frame.extend(struct.pack('>Q', length))
        
        frame.extend(message_bytes)
        return bytes(frame)
    
    def cleanup(self):
        """Clean up terminal session and PTY process"""
        self.running = False
        
        if self.pty_process:
            try:
                self.pty_process.terminate()
                self.pty_process = None
            except Exception as e:
                print(f"[Dashboard] Error terminating PTY process: {e}")
        
        if self.output_thread and self.output_thread.is_alive():
            try:
                self.output_thread.join(timeout=1.0)
            except Exception as e:
                print(f"[Dashboard] Error joining output thread: {e}")


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for serving dashboard files"""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from (project root)
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    
    def do_GET(self):
        """Handle GET requests with custom routing for dashboard"""
        try:
            # Check for WebSocket upgrade request
            if self._is_websocket_request():
                if self._websocket_handshake():
                    self._handle_websocket_connection()
                return
            
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
            elif self.path == '/emergency-restart':
                # Emergency restart endpoint - bypasses API server
                self._handle_emergency_restart()
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
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            if self.path == '/emergency-restart':
                self._handle_emergency_restart()
                return
            else:
                # Method not allowed for other POST paths
                self.send_response(405)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Method not allowed')
        except Exception as e:
            print(f"[Dashboard] Error handling POST request {self.path}: {e}")
    
    def _handle_emergency_restart(self):
        """Emergency restart endpoint - direct shell execution"""
        try:
            import subprocess
            import json
            import sys
            from pathlib import Path
            
            # Read request body for mode parameter
            content_length = int(self.headers.get('Content-Length', 0))
            mode = 'regular'  # Default mode
            
            if content_length > 0:
                request_body = self.rfile.read(content_length).decode('utf-8')
                try:
                    restart_data = json.loads(request_body)
                    mode = restart_data.get('mode', 'regular')
                except json.JSONDecodeError:
                    pass  # Use default mode
            
            print(f"[Dashboard] Emergency restart initiated in {mode} mode")
            
            # Step 1: Kill all orchestrator processes (most aggressive cleanup)
            try:
                subprocess.run(['pkill', '-9', '-f', 'orchestrate.py'], 
                             capture_output=True, timeout=5)
                print("[Dashboard] Killed orchestrator processes")
            except Exception as e:
                print(f"[Dashboard] Warning: Could not kill processes: {e}")
            
            # Step 2: Execute clear-ui command
            try:
                clear_result = subprocess.run([sys.executable, 'orchestrate.py', 'clear-ui'], 
                                            capture_output=True, text=True, timeout=20)
                if clear_result.returncode == 0:
                    print("[Dashboard] Clear-UI completed successfully")
                else:
                    print(f"[Dashboard] Clear-UI warning: {clear_result.stderr}")
            except Exception as e:
                print(f"[Dashboard] Clear-UI failed: {e}")
            
            # Step 3: Start new serve process (detached)
            try:
                serve_process = subprocess.Popen([sys.executable, 'orchestrate.py', 'serve'],
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL,
                                               start_new_session=True)
                print(f"[Dashboard] New serve process started (PID: {serve_process.pid})")
            except Exception as e:
                print(f"[Dashboard] Failed to start serve: {e}")
                raise e
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response_data = {
                'success': True,
                'message': 'Emergency restart completed',
                'mode': mode,
                'serve_pid': serve_process.pid if 'serve_process' in locals() else None
            }
            
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            print(f"[Dashboard] Emergency restart failed: {e}")
            
            # Send error response
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_data = {
                'success': False,
                'error': str(e)
            }
            
            self.wfile.write(json.dumps(error_data).encode())
    
    
    def log_message(self, format, *args):
        """Log requests with timestamp"""
        print(f"[{self.log_date_time_string()}] {format % args}")
    
    def _is_websocket_request(self):
        """Check if the request is a WebSocket upgrade request"""
        return (self.headers.get('Upgrade', '').lower() == 'websocket' and
                self.headers.get('Connection', '').lower() == 'upgrade' and
                'Sec-WebSocket-Key' in self.headers)
    
    def _websocket_handshake(self):
        """Perform WebSocket handshake according to RFC 6455"""
        try:
            websocket_key = self.headers.get('Sec-WebSocket-Key')
            if not websocket_key:
                return False
            
            # Calculate Sec-WebSocket-Accept
            magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept_key = base64.b64encode(
                hashlib.sha1((websocket_key + magic_string).encode()).digest()
            ).decode()
            
            # Send upgrade response
            self.send_response(101, 'Switching Protocols')
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', accept_key)
            self.end_headers()
            
            return True
        except Exception as e:
            print(f"[Dashboard] WebSocket handshake failed: {e}")
            return False
    
    def _parse_websocket_frame(self, data):
        """Parse incoming WebSocket frame according to RFC 6455"""
        if len(data) < 2:
            return None
        
        byte1 = data[0]
        byte2 = data[1]
        
        fin = (byte1 >> 7) & 1
        opcode = byte1 & 0x0f
        masked = (byte2 >> 7) & 1
        payload_length = byte2 & 0x7f
        
        if opcode == 8:  # Close frame
            return {'type': 'close'}
        
        if opcode != 1:  # Only handle text frames
            return None
        
        offset = 2
        if payload_length == 126:
            payload_length = struct.unpack('>H', data[offset:offset+2])[0]
            offset += 2
        elif payload_length == 127:
            payload_length = struct.unpack('>Q', data[offset:offset+8])[0]
            offset += 8
        
        if masked:
            mask = data[offset:offset+4]
            offset += 4
            payload = bytearray(data[offset:offset+payload_length])
            for i in range(payload_length):
                payload[i] ^= mask[i % 4]
        else:
            payload = data[offset:offset+payload_length]
        
        try:
            message = payload.decode('utf-8')
            return {'type': 'message', 'data': message}
        except UnicodeDecodeError:
            return None
    
    def _handle_websocket_connection(self):
        """Handle WebSocket connection with terminal session"""
        terminal_session = None
        try:
            # Create terminal session
            terminal_session = WebSocketTerminalSession(self.connection)
            terminal_session.start()
            
            # Handle incoming messages
            while True:
                try:
                    data = self.connection.recv(4096)
                    if not data:
                        break
                    
                    frame = self._parse_websocket_frame(data)
                    if not frame:
                        continue
                    
                    if frame['type'] == 'close':
                        break
                    elif frame['type'] == 'message':
                        terminal_session.send_to_terminal(frame['data'])
                        
                except ConnectionResetError:
                    break
                except Exception as e:
                    print(f"[Dashboard] WebSocket message handling error: {e}")
                    break
                    
        except Exception as e:
            print(f"[Dashboard] WebSocket connection error: {e}")
        finally:
            if terminal_session:
                terminal_session.cleanup()


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