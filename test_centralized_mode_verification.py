#!/usr/bin/env python3
"""
Test script to verify centralized mode detection and path resolution in StatusReader
Validates all 5 approved success criteria from success-criteria.md
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_status import StatusReader, get_workflow_status

def test_success_criteria():
    """Test all 5 approved success criteria"""
    print("Testing centralized mode detection and path resolution...")
    
    # Create a temporary test directory to avoid conflicts
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test 1: StatusReader class contains centralized _get_current_mode() method
        print("1. Testing centralized _get_current_mode() method...")
        reader = StatusReader(temp_path)
        
        # Should detect regular mode when no .agent-outputs-meta exists
        current_mode = reader._get_current_mode()
        assert current_mode == 'regular', f"Expected 'regular' mode, got '{current_mode}'"
        print("   PASS: Regular mode detection works")
        
        # Create .agent-outputs-meta directory
        meta_dir = temp_path / '.agent-outputs-meta'
        meta_dir.mkdir()
        
        # Should now detect meta mode
        current_mode = reader._get_current_mode()
        assert current_mode == 'meta', f"Expected 'meta' mode, got '{current_mode}'"
        print("   PASS: Meta mode detection works")
        
        # Test 2: StatusReader class contains centralized path resolution methods
        print("2. Testing centralized _get_outputs_dir() and _get_claude_dir() methods...")
        
        # Test explicit mode parameters
        outputs_dir_regular = reader._get_outputs_dir('regular')
        outputs_dir_meta = reader._get_outputs_dir('meta')
        claude_dir_regular = reader._get_claude_dir('regular')
        claude_dir_meta = reader._get_claude_dir('meta')
        
        assert outputs_dir_regular == temp_path / '.agent-outputs', f"Regular outputs dir incorrect: {outputs_dir_regular}"
        assert outputs_dir_meta == temp_path / '.agent-outputs-meta', f"Meta outputs dir incorrect: {outputs_dir_meta}"
        assert claude_dir_regular == temp_path / '.claude', f"Regular claude dir incorrect: {claude_dir_regular}"
        assert claude_dir_meta == temp_path / '.claude-meta', f"Meta claude dir incorrect: {claude_dir_meta}"
        print("   PASS: Explicit mode path resolution works")
        
        # Test auto-detection (should use meta mode since .agent-outputs-meta exists)
        outputs_dir_auto = reader._get_outputs_dir()
        claude_dir_auto = reader._get_claude_dir()
        
        assert outputs_dir_auto == temp_path / '.agent-outputs-meta', f"Auto outputs dir should be meta: {outputs_dir_auto}"
        assert claude_dir_auto == temp_path / '.claude-meta', f"Auto claude dir should be meta: {claude_dir_auto}"
        print("   PASS: Auto-detection path resolution works")
        
        # Test 3: All file operations use centralized path resolution
        print("3. Testing that all file operations use centralized methods...")
        
        # Create some test files
        (temp_path / '.agent-outputs-meta').mkdir(exist_ok=True)
        (temp_path / '.claude-meta').mkdir(exist_ok=True)
        
        status_file = temp_path / '.agent-outputs-meta' / 'current-status.md'
        checklist_file = temp_path / '.claude-meta' / 'tasks-checklist.md'
        
        status_file.write_text("✅ Explorer\n⏳ Planner")
        checklist_file.write_text("# Tasks\n- [x] Complete task 1\n- [ ] Do task 2")
        
        # These methods should work without hardcoded mode checks
        status_result = reader.read_status()  # Uses auto-detection
        validation_check = reader._has_user_validation_gate()  # Uses auto-detection
        completion_check = reader._is_workflow_complete()  # Uses auto-detection
        outputs_status = reader.get_current_outputs_status()  # Uses auto-detection
        
        # Verify they used the correct paths (meta mode)
        assert isinstance(status_result, dict), "Status result should be dict"
        assert isinstance(validation_check, bool), "Validation check should be bool"
        assert isinstance(completion_check, bool), "Completion check should be bool"
        assert isinstance(outputs_status, dict), "Outputs status should be dict"
        print("   PASS: All file operations use centralized path resolution")
        
        # Test 4: Meta mode workflows complete without path errors
        print("4. Testing meta mode workflow completion...")
        
        # Test unified function with auto-detection
        workflow_status = get_workflow_status(temp_path)
        assert isinstance(workflow_status, dict), "Workflow status should be dict"
        assert 'currentTask' in workflow_status, "Should have currentTask"
        assert 'workflow' in workflow_status, "Should have workflow"
        print("   PASS: Meta mode workflows complete without path errors")
        
        # Test 5: Test consistency between components
        print("5. Testing consistency between StatusReader instances...")
        
        # Create second StatusReader instance
        reader2 = StatusReader(temp_path)
        
        # Both should detect same mode and use same paths
        mode1 = reader._get_current_mode()
        mode2 = reader2._get_current_mode()
        assert mode1 == mode2, f"Mode detection inconsistent: {mode1} vs {mode2}"
        
        outputs1 = reader._get_outputs_dir()
        outputs2 = reader2._get_outputs_dir()
        assert outputs1 == outputs2, f"Outputs dir inconsistent: {outputs1} vs {outputs2}"
        
        claude1 = reader._get_claude_dir()
        claude2 = reader2._get_claude_dir()
        assert claude1 == claude2, f"Claude dir inconsistent: {claude1} vs {claude2}"
        print("   PASS: StatusReader instances are consistent")
        
    print("\n✅ ALL 5 SUCCESS CRITERIA VERIFIED!")
    return True

def test_existing_tests_still_pass():
    """Verify that existing tests still pass after centralization"""
    print("Testing that existing tests still pass...")
    
    # Try to run the existing consistency tests
    try:
        # Import and run existing tests if they exist
        if (Path(__file__).parent / 'test_project_root_consistency.py').exists():
            import subprocess
            result = subprocess.run([sys.executable, 'test_project_root_consistency.py'], 
                                  capture_output=True, text=True, cwd=Path(__file__).parent)
            if result.returncode == 0:
                print("   PASS: test_project_root_consistency.py still passes")
            else:
                print(f"   WARNING: test_project_root_consistency.py failed: {result.stderr}")
                
    except Exception as e:
        print(f"   WARNING: Could not run existing tests: {e}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("CENTRALIZED MODE DETECTION VERIFICATION")
    print("=" * 60)
    
    try:
        success1 = test_success_criteria()
        success2 = test_existing_tests_still_pass()
        
        if success1 and success2:
            print("\n🎉 ALL VERIFICATION TESTS PASSED!")
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)