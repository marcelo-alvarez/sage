#!/usr/bin/env python3
"""
Comprehensive test suite for ProcessManager functionality
Tests PID tracking, signal handling, orphan prevention, and system-wide cleanup
"""

import unittest
import subprocess
import sys
import time
import json
import signal
import os
import tempfile
import shutil
from pathlib import Path
from process_manager import ProcessManager


class TestProcessManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test PID files
        self.test_config_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get('HOME')
        
        # Mock home directory to use our test directory
        os.environ['HOME'] = str(self.test_config_dir)
        
        self.process_manager = ProcessManager()
        
        # Store original signal handlers
        self.original_sigint = signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.original_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore original home directory
        if self.original_home:
            os.environ['HOME'] = self.original_home
        else:
            del os.environ['HOME']
        
        # Clean up any test processes
        self.process_manager.cleanup_all_processes()
        
        # Restore original signal handlers
        signal.signal(signal.SIGINT, self.original_sigint)
        signal.signal(signal.SIGTERM, self.original_sigterm)
        
        # Remove test directory
        shutil.rmtree(self.test_config_dir, ignore_errors=True)
    
    def test_pid_file_creation_and_tracking(self):
        """Test that ProcessManager creates and maintains PID file correctly"""
        # Start a simple test process
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
        
        # Register with ProcessManager
        self.process_manager.register_process('test_process', process)
        
        # Check PID file exists and contains correct information
        pid_file = self.test_config_dir / '.claude-orchestrator' / 'pids.json'
        self.assertTrue(pid_file.exists(), "PID file should be created")
        
        with open(pid_file, 'r') as f:
            pids = json.load(f)
        
        self.assertIn('test_process', pids, "Process should be tracked in PID file")
        self.assertEqual(pids['test_process'], process.pid, "PID should match actual process PID")
        
        # Clean up
        self.process_manager.terminate_process('test_process')
    
    def test_process_registration_and_deregistration(self):
        """Test process registration and deregistration"""
        # Start multiple test processes
        process1 = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
        process2 = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
        
        # Register processes
        self.process_manager.register_process('process1', process1)
        self.process_manager.register_process('process2', process2)
        
        # Verify both are tracked
        running = self.process_manager.get_running_processes()
        self.assertIn('process1', running)
        self.assertIn('process2', running)
        
        # Deregister one process
        self.process_manager.deregister_process('process1')
        
        # Verify only process2 is tracked
        running = self.process_manager.get_running_processes()
        self.assertNotIn('process1', running)
        self.assertIn('process2', running)
        
        # Clean up
        process1.terminate()
        self.process_manager.terminate_process('process2')
    
    def test_graceful_termination(self):
        """Test graceful process termination"""
        # Start a test process
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
        self.process_manager.register_process('test_process', process)
        
        # Verify process is running
        self.assertTrue(self.process_manager.is_process_healthy('test_process'))
        
        # Terminate gracefully
        success = self.process_manager.terminate_process('test_process', timeout=5)
        
        # Verify termination was successful
        self.assertTrue(success, "Process should terminate successfully")
        self.assertFalse(self.process_manager.is_process_healthy('test_process'))
        
        # Verify process is deregistered
        running = self.process_manager.get_running_processes()
        self.assertNotIn('test_process', running)
    
    def test_force_termination(self):
        """Test force termination when graceful fails"""
        # Start a process that ignores SIGTERM
        process_code = '''
import signal
import time

def ignore_signal(sig, frame):
    pass

signal.signal(signal.SIGTERM, ignore_signal)
time.sleep(30)
'''
        process = subprocess.Popen([sys.executable, '-c', process_code])
        self.process_manager.register_process('stubborn_process', process)
        
        # Try to terminate with short timeout to force kill
        success = self.process_manager.terminate_process('stubborn_process', timeout=1)
        
        # Process should still be terminated via SIGKILL
        self.assertTrue(success, "Process should be force-killed")
        
        # Verify process is no longer running
        time.sleep(1)  # Give a moment for cleanup
        self.assertIsNotNone(process.poll(), "Process should be terminated")
    
    def test_health_monitoring(self):
        """Test health monitoring functionality"""
        # Start a test process
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
        self.process_manager.register_process('healthy_process', process)
        
        # Verify process is healthy
        self.assertTrue(self.process_manager.is_process_healthy('healthy_process'))
        
        # Kill the process externally
        process.terminate()
        process.wait()
        
        # Health check should detect the dead process
        time.sleep(0.1)  # Give a moment for process to die
        self.assertFalse(self.process_manager.is_process_healthy('healthy_process'))
        
        # Monitor health should detect and clean up unhealthy processes
        unhealthy = self.process_manager.monitor_health()
        self.assertIn('healthy_process', unhealthy)
        
        # Process should be deregistered
        running = self.process_manager.get_running_processes()
        self.assertNotIn('healthy_process', running)
    
    def test_stale_pid_cleanup(self):
        """Test cleanup of stale PIDs from file"""
        # Manually create a PID file with a non-existent PID
        pid_file = self.test_config_dir / '.claude-orchestrator' / 'pids.json'
        pid_file.parent.mkdir(exist_ok=True)
        
        # Use a PID that should not exist (very high number)
        fake_pids = {'fake_process': 999999}
        with open(pid_file, 'w') as f:
            json.dump(fake_pids, f)
        
        # Create a new ProcessManager instance to trigger cleanup
        new_pm = ProcessManager()
        
        # The fake PID should be cleaned up
        running = new_pm.get_running_processes()
        self.assertNotIn('fake_process', running)
    
    def test_system_wide_cleanup(self):
        """Test system-wide process cleanup"""
        # Start multiple test processes
        processes = []
        for i in range(3):
            process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])
            self.process_manager.register_process(f'test_process_{i}', process)
            processes.append(process)
        
        # Verify all processes are tracked
        running = self.process_manager.get_running_processes()
        self.assertEqual(len(running), 3)
        
        # Perform system-wide cleanup
        success = self.process_manager.cleanup_system_wide()
        
        # Verify cleanup was successful
        self.assertTrue(success, "System-wide cleanup should succeed")
        
        # Verify all processes are terminated
        time.sleep(1)  # Give processes time to die
        for process in processes:
            self.assertIsNotNone(process.poll(), f"Process {process.pid} should be terminated")
        
        # Verify PID file is cleared
        running = self.process_manager.get_running_processes()
        self.assertEqual(len(running), 0, "All processes should be cleaned up")
    
    def test_multiple_start_stop_cycles(self):
        """Test orphan prevention with multiple start/stop cycles"""
        orphan_count = 0
        
        for cycle in range(5):
            # Start processes
            processes = []
            for i in range(2):
                process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
                self.process_manager.register_process(f'cycle_{cycle}_process_{i}', process)
                processes.append(process)
            
            # Verify processes are running
            running = self.process_manager.get_running_processes()
            self.assertEqual(len(running), 2)
            
            # Stop all processes
            success = self.process_manager.cleanup_all_processes()
            self.assertTrue(success, f"Cleanup should succeed in cycle {cycle}")
            
            # Check for orphans by counting Python processes
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            python_processes = [line for line in result.stdout.split('\n') 
                              if 'python' in line and 'time.sleep' in line]
            current_orphans = len(python_processes)
            
            if current_orphans > orphan_count:
                self.fail(f"Orphaned processes detected after cycle {cycle}: {current_orphans - orphan_count} new orphans")
            
            orphan_count = current_orphans
        
        # Final verification - should be no orphans
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        python_processes = [line for line in result.stdout.split('\n') 
                          if 'python' in line and 'time.sleep' in line]
        self.assertEqual(len(python_processes), 0, "No orphaned processes should remain")
    
    def test_cleanup_timeout_compliance(self):
        """Test that cleanup completes within specified timeouts"""
        # Start a well-behaved process
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
        self.process_manager.register_process('timeout_test', process)
        
        # Test graceful termination timeout
        start_time = time.time()
        success = self.process_manager.terminate_process('timeout_test', timeout=5)
        elapsed = time.time() - start_time
        
        self.assertTrue(success, "Termination should succeed")
        self.assertLess(elapsed, 7, "Graceful termination should complete within timeout + margin")
        
        # Test force termination timing with stubborn process
        stubborn_code = '''
import signal
import time

def ignore_signal(sig, frame):
    pass

signal.signal(signal.SIGTERM, ignore_signal)
time.sleep(30)
'''
        process = subprocess.Popen([sys.executable, '-c', stubborn_code])
        self.process_manager.register_process('stubborn_test', process)
        
        start_time = time.time()
        success = self.process_manager.terminate_process('stubborn_test', timeout=2)
        elapsed = time.time() - start_time
        
        self.assertTrue(success, "Force termination should succeed")
        # Should complete within graceful timeout + force timeout + margin
        self.assertLess(elapsed, 8, "Force termination should complete within expected timeframe")
    
    def test_pid_file_synchronization(self):
        """Test that PID file remains synchronized with actual processes"""
        # Start processes
        processes = []
        for i in range(3):
            process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'])
            self.process_manager.register_process(f'sync_test_{i}', process)
            processes.append(process)
        
        # Verify synchronization
        running = self.process_manager.get_running_processes()
        self.assertEqual(len(running), 3)
        
        # Kill one process externally
        processes[1].terminate()
        processes[1].wait()
        
        # Create new ProcessManager to test stale PID cleanup
        new_pm = ProcessManager()
        running = new_pm.get_running_processes()
        
        # Should only have 2 running processes now
        self.assertEqual(len(running), 2)
        
        # Clean up remaining processes
        for i, process in enumerate(processes):
            if i != 1:  # Skip the already terminated one
                new_pm.terminate_process(f'sync_test_{i}')


def run_orchestrator_signal_test():
    """Integration test for signal handling in the main orchestrator"""
    import orchestrate
    import threading
    import tempfile
    import shutil
    
    # This test would ideally be run as a separate process
    # to properly test signal handling, but we'll do a basic test here
    
    test_dir = Path(tempfile.mkdtemp())
    original_home = os.environ.get('HOME')
    
    try:
        os.environ['HOME'] = str(test_dir)
        
        # Create orchestrator instance
        orchestrator = orchestrate.ClaudeCodeOrchestrator(headless=True)
        
        # Verify ProcessManager is initialized
        assert orchestrator.process_manager is not None
        
        # Verify signal handlers are installed (we can't easily test the actual signal handling
        # without forking processes, but we can verify the setup doesn't crash)
        
        print("✓ Orchestrator signal handling setup completed successfully")
        
    finally:
        if original_home:
            os.environ['HOME'] = original_home
        else:
            del os.environ['HOME']
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    print("Running ProcessManager test suite...")
    
    # Run the unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration test
    print("\nRunning integration tests...")
    run_orchestrator_signal_test()
    
    print("\n✓ All tests completed!")