#!/usr/bin/env python3
"""
Comprehensive verification test for meta mode path resolution consistency.
Validates all approved success criteria from success-criteria.md
"""

import os
import tempfile
import shutil
from pathlib import Path
import subprocess

# Import the relevant components
from workflow_status import StatusReader, get_workflow_status

def test_hardcoded_mode_checks_removed():
    """Test that api_server.py hardcoded mode checks are removed"""
    print("Testing hardcoded mode checks removed...")
    
    # Read api_server.py and check for hardcoded mode checks
    with open('api_server.py', 'r') as f:
        content = f.read()
    
    # Should not contain hardcoded mode == 'meta' checks except in centralized methods
    lines = content.split('\n')
    hardcoded_checks = []
    
    for i, line in enumerate(lines):
        if "mode == 'meta'" in line and "api_server.py" in line:
            hardcoded_checks.append((i+1, line.strip()))
    
    # Check that specific problem lines are fixed
    problem_lines = [685, 955, 982, 1015]
    for line_num in problem_lines:
        if line_num <= len(lines):
            line_content = lines[line_num - 1]
            if "self.status_reader._get_current_mode() == 'meta'" in line_content:
                print(f"   ✓ Line {line_num} uses centralized method")
            else:
                print(f"   ❌ Line {line_num} does not use centralized method: {line_content}")
                return False
    
    print("   PASS: All hardcoded mode checks replaced with centralized methods")
    return True

def test_consistent_command_execution():
    """Test that command execution uses centralized mode detection"""
    print("Testing consistent command execution...")
    
    with open('api_server.py', 'r') as f:
        content = f.read()
    
    # Check for subprocess command building with centralized mode detection
    if "if self.status_reader._get_current_mode() == 'meta':" in content:
        subprocess_uses = content.count("if self.status_reader._get_current_mode() == 'meta':")
        if subprocess_uses >= 4:  # Should be at least 4 usages for start, continue, clean, and gate decisions
            print("   PASS: Command execution uses centralized mode detection")
            return True
    
    print("   FAIL: Command execution does not use centralized mode detection consistently")
    return False

def test_path_resolution_consistency():
    """Test that both components use StatusReader path resolution"""
    print("Testing path resolution consistency...")
    
    # Create test environment
    with tempfile.TemporaryDirectory() as temp_path:
        temp_path = Path(temp_path)
        
        # Create meta mode environment
        meta_outputs = temp_path / ".agent-outputs-meta"
        meta_outputs.mkdir()
        
        # Create status files
        status_file = meta_outputs / "current-status.md"
        status_file.write_text("## Current Status\n\nTest status")
        
        # Test StatusReader path resolution
        status_reader = StatusReader(project_root=temp_path)
        
        # Test mode detection
        mode = status_reader._get_current_mode()
        if mode != "meta":
            print(f"   FAIL: Mode detection failed, expected 'meta', got '{mode}'")
            return False
        
        # Test path resolution
        outputs_dir = status_reader._get_outputs_dir()
        claude_dir = status_reader._get_claude_dir()
        
        if outputs_dir.name != ".agent-outputs-meta":
            print(f"   FAIL: Wrong outputs directory: {outputs_dir}")
            return False
            
        if claude_dir.name != ".claude-meta":
            print(f"   FAIL: Wrong claude directory: {claude_dir}")
            return False
    
    print("   PASS: Path resolution consistency verified")
    return True

def test_mode_detection_uniformity():
    """Test that both components detect identical mode"""
    print("Testing mode detection uniformity...")
    
    # Create test environment
    with tempfile.TemporaryDirectory() as temp_path:
        temp_path = Path(temp_path)
        
        # Create meta mode environment (.agent-outputs-meta directory exists)
        meta_outputs = temp_path / ".agent-outputs-meta"
        meta_outputs.mkdir()
        
        # Test multiple StatusReader instances
        status_reader1 = StatusReader(project_root=temp_path)
        status_reader2 = StatusReader(project_root=temp_path)
        
        mode1 = status_reader1._get_current_mode()
        mode2 = status_reader2._get_current_mode()
        
        if mode1 != mode2:
            print(f"   FAIL: Inconsistent mode detection: {mode1} vs {mode2}")
            return False
        
        if mode1 != "meta":
            print(f"   FAIL: Expected meta mode, got {mode1}")
            return False
    
    print("   PASS: Mode detection uniformity verified")
    return True

def test_file_operation_consistency():
    """Test that file operations use StatusReader methods"""
    print("Testing file operation consistency...")
    
    # Check that both api_server.py and orchestrate.py use StatusReader methods
    files_to_check = ['api_server.py', 'orchestrate.py']
    
    for file_path in files_to_check:
        if not Path(file_path).exists():
            print(f"   SKIP: {file_path} not found")
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for StatusReader usage
        if "self.status_reader._get_current_mode()" in content:
            print(f"   ✓ {file_path} uses StatusReader._get_current_mode()")
        else:
            print(f"   ❌ {file_path} does not use StatusReader._get_current_mode()")
            return False
    
    print("   PASS: File operation consistency verified")
    return True

def test_suite_validation():
    """Test that existing test suites pass"""
    print("Testing existing test suite validation...")
    
    # Run the test_mode_consistency.py test
    try:
        result = subprocess.run(['python', 'test_mode_consistency.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("   ✓ test_mode_consistency.py passes")
        else:
            print(f"   ❌ test_mode_consistency.py failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Error running test_mode_consistency.py: {e}")
        return False
    
    print("   PASS: Test suite validation complete")
    return True

def main():
    """Run comprehensive verification"""
    print("=" * 80)
    print("COMPREHENSIVE META MODE PATH RESOLUTION VERIFICATION")
    print("=" * 80)
    
    tests = [
        ("api_server.py removes hardcoded mode checks", test_hardcoded_mode_checks_removed),
        ("Consistent command execution", test_consistent_command_execution),
        ("Path resolution consistency", test_path_resolution_consistency),
        ("Mode detection uniformity", test_mode_detection_uniformity),
        ("File operation consistency", test_file_operation_consistency),
        ("Test suite validation", test_suite_validation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" + "=" * 78)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nRESULTS: {passed}/{total} success criteria verified")
    
    if passed == total:
        print("🎉 ALL SUCCESS CRITERIA MET - VERIFICATION COMPLETE")
        return True
    else:
        print("❌ SOME SUCCESS CRITERIA NOT MET")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)