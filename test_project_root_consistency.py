#!/usr/bin/env python3
"""
Test script to validate project_root consistency between CLI and API components.
This verifies that Path.cwd() resolves to identical absolute paths for status reading.
"""

import os
from pathlib import Path
import sys

def test_project_root_consistency():
    """Test that different Path initialization methods resolve to identical paths."""
    print("Testing project_root initialization consistency...")
    
    # Method 1: Path.cwd() (used by orchestrate.py)
    path_cwd = Path.cwd()
    
    # Method 2: Path(os.getcwd()) (previously used by api_server.py) 
    path_os_getcwd = Path(os.getcwd())
    
    # Get absolute paths for comparison
    abs_path_cwd = path_cwd.resolve()
    abs_path_os_getcwd = path_os_getcwd.resolve()
    
    print(f"Path.cwd(): {path_cwd}")
    print(f"Path.cwd().resolve(): {abs_path_cwd}")
    print(f"Path(os.getcwd()): {path_os_getcwd}")
    print(f"Path(os.getcwd()).resolve(): {abs_path_os_getcwd}")
    
    # Verify they resolve to identical absolute paths
    if abs_path_cwd == abs_path_os_getcwd:
        print("✓ SUCCESS: Both methods resolve to identical absolute paths")
        return True
    else:
        print("✗ FAILURE: Path resolution methods produce different results")
        print(f"  Difference: {abs_path_cwd} != {abs_path_os_getcwd}")
        return False

def test_status_reader_consistency():
    """Test StatusReader initialization with both methods."""
    print("\nTesting StatusReader initialization consistency...")
    
    try:
        from workflow_status import StatusReader, get_workflow_status
        
        # Initialize with both methods
        reader_cwd = StatusReader(project_root=Path.cwd())
        reader_os_getcwd = StatusReader(project_root=Path(os.getcwd()))
        
        print(f"StatusReader with Path.cwd(): {reader_cwd.project_root}")
        print(f"StatusReader with Path(os.getcwd()): {reader_os_getcwd.project_root}")
        
        # Compare resolved project_root values
        if reader_cwd.project_root.resolve() == reader_os_getcwd.project_root.resolve():
            print("✓ SUCCESS: StatusReader instances use identical project_root values")
            return True
        else:
            print("✗ FAILURE: StatusReader instances have different project_root values")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: Failed to test StatusReader consistency: {e}")
        return False

def test_unified_function_consistency():
    """Test get_workflow_status function with both project_root methods."""
    print("\nTesting get_workflow_status function consistency...")
    
    try:
        from workflow_status import get_workflow_status
        
        # Call with both project_root methods
        status_cwd = get_workflow_status(project_root=Path.cwd())
        status_os_getcwd = get_workflow_status(project_root=Path(os.getcwd()))
        
        print(f"get_workflow_status with Path.cwd() returned: {type(status_cwd)}")
        print(f"get_workflow_status with Path(os.getcwd()) returned: {type(status_os_getcwd)}")
        
        # Compare results (should be identical for same working directory)
        if status_cwd == status_os_getcwd:
            print("✓ SUCCESS: get_workflow_status returns identical results with both methods")
            return True
        else:
            print("✗ FAILURE: get_workflow_status returns different results")
            print(f"  Path.cwd() result: {status_cwd}")
            print(f"  Path(os.getcwd()) result: {status_os_getcwd}")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: Failed to test unified function consistency: {e}")
        return False

if __name__ == "__main__":
    print("Project Root Consistency Validation")
    print("=" * 40)
    
    # Run all tests
    results = []
    results.append(test_project_root_consistency())
    results.append(test_status_reader_consistency())
    results.append(test_unified_function_consistency())
    
    # Summary
    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ ALL TESTS PASSED ({passed}/{total})")
        print("StatusReader project_root initialization is now consistent across components.")
        sys.exit(0)
    else:
        print(f"✗ {total - passed} TESTS FAILED ({passed}/{total})")
        print("StatusReader project_root initialization needs further fixes.")
        sys.exit(1)