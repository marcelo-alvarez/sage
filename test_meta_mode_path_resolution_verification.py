#!/usr/bin/env python3

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from workflow_status import StatusReader, get_workflow_status

def test_api_server_uses_centralized_methods():
    """Test that api_server.py uses StatusReader._get_current_mode() and _get_outputs_dir()"""
    print("1. Testing api_server.py uses centralized StatusReader methods...")
    
    # Read api_server.py source
    api_server_file = Path("api_server.py")
    if not api_server_file.exists():
        print("   FAIL: api_server.py not found")
        return False
    
    api_content = api_server_file.read_text()
    
    # Check that old _get_outputs_directory method was removed
    if "_get_outputs_directory" in api_content:
        print("   FAIL: Custom _get_outputs_directory method still exists")
        return False
    
    # Check that it uses StatusReader methods
    if "self.status_reader._get_outputs_dir(" not in api_content:
        print("   FAIL: Does not use StatusReader._get_outputs_dir()")
        return False
        
    if "self.status_reader._get_claude_dir(" not in api_content:
        print("   FAIL: Does not use StatusReader._get_claude_dir()")
        return False
    
    print("   PASS: api_server.py uses centralized StatusReader methods")
    return True

def test_orchestrate_uses_centralized_methods():
    """Test that orchestrate.py uses StatusReader._get_current_mode() for mode detection"""
    print("2. Testing orchestrate.py uses centralized mode detection...")
    
    # Read orchestrate.py source
    orchestrate_file = Path("orchestrate.py")
    if not orchestrate_file.exists():
        print("   FAIL: orchestrate.py not found")
        return False
    
    orchestrate_content = orchestrate_file.read_text()
    
    # Check that custom _get_current_mode method was removed
    if "def _get_current_mode(" in orchestrate_content:
        print("   FAIL: Custom _get_current_mode method still exists")
        return False
    
    # Check that it uses StatusReader methods
    if "self.status_reader._get_current_mode()" not in orchestrate_content:
        print("   FAIL: Does not use StatusReader._get_current_mode()")
        return False
        
    if "self.status_reader._get_outputs_dir()" not in orchestrate_content:
        print("   FAIL: Does not use StatusReader._get_outputs_dir()")
        return False
        
    if "self.status_reader._get_claude_dir()" not in orchestrate_content:
        print("   FAIL: Does not use StatusReader._get_claude_dir()")
        return False
    
    print("   PASS: orchestrate.py uses centralized mode detection")
    return True

def test_file_operations_respect_centralized_mode():
    """Test that all file operations in both files respect the centralized mode flag"""
    print("3. Testing all file operations respect centralized mode flag...")
    
    # Create temp directories for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create meta mode directory structure
        meta_outputs = temp_path / ".agent-outputs-meta"
        meta_claude = temp_path / ".claude-meta"
        meta_outputs.mkdir()
        meta_claude.mkdir()
        
        # Create status file for meta mode
        status_file = meta_outputs / "current-status.md"
        status_file.write_text("## Current Status\n\nTest status for meta mode")
        
        # Create checklist file for meta mode
        checklist_file = meta_claude / "tasks-checklist.md"
        checklist_file.write_text("- [x] Test task 1\n- [ ] Test task 2")
        
        # Change to temp directory
        original_cwd = Path.cwd()
        os.chdir(temp_path)
        
        try:
            # Test StatusReader with meta mode
            status_reader = StatusReader(project_root=temp_path)
            
            # Test mode detection
            current_mode = status_reader._get_current_mode()
            if current_mode != "meta":
                print(f"   FAIL: Mode detection failed, got {current_mode}")
                return False
            
            # Test path resolution
            outputs_dir = status_reader._get_outputs_dir("meta")
            claude_dir = status_reader._get_claude_dir("meta")
            
            if outputs_dir.name != ".agent-outputs-meta":
                print(f"   FAIL: Wrong outputs dir: {outputs_dir}")
                return False
                
            if claude_dir.name != ".claude-meta":
                print(f"   FAIL: Wrong claude dir: {claude_dir}")
                return False
            
            # Test workflow status reading
            status = get_workflow_status(mode="meta", project_root=temp_path)
            if not status or not status.get("current_status"):
                print("   FAIL: Could not read workflow status in meta mode")
                return False
            
        finally:
            os.chdir(original_cwd)
    
    print("   PASS: All file operations respect centralized mode flag")
    return True

