#!/usr/bin/env python3
"""
Shared logging system for Claude Orchestrator components
Extracted from duplicate implementations to eliminate code duplication
"""

import sys
from datetime import datetime
from pathlib import Path


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