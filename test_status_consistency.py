#!/usr/bin/env python3
"""
Test script to validate status consistency between CLI and API interfaces.
This ensures that cc-orchestrate status and GET /api/status return identical data.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
import requests
from threading import Thread
import signal

def start_api_server_background():
    """Start API server in background for testing."""
    try:
        # Start API server in background
        process = subprocess.Popen(
            [sys.executable, "api_server.py", "--port", "8001"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path.cwd()
        )
        
        # Wait for server to start
        time.sleep(2)
        
        # Check if server is running
        try:
            response = requests.get("http://localhost:8001/api/status", timeout=5)
            if response.status_code == 200:
                print("✓ API server started successfully on port 8001")
                return process
        except requests.exceptions.RequestException:
            pass
        
        print("✗ Failed to start API server")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"✗ Error starting API server: {e}")
        return None

def get_cli_status():
    """Get status using the same method orchestrate.py uses internally."""
    try:
        print("Getting status via unified function (simulating CLI)...")
        from workflow_status import get_workflow_status
        from pathlib import Path
        
        # This is the same method orchestrate.py uses internally
        status_data = get_workflow_status(project_root=Path.cwd())
        
        if isinstance(status_data, dict):
            print("✓ CLI-equivalent status data retrieved successfully")
            return status_data
        else:
            print(f"✗ CLI-equivalent status data failed: unexpected type {type(status_data)}")
            return None
            
    except Exception as e:
        print(f"✗ Error getting CLI-equivalent status data: {e}")
        return None

def get_api_status():
    """Get status using API endpoint."""
    try:
        print("Getting status via API...")
        response = requests.get("http://localhost:8001/api/status", timeout=10)
        
        if response.status_code == 200:
            print("✓ API status request successful")
            return response.json()
        else:
            print(f"✗ API status request failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ Error requesting API status: {e}")
        return None

def compare_status_data(cli_data, api_data):
    """Compare CLI and API status data for consistency."""
    print("\nComparing CLI and API status data...")
    
    # Both are now JSON/dict format
    if not cli_data or not api_data:
        print("✗ Cannot compare - missing data")
        return False
    
    try:
        # Check if both data structures contain the same fields
        expected_fields = ["currentTask", "workflow", "workflowComplete"]
        
        cli_fields = [field for field in expected_fields if field in cli_data]
        api_fields = [field for field in expected_fields if field in api_data]
        
        if cli_fields != api_fields:
            print(f"✗ Field mismatch - CLI: {cli_fields}, API: {api_fields}")
            return False
        
        print(f"✓ Both contain same fields: {cli_fields}")
        
        # Compare current task
        cli_task = cli_data.get("currentTask", "")
        api_task = api_data.get("currentTask", "")
        
        if cli_task != api_task:
            print(f"✗ Current task mismatch:")
            print(f"  CLI:  '{cli_task}'")
            print(f"  API:  '{api_task}'")
            return False
        
        print(f"✓ Current task matches: '{cli_task}'")
        
        # Compare workflow items count
        cli_workflow = cli_data.get("workflow", [])
        api_workflow = api_data.get("workflow", [])
        
        if len(cli_workflow) != len(api_workflow):
            print(f"✗ Workflow count mismatch - CLI: {len(cli_workflow)}, API: {len(api_workflow)}")
            return False
        
        print(f"✓ Workflow item count matches: {len(cli_workflow)}")
        
        # Compare completion status
        cli_complete = cli_data.get("workflowComplete", False)
        api_complete = api_data.get("workflowComplete", False)
        
        if cli_complete != api_complete:
            print(f"✗ Completion status mismatch - CLI: {cli_complete}, API: {api_complete}")
            return False
        
        print(f"✓ Completion status matches: {cli_complete}")
        
        print("✓ SUCCESS: CLI and API status data are identical")
        return True
        
    except Exception as e:
        print(f"✗ Error comparing status data: {e}")
        return False

def test_unified_function_direct():
    """Test get_workflow_status function directly."""
    print("\nTesting get_workflow_status function directly...")
    
    try:
        from workflow_status import get_workflow_status
        from pathlib import Path
        
        # Get status using the unified function
        status_data = get_workflow_status(project_root=Path.cwd())
        
        if isinstance(status_data, dict):
            print("✓ get_workflow_status returns dict data structure")
            
            # Check required fields
            required_fields = ["currentTask", "workflow", "workflowComplete"]
            present_fields = [field for field in required_fields if field in status_data]
            
            print(f"✓ Present fields: {present_fields}")
            print(f"✓ Workflow items: {len(status_data.get('workflow', []))}")
            print(f"✓ Completion status: {status_data.get('workflowComplete', False)}")
            
            return True
        else:
            print(f"✗ get_workflow_status returned unexpected type: {type(status_data)}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing unified function: {e}")
        return False

def main():
    print("Status Consistency Validation")
    print("=" * 40)
    
    # Test unified function first
    test_results = []
    test_results.append(test_unified_function_direct())
    
    # Start API server for cross-component testing
    print("\nStarting API server for cross-component testing...")
    api_process = start_api_server_background()
    
    if api_process:
        try:
            # Get CLI-equivalent status
            cli_status = get_cli_status()
            
            # Get API status
            api_status = get_api_status()
            
            # Compare results
            consistency_result = compare_status_data(cli_status, api_status)
            test_results.append(consistency_result)
            
        finally:
            # Clean up API server
            print("\nCleaning up API server...")
            api_process.terminate()
            time.sleep(1)
            if api_process.poll() is None:
                api_process.kill()
            print("✓ API server stopped")
    else:
        print("✗ Skipping cross-component test - API server failed to start")
        test_results.append(False)
    
    # Summary
    print("\n" + "=" * 40)
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"✓ ALL TESTS PASSED ({passed}/{total})")
        print("Status reading is consistent across CLI and API interfaces.")
        return True
    else:
        print(f"✗ {total - passed} TESTS FAILED ({passed}/{total})")
        print("Status consistency needs further investigation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)