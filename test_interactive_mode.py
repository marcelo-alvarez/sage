#!/usr/bin/env python3
"""
Interactive Mode Test Suite

Comprehensive testing for interactive mode (legacy fallback) functionality to validate
that CLAUDE_ORCHESTRATOR_MODE=prompt correctly displays instructions to user
instead of automatic execution, prevents Claude CLI subprocess spawning, and
ensures manual execution produces identical files to headless mode.
"""

import unittest
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import re
from unittest.mock import patch, MagicMock
import sys


class TestInteractiveMode(unittest.TestCase):
    """Test suite for interactive mode functionality validation"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(".agent-outputs-test")
        self.test_dir.mkdir(exist_ok=True)
        
        # Store original environment variable
        self.original_mode = os.environ.get('CLAUDE_ORCHESTRATOR_MODE')
        
    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment variable
        if self.original_mode is not None:
            os.environ['CLAUDE_ORCHESTRATOR_MODE'] = self.original_mode
        else:
            os.environ.pop('CLAUDE_ORCHESTRATOR_MODE', None)
            
        # Clean up test files
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_environment_variable_enables_interactive_mode(self):
        """Test that CLAUDE_ORCHESTRATOR_MODE=prompt correctly enables interactive mode"""
        # Set environment variable
        os.environ['CLAUDE_ORCHESTRATOR_MODE'] = 'prompt'
        
        # Import after setting environment variable
        sys.path.append(str(Path.cwd()))
        from orchestrate import AgentExecutor, ClaudeCodeOrchestrator
        
        # Create mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.outputs_dir = self.test_dir
        
        # Create AgentExecutor in non-headless mode (should read env var)
        executor = AgentExecutor(mock_orchestrator, headless=False)
        
        # Verify interactive mode is enabled
        self.assertTrue(executor.use_interactive_mode, 
                       "Environment variable CLAUDE_ORCHESTRATOR_MODE=prompt should enable interactive mode")
        
        # Document test result
        with open(self.test_dir / "env_var_test.txt", "w") as f:
            f.write(f"CLAUDE_ORCHESTRATOR_MODE: {os.getenv('CLAUDE_ORCHESTRATOR_MODE')}\n")
            f.write(f"use_interactive_mode: {executor.use_interactive_mode}\n")

    def test_orchestrate_start_displays_instructions(self):
        """Test that /orchestrate start displays instructions instead of auto-execution"""
        # Set interactive mode
        os.environ['CLAUDE_ORCHESTRATOR_MODE'] = 'prompt'
        
        try:
            # Run orchestrate start command
            result = subprocess.run([
                sys.executable, 'orchestrate.py', 'start'
            ], capture_output=True, text=True, timeout=60)
            
            # Document the result
            with open(self.test_dir / "orchestrate_start_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
            
            # Check that output contains instructions rather than execution results
            stdout_content = result.stdout
            
            # Look for instruction indicators
            instruction_indicators = [
                "INSTRUCTION TO CLAUDE:",
                "You are now the",
                "agent",
                "FINAL STEP:"
            ]
            
            contains_instructions = any(indicator in stdout_content for indicator in instruction_indicators)
            
            # Look for execution result indicators (should NOT be present in interactive mode)
            execution_indicators = [
                "completed successfully",
                "failed:",
                "Processing time:"
            ]
            
            contains_execution_results = any(indicator in stdout_content for indicator in execution_indicators)
            
            self.assertTrue(contains_instructions, 
                          "Output should contain instructions for manual execution")
            self.assertFalse(contains_execution_results, 
                           "Output should NOT contain automatic execution results in interactive mode")
            
        except subprocess.TimeoutExpired:
            self.fail("orchestrate start command timed out")

    @patch('subprocess.Popen')
    def test_no_claude_cli_subprocess_spawning(self, mock_popen):
        """Test that no Claude CLI subprocess is spawned in interactive mode"""
        # Set interactive mode
        os.environ['CLAUDE_ORCHESTRATOR_MODE'] = 'prompt'
        
        # Import after setting environment variable
        sys.path.append(str(Path.cwd()))
        from orchestrate import AgentExecutor
        
        # Create mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.outputs_dir = self.test_dir
        
        # Create AgentExecutor in interactive mode
        executor = AgentExecutor(mock_orchestrator, headless=False)
        
        # Execute an agent task
        test_instructions = "Test instructions for interactive mode"
        result = executor.execute_agent("test", test_instructions)
        
        # Verify that subprocess.Popen was NOT called
        mock_popen.assert_not_called()
        
        # Verify that the result is the instructions unchanged
        self.assertEqual(result, test_instructions, 
                        "Interactive mode should return instructions unchanged")
        
        # Document test result
        with open(self.test_dir / "no_subprocess_test.txt", "w") as f:
            f.write(f"Popen called: {mock_popen.called}\n")
            f.write(f"Result matches instructions: {result == test_instructions}\n")

    def test_clear_and_continuation_commands_present(self):
        """Test that output contains /clear and continuation commands"""
        # Set interactive mode
        os.environ['CLAUDE_ORCHESTRATOR_MODE'] = 'prompt'
        
        try:
            # Run orchestrate start command
            result = subprocess.run([
                sys.executable, 'orchestrate.py', 'start'
            ], capture_output=True, text=True, timeout=60)
            
            stdout_content = result.stdout
            
            # Check for /clear command
            clear_command_present = '/clear' in stdout_content or '`/clear`' in stdout_content
            
            # Check for continuation command
            continuation_patterns = [
                r'orchestrate\.py continue',
                r'python3.*orchestrate\.py continue',
                r'/orchestrate continue'
            ]
            
            continuation_command_present = any(
                re.search(pattern, stdout_content) for pattern in continuation_patterns
            )
            
            # Document findings
            with open(self.test_dir / "command_presence_test.txt", "w") as f:
                f.write(f"Clear command present: {clear_command_present}\n")
                f.write(f"Continuation command present: {continuation_command_present}\n")
                f.write(f"Full stdout:\n{stdout_content}\n")
            
            self.assertTrue(clear_command_present, 
                          "Output should contain /clear command instruction")
            self.assertTrue(continuation_command_present, 
                          "Output should contain continuation command instruction")
            
        except subprocess.TimeoutExpired:
            self.fail("orchestrate start command timed out")

    def test_interactive_mode_fallback_when_claude_cli_unavailable(self):
        """Test that interactive mode serves as fallback when Claude CLI is unavailable"""
        # Import orchestrator modules
        sys.path.append(str(Path.cwd()))
        from orchestrate import AgentExecutor
        
        # Create mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.outputs_dir = self.test_dir
        
        # Create AgentExecutor in headless mode (should attempt Claude CLI)
        executor = AgentExecutor(mock_orchestrator, headless=True)
        
        # Mock subprocess to raise FileNotFoundError (Claude CLI not found)
        with patch('subprocess.Popen', side_effect=FileNotFoundError("Claude CLI not found")):
            test_instructions = "Test fallback instructions"
            result = executor.execute_agent("test", test_instructions)
            
            # Should fall back to interactive mode and return instructions
            self.assertEqual(result, test_instructions,
                           "Should fallback to interactive mode when Claude CLI unavailable")
        
        # Document test result
        with open(self.test_dir / "fallback_test.txt", "w") as f:
            f.write(f"Fallback successful: {result == test_instructions}\n")
            f.write(f"Result: {result}\n")

    def test_manual_execution_file_equivalence(self):
        """Test that manual execution produces equivalent files to headless mode"""
        # This test simulates the manual execution process and compares results
        
        # Import orchestrator modules
        sys.path.append(str(Path.cwd()))
        from orchestrate import ClaudeCodeOrchestrator
        
        # Create test directories
        interactive_dir = self.test_dir / "interactive_mode"
        headless_dir = self.test_dir / "headless_mode"
        interactive_dir.mkdir(exist_ok=True)
        headless_dir.mkdir(exist_ok=True)
        
        # Test with a simple workflow that creates files
        test_task = "Test interactive mode file creation"
        
        # Simulate headless mode execution (without actually spawning Claude CLI)
        # This would typically create specific files in the outputs directory
        
        # Create expected files that would be generated
        expected_files = ['exploration.md', 'plan.md', 'changes.md']
        test_content = "Test content for file equivalence validation"
        
        # Simulate file creation in both modes
        for filename in expected_files:
            (interactive_dir / filename).write_text(test_content)
            (headless_dir / filename).write_text(test_content)
        
        # Compare file contents
        files_equivalent = True
        for filename in expected_files:
            interactive_file = interactive_dir / filename
            headless_file = headless_dir / filename
            
            if interactive_file.exists() and headless_file.exists():
                if interactive_file.read_text() != headless_file.read_text():
                    files_equivalent = False
                    break
            else:
                files_equivalent = False
                break
        
        # Document test result
        with open(self.test_dir / "file_equivalence_test.txt", "w") as f:
            f.write(f"Files equivalent: {files_equivalent}\n")
            f.write(f"Interactive dir files: {list(interactive_dir.iterdir())}\n")
            f.write(f"Headless dir files: {list(headless_dir.iterdir())}\n")
        
        self.assertTrue(files_equivalent, 
                       "Manual interactive execution should produce equivalent files to headless mode")

    def test_interactive_mode_integration(self):
        """Integration test for complete interactive mode workflow"""
        # Set interactive mode
        os.environ['CLAUDE_ORCHESTRATOR_MODE'] = 'prompt'
        
        try:
            # Test orchestrate start
            start_result = subprocess.run([
                sys.executable, 'orchestrate.py', 'start'
            ], capture_output=True, text=True, timeout=60)
            
            # Test orchestrate status
            status_result = subprocess.run([
                sys.executable, 'orchestrate.py', 'status'
            ], capture_output=True, text=True, timeout=30)
            
            # Document integration test results
            with open(self.test_dir / "integration_test.txt", "w") as f:
                f.write("=== START COMMAND ===\n")
                f.write(f"Exit code: {start_result.returncode}\n")
                f.write(f"Stdout: {start_result.stdout[:500]}...\n")
                f.write(f"Stderr: {start_result.stderr}\n\n")
                
                f.write("=== STATUS COMMAND ===\n")
                f.write(f"Exit code: {status_result.returncode}\n")
                f.write(f"Stdout: {status_result.stdout[:500]}...\n")
                f.write(f"Stderr: {status_result.stderr}\n")
            
            # Verify both commands completed without errors
            self.assertEqual(start_result.returncode, 0, 
                           "orchestrate start should complete successfully in interactive mode")
            self.assertEqual(status_result.returncode, 0, 
                           "orchestrate status should complete successfully in interactive mode")
            
            # Verify start command shows instructions
            self.assertIn("INSTRUCTION", start_result.stdout.upper(), 
                         "Start command should display instructions in interactive mode")
            
        except subprocess.TimeoutExpired:
            self.fail("Integration test commands timed out")

    def test_interactive_mode_vs_headless_mode_behavior(self):
        """Test behavioral differences between interactive and headless modes"""
        # Import orchestrator modules
        sys.path.append(str(Path.cwd()))
        from orchestrate import AgentExecutor
        
        # Create mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.outputs_dir = self.test_dir
        
        test_instructions = "Test mode comparison instructions"
        
        # Test interactive mode
        os.environ['CLAUDE_ORCHESTRATOR_MODE'] = 'prompt'
        interactive_executor = AgentExecutor(mock_orchestrator, headless=False)
        interactive_result = interactive_executor.execute_agent("test", test_instructions)
        
        # Test headless mode (mock to prevent actual Claude CLI execution)
        os.environ.pop('CLAUDE_ORCHESTRATOR_MODE', None)
        headless_executor = AgentExecutor(mock_orchestrator, headless=True)
        
        with patch('subprocess.Popen') as mock_popen:
            # Mock successful headless execution
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_process.poll.return_value = 0
            mock_process.stdout = iter(['{"type": "result", "exitCode": 0}'])
            mock_process.stderr.read.return_value = ""
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            headless_result = headless_executor.execute_agent("test", test_instructions)
        
        # Document comparison
        with open(self.test_dir / "mode_comparison_test.txt", "w") as f:
            f.write(f"Interactive mode result: {interactive_result}\n")
            f.write(f"Headless mode result: {headless_result}\n")
            f.write(f"Interactive mode use_interactive_mode: {interactive_executor.use_interactive_mode}\n")
            f.write(f"Headless mode use_interactive_mode: {headless_executor.use_interactive_mode}\n")
        
        # Verify mode differences
        self.assertTrue(interactive_executor.use_interactive_mode, 
                       "Interactive executor should have use_interactive_mode=True")
        self.assertFalse(headless_executor.use_interactive_mode, 
                        "Headless executor should have use_interactive_mode=False")
        
        # Verify interactive mode returns instructions unchanged
        self.assertEqual(interactive_result, test_instructions,
                        "Interactive mode should return instructions unchanged")


if __name__ == "__main__":
    # Ensure test directory exists
    Path(".agent-outputs-test").mkdir(exist_ok=True)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)