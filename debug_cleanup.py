#!/usr/bin/env python3
import subprocess
import sys
import time
from process_manager import ProcessManager

# Create a test process manager
pm = ProcessManager()

# Start test processes
processes = []
for i in range(3):
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])
    pm.register_process(f'debug_test_{i}', process)
    processes.append(process)
    print(f"Started process debug_test_{i} with PID {process.pid}")

# Check running processes
running = pm.get_running_processes()
print(f"Running processes before cleanup: {running}")

# Perform cleanup
print("Starting cleanup...")
success = pm.cleanup_system_wide()
print(f"Cleanup success: {success}")

# Check if processes are still running
time.sleep(1)
for process in processes:
    poll_result = process.poll()
    print(f"Process {process.pid} poll result: {poll_result}")

# Check running processes after cleanup
running_after = pm.get_running_processes()
print(f"Running processes after cleanup: {running_after}")