def test_meta_mode_workflows_no_errors():
    """Test that meta mode workflows complete without FileNotFoundError or NoSuchFileOrDirectory"""
    print("4. Testing meta mode workflows complete without path errors...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create regular mode directory structure first
        regular_outputs = temp_path / ".agent-outputs"
        regular_claude = temp_path / ".claude"
        regular_outputs.mkdir()
        regular_claude.mkdir()
        
        # Create meta mode directory structure
        meta_outputs = temp_path / ".agent-outputs-meta"
        meta_claude = temp_path / ".claude-meta"
        meta_outputs.mkdir()
        meta_claude.mkdir()
        
        # Create status files for both modes
        (regular_outputs / "current-status.md").write_text("Regular status")
        (meta_outputs / "current-status.md").write_text("Meta status")
        
        # Create checklist files for both modes
        (regular_claude / "tasks-checklist.md").write_text("- [x] Regular task")
        (meta_claude / "tasks-checklist.md").write_text("- [x] Meta task")
        
        original_cwd = Path.cwd()
        os.chdir(temp_path)
        
        try:
            # Test both modes work without errors
            for mode in ["regular", "meta"]:
                try:
                    status_reader = StatusReader(project_root=temp_path)
                    
                    # Test mode detection
                    detected_mode = status_reader._get_current_mode()
                    
                    # Test path resolution
                    outputs_dir = status_reader._get_outputs_dir(mode)
                    claude_dir = status_reader._get_claude_dir(mode)
                    
                    # Test file operations
                    status = get_workflow_status(mode=mode, project_root=temp_path)
                    
                    if not outputs_dir.exists():
                        print(f"   FAIL: Outputs directory doesn't exist for {mode}: {outputs_dir}")
                        return False
                    
                    if not claude_dir.exists():
                        print(f"   FAIL: Claude directory doesn't exist for {mode}: {claude_dir}")
                        return False
                    
                    if not status:
                        print(f"   FAIL: Could not get workflow status for {mode}")
                        return False
                        
                except (FileNotFoundError, OSError) as e:
                    print(f"   FAIL: Path error in {mode} mode: {e}")
                    return False
        
        finally:
            os.chdir(original_cwd)
    
    print("   PASS: Meta mode workflows complete without path errors")
    return True

def test_status_requests_identical_results():
    """Test that status requests return identical results whether using centralized StatusReader or individual implementations"""
    print("5. Testing status requests return identical results...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create meta mode test environment
        meta_outputs = temp_path / ".agent-outputs-meta"
        meta_claude = temp_path / ".claude-meta"
        meta_outputs.mkdir()
        meta_claude.mkdir()
        
        # Create identical status content
        status_content = """## Current Status

### Task 1
Status: Complete

### Task 2  
Status: In Progress
"""
        (meta_outputs / "current-status.md").write_text(status_content)
        (meta_claude / "tasks-checklist.md").write_text("- [x] Task 1\n- [ ] Task 2")
        
        original_cwd = Path.cwd()
        os.chdir(temp_path)
        
        try:
            # Get status using centralized methods
            status_reader1 = StatusReader(project_root=temp_path)
            status_reader2 = StatusReader(project_root=temp_path)
            
            status1 = get_workflow_status(mode="meta", project_root=temp_path)
            status2 = get_workflow_status(mode="meta", project_root=temp_path)
            
            # Check that results are identical
            if status1.get("current_status") != status2.get("current_status"):
                print("   FAIL: Status results are inconsistent")
                return False
            
            if status1.get("workflow_complete") != status2.get("workflow_complete"):
                print("   FAIL: Completion status results are inconsistent")
                return False
            
            # Test mode detection consistency
            mode1 = status_reader1._get_current_mode()
            mode2 = status_reader2._get_current_mode()
            
            if mode1 != mode2:
                print(f"   FAIL: Mode detection inconsistent: {mode1} vs {mode2}")
                return False
        
        finally:
            os.chdir(original_cwd)
    
    print("   PASS: Status requests return identical results")
    return True

def test_mode_detection_consistency():
    """Test that mode detection returns consistent results across all components when .agent-outputs-meta directory exists"""
    print("6. Testing mode detection consistency across components...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create meta mode directory (this should trigger meta mode detection)
        meta_outputs = temp_path / ".agent-outputs-meta"
        meta_outputs.mkdir()
        
        original_cwd = Path.cwd()
        os.chdir(temp_path)
        
        try:
            # Create multiple StatusReader instances
            readers = [StatusReader(project_root=temp_path) for _ in range(3)]
            
            # Test that all readers detect the same mode
            modes = [reader._get_current_mode() for reader in readers]
            
            if not all(mode == "meta" for mode in modes):
                print(f"   FAIL: Inconsistent mode detection: {modes}")
                return False
            
            # Test path resolution consistency
            outputs_dirs = [reader._get_outputs_dir() for reader in readers]
            claude_dirs = [reader._get_claude_dir() for reader in readers]
            
            if not all(d.name == ".agent-outputs-meta" for d in outputs_dirs):
                print(f"   FAIL: Inconsistent outputs dir resolution: {[d.name for d in outputs_dirs]}")
                return False
                
            if not all(d.name == ".claude-meta" for d in claude_dirs):
                print(f"   FAIL: Inconsistent claude dir resolution: {[d.name for d in claude_dirs]}")
                return False
        
        finally:
            os.chdir(original_cwd)
    
    print("   PASS: Mode detection returns consistent results across components")
    return True

def main():
    """Run all verification tests"""
    print("=" * 60)
    print("META MODE PATH RESOLUTION VERIFICATION")
    print("=" * 60)
    
    tests = [
        test_api_server_uses_centralized_methods,
        test_orchestrate_uses_centralized_methods,
        test_file_operations_respect_centralized_mode,
        test_meta_mode_workflows_no_errors,
        test_status_requests_identical_results,
        test_mode_detection_consistency
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"   ❌ Test failed: {test.__name__}")
        except Exception as e:
            print(f"   ❌ Test error in {test.__name__}: {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL SUCCESS CRITERIA VERIFIED!")
        return True
    else:
        print("❌ SOME VERIFICATION TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)