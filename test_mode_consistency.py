#!/usr/bin/env python3
"""
Test Mode Consistency Between Components

Tests that api_server.py and orchestrate.py use identical mode detection
and path resolution via StatusReader centralized methods.

Success Criteria:
- StatusReader's _get_current_mode() method returns identical mode values when called from both contexts
- All file operations use StatusReader's _get_outputs_dir() method instead of hardcoded mode checks
- API server status endpoint returns identical directory paths as orchestrator CLI
- Directory path resolution is consistent when switching between regular and meta modes
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from workflow_status import StatusReader, get_workflow_status
from orchestrate import ClaudeCodeOrchestrator


class TestModeConsistency(unittest.TestCase):
    """Test consistency of mode detection and path resolution between components"""
    
    def setUp(self):
        """Set up test environment with temporary directories"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        os.chdir(self.test_dir)
        
        # Create basic project structure
        (self.test_dir / '.claude').mkdir()
        (self.test_dir / '.agent-outputs').mkdir()
        
        print(f"[TEST] Created test environment at: {self.test_dir}")
        
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        
    def test_statusreader_mode_detection_consistency(self):
        """Test that StatusReader._get_current_mode() returns consistent results"""
        print(f"\n[TEST] Testing StatusReader mode detection consistency")
        
        # Test regular mode
        status_reader = StatusReader(project_root=self.test_dir)
        regular_mode = status_reader._get_current_mode()
        self.assertEqual(regular_mode, 'regular')
        print(f"[TEST] Regular mode detected: {regular_mode}")
        
        # Create meta mode directory and test
        (self.test_dir / '.agent-outputs-meta').mkdir()
        meta_mode = status_reader._get_current_mode()
        self.assertEqual(meta_mode, 'meta')
        print(f"[TEST] Meta mode detected: {meta_mode}")
        
        # Test multiple StatusReader instances return same result
        status_reader_2 = StatusReader(project_root=self.test_dir)
        meta_mode_2 = status_reader_2._get_current_mode()
        self.assertEqual(meta_mode, meta_mode_2)
        print(f"[TEST] ✓ Multiple StatusReader instances return identical mode values")
        
    def test_path_resolution_consistency(self):
        """Test that StatusReader path resolution is consistent across contexts"""
        print(f"\n[TEST] Testing path resolution consistency")
        
        status_reader = StatusReader(project_root=self.test_dir)
        
        # Test regular mode paths
        regular_outputs = status_reader._get_outputs_dir()
        regular_claude = status_reader._get_claude_dir()
        self.assertEqual(regular_outputs, self.test_dir / '.agent-outputs')
        self.assertEqual(regular_claude, self.test_dir / '.claude')
        print(f"[TEST] Regular mode paths - outputs: {regular_outputs.name}, claude: {regular_claude.name}")
        
        # Create meta mode directory and test meta paths
        (self.test_dir / '.agent-outputs-meta').mkdir()
        (self.test_dir / '.claude-meta').mkdir()
        
        meta_outputs = status_reader._get_outputs_dir()
        meta_claude = status_reader._get_claude_dir()
        self.assertEqual(meta_outputs, self.test_dir / '.agent-outputs-meta')
        self.assertEqual(meta_claude, self.test_dir / '.claude-meta')
        print(f"[TEST] Meta mode paths - outputs: {meta_outputs.name}, claude: {meta_claude.name}")
        
        print(f"[TEST] ✓ Path resolution switches correctly between modes")
        
    def test_orchestrator_statusreader_consistency(self):
        """Test that orchestrator uses StatusReader methods consistently"""
        print(f"\n[TEST] Testing orchestrator StatusReader usage consistency")
        
        # Create minimal orchestrator instance (without starting full workflow)
        original_argv = sys.argv.copy()
        
        try:
            # Test regular mode
            sys.argv = ['orchestrate.py']
            orchestrator = ClaudeCodeOrchestrator()
            
            # Verify orchestrator uses StatusReader for path resolution
            self.assertIsInstance(orchestrator.status_reader, StatusReader)
            self.assertEqual(orchestrator.outputs_dir.resolve(), (self.test_dir / '.agent-outputs').resolve())
            self.assertEqual(orchestrator.claude_dir.resolve(), (self.test_dir / '.claude').resolve())
            print(f"[TEST] Regular mode orchestrator paths - outputs: {orchestrator.outputs_dir.name}, claude: {orchestrator.claude_dir.name}")
            
            # Test meta mode
            (self.test_dir / '.agent-outputs-meta').mkdir()
            (self.test_dir / '.claude-meta').mkdir()
            
            sys.argv = ['orchestrate.py', 'meta']
            orchestrator_meta = ClaudeCodeOrchestrator()
            
            self.assertEqual(orchestrator_meta.outputs_dir.resolve(), (self.test_dir / '.agent-outputs-meta').resolve())
            self.assertEqual(orchestrator_meta.claude_dir.resolve(), (self.test_dir / '.claude-meta').resolve())
            print(f"[TEST] Meta mode orchestrator paths - outputs: {orchestrator_meta.outputs_dir.name}, claude: {orchestrator_meta.claude_dir.name}")
            
            print(f"[TEST] ✓ Orchestrator uses StatusReader centralized path resolution consistently")
            
        finally:
            sys.argv = original_argv
            
    def test_unified_function_consistency(self):
        """Test that get_workflow_status() function returns consistent results"""
        print(f"\n[TEST] Testing get_workflow_status() function consistency")
        
        # Create basic status file for testing
        status_content = """# Current Status

## Current Task
Testing mode consistency

## Workflow Progress
- [ ] ⏳ Explorer
- [ ] ⏳ Planner  
- [ ] ⏳ Coder
- [ ] ⏳ Verifier

## Agents Status
All agents pending
"""
        
        # Test regular mode
        (self.test_dir / '.agent-outputs' / 'current-status.md').write_text(status_content)
        
        status_regular = get_workflow_status(project_root=self.test_dir, mode='regular')
        self.assertIsInstance(status_regular, dict)
        self.assertIn('currentTask', status_regular)
        self.assertIn('workflow', status_regular)
        print(f"[TEST] Regular mode status retrieved: {len(status_regular['workflow'])} workflow items")
        
        # Test meta mode
        (self.test_dir / '.agent-outputs-meta').mkdir()
        (self.test_dir / '.agent-outputs-meta' / 'current-status.md').write_text(status_content)
        
        status_meta = get_workflow_status(project_root=self.test_dir, mode='meta')
        self.assertIsInstance(status_meta, dict)
        self.assertIn('currentTask', status_meta)
        self.assertIn('workflow', status_meta)
        print(f"[TEST] Meta mode status retrieved: {len(status_meta['workflow'])} workflow items")
        
        # Test auto-detection (should detect meta mode due to .agent-outputs-meta existence)
        status_auto = get_workflow_status(project_root=self.test_dir)
        self.assertEqual(len(status_auto['workflow']), len(status_meta['workflow']))
        print(f"[TEST] Auto-detection matches meta mode: {len(status_auto['workflow'])} workflow items")
        
        print(f"[TEST] ✓ get_workflow_status() function returns consistent results across modes")
        
    def test_cross_component_consistency(self):
        """Test that both components return identical results for same mode state"""
        print(f"\n[TEST] Testing cross-component consistency")
        
        # Create meta mode environment
        (self.test_dir / '.agent-outputs-meta').mkdir()
        (self.test_dir / '.claude-meta').mkdir()
        
        # Test StatusReader directly (simulating api_server.py usage)
        status_reader_direct = StatusReader(project_root=self.test_dir)
        api_mode = status_reader_direct._get_current_mode()
        api_outputs_dir = status_reader_direct._get_outputs_dir()
        api_claude_dir = status_reader_direct._get_claude_dir()
        
        # Test via orchestrator (simulating orchestrate.py usage)
        original_argv = sys.argv.copy()
        try:
            sys.argv = ['orchestrate.py', 'meta']
            orchestrator = ClaudeCodeOrchestrator()
            cli_mode = orchestrator.status_reader._get_current_mode()
            cli_outputs_dir = orchestrator.outputs_dir
            cli_claude_dir = orchestrator.claude_dir
            
            # Verify identical results (resolve paths to handle symlinks like /var -> /private/var on macOS)
            self.assertEqual(api_mode, cli_mode)
            self.assertEqual(api_outputs_dir.resolve(), cli_outputs_dir.resolve())
            self.assertEqual(api_claude_dir.resolve(), cli_claude_dir.resolve())
            
            print(f"[TEST] API detected mode: {api_mode}, paths: {api_outputs_dir.name}, {api_claude_dir.name}")
            print(f"[TEST] CLI detected mode: {cli_mode}, paths: {cli_outputs_dir.name}, {cli_claude_dir.name}")
            print(f"[TEST] ✓ Both components return identical paths for same mode state")
            
        finally:
            sys.argv = original_argv


if __name__ == '__main__':
    print("="*80)
    print("TESTING MODE CONSISTENCY BETWEEN COMPONENTS")
    print("="*80)
    
    unittest.main(verbosity=2)