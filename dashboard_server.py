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
from process_manager import ProcessManager

# Global ProcessManager instance for terminal process tracking
_process_manager = None

def get_process_manager():
    """Get or create the ProcessManager instance"""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager(meta_mode='meta' in sys.argv)
    return _process_manager


class WebSocketTerminalSession:
    """Manages a terminal session over WebSocket connection"""
    
    def __init__(self, connection, process_manager=None):
        self.connection = connection
        self.pty_process = None
        self.output_thread = None
        self.running = False
        self.process_manager = process_manager or get_process_manager()
        self.process_name = None
        self.terminal_logger = OrchestratorLogger("terminal-handler")
        
    def start(self):
        """Start terminal session and PTY process"""
        self.terminal_logger.info("Starting terminal session")
        
        try:
            # Log environment context before spawn attempt
            env_context = {
                'working_directory': os.getcwd(),
                'path_env': os.environ.get('PATH', 'Not set'),
                'claude_cli_command': 'claude'
            }
            
            self.terminal_logger.debug(f"PTY spawn environment context: {env_context}")
            
            # Spawn Claude CLI process
            self.pty_process = PtyProcessUnicode.spawn(['claude'])
            self.running = True
            
            # Register terminal process with ProcessManager
            terminal_id = f"terminal-{id(self)}"
            self.process_name = terminal_id
            self.process_manager.register_process(terminal_id, self.pty_process)
            
            self.terminal_logger.info(f"Terminal process {terminal_id} spawned and registered with ProcessManager")
            
            # Start output thread for non-blocking I/O
            self.output_thread = threading.Thread(target=self._read_pty_output)
            self.output_thread.daemon = True
            self.output_thread.start()
            
            self.terminal_logger.info("Terminal session started successfully")
            
        except Exception as e:
            # Log detailed PTY spawn error with environment context
            error_context = {
                'command': ['claude'],
                'working_directory': os.getcwd(),
                'path_env': os.environ.get('PATH', 'Not set'),
                'user_env': os.environ.get('USER', 'Not set'),
                'shell_env': os.environ.get('SHELL', 'Not set'),
                'error': str(e),
                'error_type': type(e).__name__
            }
            
            self.terminal_logger.error(f"PTY process spawn failed: {error_context}")
            
            # Send fallback message to client with error context
            client_error_msg = f"Terminal connection failed: {str(e)}. Please check Claude CLI installation."
            self.terminal_logger.warning(f"Sending fallback error message to client: {client_error_msg}")
            
            try:
                self._send_websocket_message(client_error_msg)
            except Exception as ws_error:
                self.terminal_logger.error(f"Failed to send fallback message to client: {ws_error}")
            
            raise
    
    def send_to_terminal(self, data):
        """Send data to the terminal process"""
        if self.pty_process and self.running:
            try:
                self.pty_process.write(data)
                self.terminal_logger.debug(f"Sent {len(data)} bytes to terminal process")
            except Exception as e:
                self.terminal_logger.error(f"Error writing to terminal: {e}")
                
                # Send fallback message to client about communication failure
                try:
                    fallback_msg = f"Terminal communication error: {str(e)}. Connection may be unstable."
                    self.terminal_logger.warning(f"Sending communication error fallback to client: {fallback_msg}")
                    self._send_websocket_message(fallback_msg)
                except Exception as ws_error:
                    self.terminal_logger.error(f"Failed to send communication error fallback to client: {ws_error}")
        else:
            self.terminal_logger.warning("Cannot send to terminal: process not running or not available")
    
    def _read_pty_output(self):
        """Read output from PTY process and send to WebSocket"""
        timeout_count = 0
        max_timeouts = 5  # Allow 5 consecutive timeouts before considering reconnection
        
        self.terminal_logger.debug("Starting PTY output reading thread")
        
        while self.running and self.pty_process:
            try:
                output = self.pty_process.read(timeout=0.1)
                if output:
                    timeout_count = 0  # Reset timeout counter on successful read
                    self._send_websocket_message(output)
                    self.terminal_logger.debug(f"Read and sent {len(output)} bytes from PTY")
                
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    timeout_count += 1
                    
                    if timeout_count <= max_timeouts:
                        self.terminal_logger.warning(f"PTY read timeout ({timeout_count}/{max_timeouts}): {e}")
                        
                        # Brief pause before retry
                        time.sleep(0.1)
                        continue
                    else:
                        self.terminal_logger.error(f"PTY communication failed after {max_timeouts} consecutive timeouts: {e}")
                        
                        # Send reconnection fallback message to client
                        try:
                            fallback_msg = f"Terminal connection lost after multiple timeouts. Please refresh to reconnect."
                            self.terminal_logger.warning(f"Sending reconnection fallback to client: {fallback_msg}")
                            self._send_websocket_message(fallback_msg)
                        except Exception as ws_error:
                            self.terminal_logger.error(f"Failed to send reconnection fallback to client: {ws_error}")
                
                break
        
        self.terminal_logger.debug("PTY output reading thread stopped")
    
    def _send_websocket_message(self, message):
        """Send message to WebSocket client"""
        if self.connection:
            try:
                frame = self._create_websocket_frame(message)
                self.connection.send(frame)
                self.terminal_logger.debug(f"Sent WebSocket message ({len(message)} chars)")
            except Exception as e:
                self.terminal_logger.error(f"WebSocket send error: {e}")
                
                # Check if this is a connection failure that should trigger cleanup
                if any(error_type in str(e).lower() for error_type in ['broken pipe', 'connection reset', 'connection aborted']):
                    self.terminal_logger.warning("WebSocket connection appears broken, triggering cleanup")
                    
                    # Integrate with ProcessManager health monitoring
                    if self.process_name and self.process_manager:
                        try:
                            is_healthy = self.process_manager.is_process_healthy(self.process_name)
                            self.terminal_logger.info(f"Terminal process {self.process_name} health status: {'healthy' if is_healthy else 'unhealthy'}")
                            
                            if not is_healthy:
                                self.terminal_logger.warning(f"Unhealthy terminal process detected, initiating cleanup for {self.process_name}")
                                self.running = False
                        except Exception as health_error:
                            self.terminal_logger.error(f"Error checking process health during WebSocket failure: {health_error}")
        else:
            self.terminal_logger.warning("Cannot send WebSocket message: connection not available")
    
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
        self.terminal_logger.info("Starting terminal session cleanup")
        self.running = False
        
        # Check process health before termination attempt
        process_healthy = False
        if self.process_name and self.process_manager:
            try:
                process_healthy = self.process_manager.is_process_healthy(self.process_name)
                if process_healthy:
                    self.terminal_logger.info(f"Terminal process {self.process_name} is healthy, proceeding with termination")
                else:
                    self.terminal_logger.warning(f"Terminal process {self.process_name} is not healthy, will deregister")
            except Exception as e:
                self.terminal_logger.error(f"Error checking process health: {e}")
        
        if self.pty_process and process_healthy:
            try:
                # Follow ProcessManager.terminate_process() pattern: terminate() → wait(timeout) → force kill if needed
                self.pty_process.terminate()
                self.terminal_logger.info(f"Sent SIGTERM to PTY process for {self.process_name}")
                
                # Wait for process termination with timeout
                try:
                    # Use timeout=5 similar to ProcessManager.terminate_process default
                    exit_code = self.pty_process.wait(timeout=5)
                    self.terminal_logger.info(f"PTY process for {self.process_name} terminated gracefully with exit code {exit_code}")
                except Exception as wait_error:
                    # Force kill if graceful termination fails
                    self.terminal_logger.warning(f"PTY process termination timeout, attempting force kill: {wait_error}")
                    try:
                        self.pty_process.kill()
                        # Wait briefly for force kill to complete
                        exit_code = self.pty_process.wait(timeout=2)
                        self.terminal_logger.info(f"PTY process for {self.process_name} force-killed with exit code {exit_code}")
                    except Exception as kill_error:
                        self.terminal_logger.error(f"Error force-killing PTY process: {kill_error}")
                
                self.pty_process = None
            except Exception as e:
                self.terminal_logger.error(f"Error terminating PTY process: {e}")
                self.pty_process = None
        elif self.pty_process:
            # Process is not healthy, just clean up the reference
            self.terminal_logger.warning(f"PTY process for {self.process_name} was not healthy, cleaning up reference")
            self.pty_process = None
        
        # Deregister process from ProcessManager ONLY after successful process termination
        if self.process_name and self.process_manager:
            try:
                self.process_manager.deregister_process(self.process_name)
                self.terminal_logger.info(f"Deregistered terminal process {self.process_name} from ProcessManager")
            except Exception as e:
                self.terminal_logger.error(f"Error deregistering terminal process: {e}")
        
        # Clean up output thread
        if self.output_thread and self.output_thread.is_alive():
            try:
                self.output_thread.join(timeout=1.0)
                self.terminal_logger.debug("Output thread joined successfully")
            except Exception as e:
                self.terminal_logger.error(f"Error joining output thread: {e}")
        
        self.terminal_logger.info("Terminal session cleanup completed")


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for serving dashboard files"""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from (project root)
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
        try:
            self.request_logger = OrchestratorLogger("dashboard-requests")
        except Exception as e:
            # Fallback if OrchestratorLogger fails to initialize
            print(f"[WARNING] Failed to initialize request_logger: {e}")
            self.request_logger = None
    
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
            # Log other errors but don't crash - defensive check for request_logger
            if hasattr(self, 'request_logger'):
                self.request_logger.error(f"Error handling request {self.path}: {e}")
            else:
                # Fallback logging if request_logger is not available
                print(f"[ERROR] Dashboard handler error for {self.path}: {e}")
                import traceback
                traceback.print_exc()
    
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
            # Defensive check for request_logger
            if hasattr(self, 'request_logger'):
                self.request_logger.error(f"Error handling POST request {self.path}: {e}")
            else:
                # Fallback logging if request_logger is not available
                print(f"[ERROR] Dashboard handler POST error for {self.path}: {e}")
                import traceback
                traceback.print_exc()
    
    def _handle_emergency_restart(self):
        """Emergency restart endpoint - direct shell execution"""
        # Helper function for safe logging
        def safe_log(level, message):
            if hasattr(self, 'request_logger'):
                getattr(self.request_logger, level)(message)
            else:
                print(f"[{level.upper()}] {message}")
        
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
            
            safe_log('info', f"Emergency restart initiated in {mode} mode")
            
            # Step 1: Kill all orchestrator processes (most aggressive cleanup)
            try:
                subprocess.run(['pkill', '-9', '-f', 'orchestrate.py'], 
                             capture_output=True, timeout=5)
                safe_log('info', "Killed orchestrator processes")
            except Exception as e:
                safe_log('warning', f"Could not kill processes: {e}")
            
            # Step 2: Execute clear-ui command
            try:
                clear_result = subprocess.run([sys.executable, 'orchestrate.py', 'clear-ui'], 
                                            capture_output=True, text=True, timeout=20)
                if clear_result.returncode == 0:
                    safe_log('info', "Clear-UI completed successfully")
                else:
                    safe_log('warning', f"Clear-UI warning: {clear_result.stderr}")
            except Exception as e:
                safe_log('error', f"Clear-UI failed: {e}")
            
            # Step 3: Start new serve process (detached)
            try:
                serve_process = subprocess.Popen([sys.executable, 'orchestrate.py', 'serve'],
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL,
                                               start_new_session=True)
                safe_log('info', f"New serve process started (PID: {serve_process.pid})")
            except Exception as e:
                safe_log('error', f"Failed to start serve: {e}")
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
            safe_log('error', f"Emergency restart failed: {e}")
            
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
        # Defensive check for request_logger
        if hasattr(self, 'request_logger'):
            self.request_logger.debug(f"[{self.log_date_time_string()}] {format % args}")
        else:
            # Fallback to standard logging if request_logger is not available
            print(f"[{self.log_date_time_string()}] {format % args}")
    
    def _is_websocket_request(self):
        """Check if the request is a WebSocket upgrade request"""
        return (self.headers.get('Upgrade', '').lower() == 'websocket' and
                self.headers.get('Connection', '').lower() == 'upgrade' and
                'Sec-WebSocket-Key' in self.headers)
    
    def _websocket_handshake(self):
        """Perform WebSocket handshake according to RFC 6455"""
        # Helper function for safe logging  
        def safe_log(level, message):
            if hasattr(self, 'request_logger') and self.request_logger:
                getattr(self.request_logger, level)(message)
            else:
                print(f"[{level.upper()}] WebSocket handshake: {message}")
        
        try:
            websocket_key = self.headers.get('Sec-WebSocket-Key')
            if not websocket_key:
                safe_log('warning', "WebSocket handshake missing Sec-WebSocket-Key header")
                return False
            
            safe_log('debug', "Starting WebSocket handshake")
            
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
            
            safe_log('info', "WebSocket handshake completed successfully")
            return True
        except Exception as e:
            safe_log('error', f"WebSocket handshake failed: {e}")
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
        # Create logger for WebSocket handling
        websocket_logger = OrchestratorLogger("websocket-handler")
        websocket_logger.info("WebSocket connection established")
        
        terminal_session = None
        try:
            # Create terminal session with ProcessManager integration
            process_manager = get_process_manager()
            terminal_session = WebSocketTerminalSession(self.connection, process_manager)
            terminal_session.start()
            
            websocket_logger.info("Terminal session created and started")
            
            # Handle incoming messages with timeout and reconnection logic
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            while True:
                try:
                    data = self.connection.recv(4096)
                    if not data:
                        websocket_logger.info("WebSocket connection closed by client")
                        break
                    
                    frame = self._parse_websocket_frame(data)
                    if not frame:
                        websocket_logger.debug("Received invalid WebSocket frame, ignoring")
                        continue
                    
                    if frame['type'] == 'close':
                        websocket_logger.info("Received WebSocket close frame")
                        break
                    elif frame['type'] == 'message':
                        terminal_session.send_to_terminal(frame['data'])
                        consecutive_errors = 0  # Reset error counter on successful message
                        
                except ConnectionResetError:
                    websocket_logger.warning("WebSocket connection reset by client")
                    break
                except Exception as e:
                    consecutive_errors += 1
                    websocket_logger.error(f"WebSocket message handling error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        websocket_logger.error(f"Too many consecutive errors ({consecutive_errors}), closing connection")
                        
                        # Send final error message to client if possible
                        try:
                            if terminal_session:
                                terminal_session._send_websocket_message("Connection terminated due to repeated errors. Please refresh to reconnect.")
                        except:
                            pass  # Best effort only
                        break
                    
                    # Brief pause before continuing
                    time.sleep(0.1)
                    
        except Exception as e:
            websocket_logger.error(f"WebSocket connection error: {e}")
            
            # Integrate with ProcessManager health monitoring for connection failures
            if terminal_session and terminal_session.process_name:
                try:
                    process_manager = get_process_manager()
                    is_healthy = process_manager.is_process_healthy(terminal_session.process_name)
                    websocket_logger.info(f"Terminal process health during connection error: {'healthy' if is_healthy else 'unhealthy'}")
                except Exception as health_error:
                    websocket_logger.error(f"Error checking process health during connection failure: {health_error}")
                    
        finally:
            websocket_logger.info("Cleaning up WebSocket connection")
            if terminal_session:
                terminal_session.cleanup()
            websocket_logger.info("WebSocket connection cleanup completed")


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
    
    # Initialize ProcessManager for terminal process tracking
    process_manager = get_process_manager()
    
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
        # Clean up any registered terminal processes
        try:
            process_manager.cleanup_all_processes()
        except Exception as e:
            dashboard_logger.error(f"Error cleaning up terminal processes: {e}")
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
            main_logger = OrchestratorLogger("dashboard-main")
            main_logger.error("Invalid port argument provided")
            main_logger.info("Usage: python dashboard_server.py [port]")
            main_logger.info("Example: python dashboard_server.py 5678")
            sys.exit(1)
    
    # Start the server
    success = start_dashboard_server(port, host)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()