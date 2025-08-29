#!/usr/bin/env python3
"""
Real-time log streaming for Claude Orchestrator CLI
Shows only new log entries from current agent execution
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional


class LogStreamer:
    """Streams new lines from agent log files in real-time"""
    
    def __init__(self, log_file_path: Path, agent_name: str):
        self.log_file_path = log_file_path
        self.agent_name = agent_name
        self.initial_line_count = 0
        self.streaming_thread = None
        self.stop_streaming = False
        self.is_active = False
    
    def _get_file_line_count(self) -> int:
        """Get current number of lines in the log file"""
        if not self.log_file_path.exists():
            return 0
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception as e:
            print(f"[LogStreamer] Error counting lines in {self.log_file_path}: {e}")
            return 0
    
    def _read_lines_from_position(self, start_line: int) -> list:
        """Read lines from the file starting at specified line number (1-indexed)"""
        if not self.log_file_path.exists():
            return []
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if start_line <= len(lines):
                    return lines[start_line:]  # Convert to 0-indexed
                return []
        except Exception as e:
            print(f"[LogStreamer] Error reading from {self.log_file_path}: {e}")
            return []
    
    def _format_log_line(self, line: str) -> str:
        """Format log line for terminal display - show all content as-is"""
        line = line.rstrip('\n')
        
        # Skip only empty lines
        if not line.strip():
            return None
        
        return line
    
    def _streaming_loop(self):
        """Main streaming loop that runs in background thread"""
        current_line_count = self.initial_line_count
        poll_interval = 0.1  # 100ms polling
        
        while not self.stop_streaming:
            try:
                new_lines = self._read_lines_from_position(current_line_count)
                
                if new_lines:
                    for line in new_lines:
                        formatted_line = self._format_log_line(line)
                        if formatted_line:
                            print(f"  {formatted_line}")
                    
                    current_line_count += len(new_lines)
                
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"[LogStreamer] Streaming error: {e}")
                time.sleep(poll_interval)
    
    def start_streaming(self):
        """Start streaming new log entries"""
        if self.is_active:
            return
        
        # Capture baseline line count
        self.initial_line_count = self._get_file_line_count()
        
        # Start streaming thread
        self.stop_streaming = False
        self.streaming_thread = threading.Thread(
            target=self._streaming_loop, 
            daemon=True,
            name=f"LogStreamer-{self.agent_name}"
        )
        self.streaming_thread.start()
        self.is_active = True
    
    def stop_streaming_now(self):
        """Stop streaming immediately"""
        if not self.is_active:
            return
        
        self.stop_streaming = True
        if self.streaming_thread and self.streaming_thread.is_alive():
            self.streaming_thread.join(timeout=1.0)  # Wait up to 1 second
        
        self.is_active = False


def should_stream_logs() -> bool:
    """Check if log streaming should be enabled"""
    # Default: enabled (True)
    # Disable with CLAUDE_ORCHESTRATOR_STREAM_LOGS=false
    env_value = os.getenv('CLAUDE_ORCHESTRATOR_STREAM_LOGS', 'true').lower()
    return env_value not in ('false', '0', 'no', 'off', 'disabled')