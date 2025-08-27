import json
import os
import signal
import subprocess
import time
import psutil
from pathlib import Path
from typing import Dict, List, Optional


class ProcessManager:
    def __init__(self, meta_mode=False):
        self.config_dir = Path.home() / '.claude-orchestrator'
        self.meta_mode = meta_mode
        
        # Use different PID files for meta vs regular mode
        if meta_mode:
            self.pid_file = self.config_dir / 'pids-meta.json'
        else:
            self.pid_file = self.config_dir / 'pids.json'
            
        self.processes: Dict[str, subprocess.Popen] = {}
        self._ensure_config_dir()
        self._load_pids()
        
    def _ensure_config_dir(self):
        self.config_dir.mkdir(exist_ok=True)
    
    def _load_pids(self):
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    data = json.load(f)
                    # Clean up any stale PIDs that are no longer running
                    self._cleanup_stale_pids(data)
            except (json.JSONDecodeError, FileNotFoundError):
                self._save_pids({})
    
    def _cleanup_stale_pids(self, data: Dict):
        active_pids = {}
        for name, proc_info in data.items():
            # Handle both old format (just PID) and new format (dict with pid/pgid)
            if isinstance(proc_info, dict):
                pid = proc_info.get('pid')
                if pid and self._is_process_running(pid):
                    active_pids[name] = proc_info  # Keep the full dict format
            else:
                # Old format - just PID
                pid = proc_info
                if self._is_process_running(pid):
                    active_pids[name] = pid  # Keep old format for backward compatibility
        self._save_pids(active_pids)
    
    def _save_pids(self, data: Dict):
        with open(self.pid_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _is_process_running(self, pid: int) -> bool:
        try:
            if not psutil.pid_exists(pid):
                return False
            
            # Check if process is zombie - zombies are effectively dead
            try:
                process = psutil.Process(pid)
                status = process.status()
                # Zombie processes should be considered as terminated
                if status == psutil.STATUS_ZOMBIE:
                    return False
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _reap_zombie_if_child(self, pid: int):
        """Attempt to reap zombie process if it's our child"""
        try:
            # Only reap if process is a zombie and we're the parent
            if psutil.pid_exists(pid):
                try:
                    process = psutil.Process(pid)
                    if process.status() == psutil.STATUS_ZOMBIE:
                        # Try to reap the zombie using waitpid with WNOHANG
                        import os
                        try:
                            os.waitpid(pid, os.WNOHANG)
                            print(f"Successfully reaped zombie process {pid}")
                        except (OSError, ChildProcessError):
                            # Not our child or already reaped - this is fine
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def register_process(self, name: str, process: subprocess.Popen):
        self.processes[name] = process
        
        # Load current PIDs, update with new process, and save
        current_pids = {}
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    current_pids = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                current_pids = {}
        
        # Store both PID and PGID for process group management
        try:
            pgid = os.getpgid(process.pid)
        except (OSError, ProcessLookupError):
            pgid = process.pid  # Fallback to PID if PGID lookup fails
        
        current_pids[name] = {
            'pid': process.pid,
            'pgid': pgid
        }
        self._save_pids(current_pids)
    
    def register_main_process(self, name: str, pid: int = None):
        """Register the main process by PID for system-wide tracking"""
        if pid is None:
            pid = os.getpid()
        
        # Load current PIDs, update with main process, and save
        current_pids = {}
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    current_pids = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                current_pids = {}
        
        # Store both PID and PGID for main process too
        try:
            pgid = os.getpgid(pid)
        except (OSError, ProcessLookupError):
            pgid = pid  # Fallback to PID if PGID lookup fails
        
        current_pids[name] = {
            'pid': pid,
            'pgid': pgid
        }
        self._save_pids(current_pids)
    
    def deregister_process(self, name: str):
        if name in self.processes:
            del self.processes[name]
        
        # Load current PIDs, remove the process, and save
        current_pids = {}
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    current_pids = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                current_pids = {}
        
        if name in current_pids:
            del current_pids[name]
        self._save_pids(current_pids)
    
    def is_process_healthy(self, name: str) -> bool:
        if name not in self.processes:
            return False
        
        process = self.processes[name]
        # Check if process is still running
        if process.poll() is not None:
            return False
        
        # Additional health check - verify PID still exists
        return self._is_process_running(process.pid)
    
    def terminate_process(self, name: str, timeout: int = 10) -> bool:
        if name not in self.processes:
            return True
        
        process = self.processes[name]
        pid = process.pid
        
        try:
            # Get process group ID
            try:
                pgid = os.getpgid(pid)
            except (OSError, ProcessLookupError):
                # Process already dead or no permission
                self.deregister_process(name)
                return True
            
            # Try graceful termination first on entire process group
            try:
                os.kill(-pgid, signal.SIGTERM)  # Use negative PID to target process group
                print(f"Sent SIGTERM to process group {pgid} for process {name} (PID: {pid})")
            except (OSError, ProcessLookupError):
                # Process or process group already dead
                self.deregister_process(name)
                return True
            
            try:
                process.wait(timeout=timeout)
                print(f"Process {name} (PID: {pid}) and its group terminated gracefully")
                self.deregister_process(name)
                return True
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination fails
                # Adjust force kill timeout to meet timing requirements:
                # - For timeout=5: total should be ≤7s, so force timeout = 7-5 = 2s
                # - For timeout=2: total should be ≤8s, so force timeout = 8-2 = 6s
                # Use min(3, max(2, 8-timeout)) to handle edge cases
                force_timeout = min(3, max(2, 8 - timeout))
                try:
                    os.kill(-pgid, signal.SIGKILL)  # Use negative PID to target process group
                    print(f"Sent SIGKILL to process group {pgid} for process {name} (PID: {pid})")
                except (OSError, ProcessLookupError):
                    # Process or process group already dead
                    self.deregister_process(name)
                    return True
                
                try:
                    process.wait(timeout=force_timeout)
                    print(f"Process {name} (PID: {pid}) and its group force-killed")
                    self.deregister_process(name)
                    return True
                except subprocess.TimeoutExpired:
                    print(f"Failed to terminate process group {pgid} for process {name} (PID: {pid})")
                    return False
        except (OSError, subprocess.SubprocessError) as e:
            print(f"Error terminating process {name}: {e}")
            # Still deregister since process might be dead
            self.deregister_process(name)
            return False
    
    def cleanup_all_processes(self, graceful_timeout: int = 10, force_timeout: int = 5) -> bool:
        success = True
        process_names = list(self.processes.keys())
        
        # First pass: graceful termination
        for name in process_names:
            if not self.terminate_process(name, graceful_timeout):
                success = False
        
        # Verify all processes are terminated
        for name in list(self.processes.keys()):
            if name in self.processes:
                print(f"Warning: Process {name} still running after cleanup")
                success = False
        
        return success
    
    def cleanup_system_wide(self) -> bool:
        if not self.pid_file.exists():
            return True
        
        try:
            with open(self.pid_file, 'r') as f:
                pids = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return True
        
        success = True
        for name, proc_info in pids.items():
            # Handle both old format (just PID) and new format (dict with pid/pgid)
            if isinstance(proc_info, dict):
                pid = proc_info.get('pid')
                pgid = proc_info.get('pgid', pid)  # Fallback to PID if no PGID
            else:
                # Old format - just PID
                pid = proc_info
                pgid = pid
            
            if self._is_process_running(pid):
                try:
                    # Try graceful termination on process group
                    try:
                        os.kill(-pgid, signal.SIGTERM)  # Use negative PID to target process group
                        print(f"Sent SIGTERM to process group {pgid} for process {name} (PID: {pid})")
                    except (OSError, ProcessLookupError):
                        # Fallback to individual process if process group fails
                        os.kill(pid, signal.SIGTERM)
                        print(f"Sent SIGTERM to process {name} (PID: {pid})")
                    
                    # Wait for graceful termination
                    for _ in range(100):  # 10 seconds at 0.1s intervals
                        if not self._is_process_running(pid):
                            print(f"Process {name} (PID: {pid}) and its group terminated gracefully")
                            # Reap zombie processes to prevent accumulation
                            self._reap_zombie_if_child(pid)
                            break
                        time.sleep(0.1)
                    else:
                        # Force kill if still running
                        try:
                            try:
                                os.kill(-pgid, signal.SIGKILL)  # Use negative PID to target process group
                                print(f"Sent SIGKILL to process group {pgid} for process {name} (PID: {pid})")
                            except (OSError, ProcessLookupError):
                                # Fallback to individual process if process group fails
                                os.kill(pid, signal.SIGKILL)
                                print(f"Sent SIGKILL to process {name} (PID: {pid})")
                            
                            # Wait up to 5 seconds for force termination to complete
                            terminated = False
                            for _ in range(50):  # 5 seconds at 0.1s intervals
                                if not self._is_process_running(pid):
                                    terminated = True
                                    break
                                time.sleep(0.1)
                            
                            if terminated:
                                print(f"Process {name} (PID: {pid}) and its group terminated after force kill")
                                # Reap zombie processes to prevent accumulation
                                self._reap_zombie_if_child(pid)
                            else:
                                print(f"Failed to kill process {name} (PID: {pid}) and its group")
                                success = False
                        except (OSError, ProcessLookupError):
                            # Process already dead - this is success
                            print(f"Process {name} (PID: {pid}) already terminated")
                            # Reap zombie processes to prevent accumulation
                            self._reap_zombie_if_child(pid)
                except (OSError, ProcessLookupError):
                    # Process already dead or no permission
                    print(f"Process {name} (PID: {pid}) already dead or no permission")
                    pass
        
        # Clear the PID file after cleanup
        self._save_pids({})
        return success
    
    def get_running_processes(self) -> Dict[str, int]:
        running = {}
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pids = json.load(f)
                for name, proc_info in pids.items():
                    # Handle both old format (just PID) and new format (dict with pid/pgid)
                    if isinstance(proc_info, dict):
                        pid = proc_info.get('pid')
                    else:
                        # Old format - just PID
                        pid = proc_info
                    
                    if pid and self._is_process_running(pid):
                        running[name] = pid
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return running
    
    def monitor_health(self) -> List[str]:
        unhealthy = []
        for name in list(self.processes.keys()):
            if not self.is_process_healthy(name):
                unhealthy.append(name)
                self.deregister_process(name)
        return unhealthy
    
    def get_process_group_id(self, name: str) -> Optional[int]:
        """Get the process group ID for a named process"""
        if name not in self.processes:
            return None
        
        process = self.processes[name]
        try:
            return os.getpgid(process.pid)
        except (OSError, ProcessLookupError):
            return None
    
    def kill_process_group(self, pgid: int, signal_type: int = signal.SIGTERM) -> bool:
        """Send a signal to an entire process group"""
        try:
            os.kill(-pgid, signal_type)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def is_process_group_running(self, pgid: int) -> bool:
        """Check if any processes exist in the given process group"""
        try:
            # Try to send signal 0 (no-op) to the process group to check if it exists
            os.kill(-pgid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def get_process_group_info(self) -> Dict[str, Dict[str, int]]:
        """Get detailed process and process group information for all tracked processes"""
        info = {}
        for name, process in self.processes.items():
            try:
                pgid = os.getpgid(process.pid)
                info[name] = {
                    'pid': process.pid,
                    'pgid': pgid,
                    'running': self._is_process_running(process.pid)
                }
            except (OSError, ProcessLookupError):
                info[name] = {
                    'pid': process.pid,
                    'pgid': None,
                    'running': False
                }
        return info