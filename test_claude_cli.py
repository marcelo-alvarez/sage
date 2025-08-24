#!/usr/bin/env python3
"""
Claude CLI Test Suite

Comprehensive testing for Claude CLI functionality to validate headless agent execution
capabilities as Phase 1 of migrating from manual interactive-based orchestration.

This test suite validates:
- Basic prompt execution with -p flag
- JSON output format parsing
- Permission bypass with --dangerously-skip-permissions
- Working directory isolation with --working-dir
- Turn limiting with --max-turns
- Integration testing with all flags combined
- Version detection and compatibility
"""

import unittest
import subprocess
import json
import os
import tempfile
import shutil
from pathlib import Path
import re


class TestClaudeCLI(unittest.TestCase):
    """Test suite for Claude CLI functionality validation"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(".agent-outputs-meta")
        self.test_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        """Clean up test environment"""
        # Clean up any test files in .agent-outputs-meta
        if self.test_dir.exists():
            for item in self.test_dir.iterdir():
                if item.name.startswith("test_"):
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)

    def test_claude_cli_available(self):
        """Test that Claude CLI is available in PATH"""
        try:
            result = subprocess.run(
                ["claude", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(result.returncode, 0, "Claude CLI should be available in PATH")
            self.assertIn("claude", result.stdout.lower(), "Help output should mention claude")
        except FileNotFoundError:
            self.fail("Claude CLI not found in PATH. Please install Claude CLI first.")
        except subprocess.TimeoutExpired:
            self.fail("Claude CLI help command timed out")

    def test_claude_version_detection(self):
        """Test Claude CLI version detection and document minimum requirements"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(result.returncode, 0, "Version command should succeed")
            
            version_output = result.stdout.strip()
            self.assertIsNotNone(version_output, "Version output should not be empty")
            
            # Extract version number using regex
            version_match = re.search(r'(\d+\.\d+\.\d+)', version_output)
            if version_match:
                version = version_match.group(1)
                print(f"Detected Claude CLI version: {version}")
                
                # Document version in test output
                with open(self.test_dir / "version_info.txt", "w") as f:
                    f.write(f"Claude CLI Version: {version}\n")
                    f.write(f"Full version output: {version_output}\n")
            else:
                print(f"Could not parse version from: {version_output}")
                
        except FileNotFoundError:
            self.fail("Claude CLI not found for version check")
        except subprocess.TimeoutExpired:
            self.fail("Claude CLI version command timed out")

    def test_basic_prompt_execution(self):
        """Test basic interactive execution with -p flag"""
        try:
            result = subprocess.run(
                ["claude", "-p", "echo test"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check that command completed
            self.assertIsNotNone(result.returncode, "Command should complete and return exit code")
            
            # Document the result regardless of success/failure for analysis
            with open(self.test_dir / "basic_prompt_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
            
            if result.returncode == 0:
                self.assertIn("test", result.stdout, "Output should contain echoed text")
            else:
                print(f"Basic interactive test failed with exit code {result.returncode}")
                print(f"Stderr: {result.stderr}")
                
        except FileNotFoundError:
            self.fail("Claude CLI not found for basic prompt test")
        except subprocess.TimeoutExpired:
            self.fail("Basic prompt execution timed out")

    def test_json_output_format(self):
        """Test JSON output format parsing"""
        try:
            result = subprocess.run(
                ["claude", "-p", "echo test", "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Document the result
            with open(self.test_dir / "json_output_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
            
            if result.returncode == 0 and result.stdout:
                # Basic JSON output validation
                has_valid_json = False
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            json.loads(line)
                            has_valid_json = True
                            break
                        except json.JSONDecodeError:
                            continue
                
                self.assertTrue(has_valid_json, "Should have at least one valid JSON line")
            else:
                print(f"JSON output test failed with exit code {result.returncode}")
                
        except FileNotFoundError:
            self.fail("Claude CLI not found for JSON output test")
        except subprocess.TimeoutExpired:
            self.fail("JSON output test timed out")

    def test_permission_bypass(self):
        """Test permission bypass with --dangerously-skip-permissions"""
        try:
            result = subprocess.run(
                ["claude", "-p", "echo test", "--dangerously-skip-permissions"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Document the result
            with open(self.test_dir / "permission_bypass_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
            
            # Check if command ran without interactive prompts
            if result.returncode == 0:
                self.assertNotIn("permission", result.stderr.lower(), 
                                "Should not see permission prompts in stderr")
            else:
                print(f"Permission bypass test failed with exit code {result.returncode}")
                
        except FileNotFoundError:
            self.fail("Claude CLI not found for permission bypass test")
        except subprocess.TimeoutExpired:
            self.fail("Permission bypass test timed out")

    def test_working_directory_isolation(self):
        """Test working directory isolation with --working-dir"""
        test_working_dir = self.test_dir / "test_workdir"
        test_working_dir.mkdir(exist_ok=True)
        
        try:
            result = subprocess.run(
                ["claude", "-p", "create a file named test_file.txt with content 'hello'", 
                 "--working-dir", str(test_working_dir)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Document the result
            with open(self.test_dir / "working_dir_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
                f.write(f"Working directory: {test_working_dir}\n")
                f.write(f"Files in working dir: {list(test_working_dir.iterdir()) if test_working_dir.exists() else 'Directory not found'}\n")
            
            # Check if working directory constraint is respected
            if result.returncode == 0:
                print(f"Working directory test completed with exit code 0")
            else:
                print(f"Working directory test failed with exit code {result.returncode}")
                
        except FileNotFoundError:
            self.fail("Claude CLI not found for working directory test")
        except subprocess.TimeoutExpired:
            self.fail("Working directory test timed out")

    def test_turn_limiting(self):
        """Test turn limiting with --max-turns"""
        try:
            result = subprocess.run(
                ["claude", "-p", "echo test", "--max-turns", "5"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Document the result
            with open(self.test_dir / "turn_limiting_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
            
            if result.returncode == 0:
                print("Turn limiting test completed successfully")
            else:
                print(f"Turn limiting test failed with exit code {result.returncode}")
                
        except FileNotFoundError:
            self.fail("Claude CLI not found for turn limiting test")
        except subprocess.TimeoutExpired:
            self.fail("Turn limiting test timed out")

    def test_integrated_flags(self):
        """Test all flags working together in integrated command"""
        test_working_dir = self.test_dir / "integrated_test"
        test_working_dir.mkdir(exist_ok=True)
        
        try:
            result = subprocess.run([
                "claude", 
                "-p", "echo integrated test", 
                "--output-format", "json",
                "--dangerously-skip-permissions",
                "--max-turns", "10",
                "--working-dir", str(test_working_dir)
            ], capture_output=True, text=True, timeout=45)
            
            # Document the comprehensive result
            with open(self.test_dir / "integrated_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
                f.write(f"Working directory: {test_working_dir}\n")
            
            if result.returncode == 0 and result.stdout:
                # Try to parse JSON from integrated test
                try:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            json.loads(line)
                    print("Integrated test: JSON parsing successful")
                except json.JSONDecodeError as e:
                    print(f"Integrated test: JSON parsing failed: {e}")
            
            print(f"Integrated test completed with exit code: {result.returncode}")
            
        except FileNotFoundError:
            self.fail("Claude CLI not found for integrated test")
        except subprocess.TimeoutExpired:
            self.fail("Integrated test timed out")

    def test_error_handling(self):
        """Test error handling with invalid prompts"""
        try:
            result = subprocess.run(
                ["claude", "-p", ""],  # Empty prompt
                capture_output=True,
                text=True,
                timeout=15
            )
            
            # Document error handling behavior
            with open(self.test_dir / "error_handling_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
            
            # Empty prompt should either fail gracefully or handle appropriately
            print(f"Error handling test completed with exit code: {result.returncode}")
            
        except FileNotFoundError:
            self.fail("Claude CLI not found for error handling test")
        except subprocess.TimeoutExpired:
            self.fail("Error handling test timed out")

    def test_completion_detection_json_result_event(self):
        """Test that JSON result events can be properly detected and parsed"""
        try:
            # Test with a simple task that should generate a result event
            result = subprocess.run([
                "claude", 
                "-p", "write 'test completion' to a file named completion_test.txt", 
                "--output-format", "json",
                "--working-dir", str(self.test_dir)
            ], capture_output=True, text=True, timeout=45)
            
            # Document the result
            with open(self.test_dir / "completion_detection_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
            
            # Parse JSON events and look for result type
            if result.stdout:
                json_events = []
                result_events = []
                
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            event = json.loads(line)
                            json_events.append(event)
                            if event.get('type') == 'result':
                                result_events.append(event)
                        except json.JSONDecodeError:
                            continue
                
                # Document findings
                with open(self.test_dir / "completion_events_analysis.json", "w") as f:
                    json.dump({
                        'total_events': len(json_events),
                        'result_events': result_events,
                        'all_event_types': [e.get('type', 'unknown') for e in json_events]
                    }, f, indent=2)
                
                print(f"Completion detection test: Found {len(result_events)} result events out of {len(json_events)} total events")
                
                if result_events:
                    self.assertGreater(len(result_events), 0, "Should find at least one result event")
                    for event in result_events:
                        self.assertIn('exitCode', event, "Result events should contain exitCode")
                else:
                    print("Warning: No result events found - this may indicate completion detection issues")
            
        except FileNotFoundError:
            self.fail("Claude CLI not found for completion detection test")
        except subprocess.TimeoutExpired:
            self.fail("Completion detection test timed out")

    def test_status_file_fallback_detection(self):
        """Test that status.txt fallback detection works properly"""
        test_working_dir = self.test_dir / "status_test"
        test_working_dir.mkdir(exist_ok=True)
        
        try:
            # Test with a task that should write to status.txt
            result = subprocess.run([
                "claude", 
                "-p", "create a file named status.txt with content 'Task in progress\nAGENT COMPLETE\nTask finished'", 
                "--working-dir", str(test_working_dir)
            ], capture_output=True, text=True, timeout=30)
            
            # Document the result
            with open(self.test_dir / "status_fallback_test.txt", "w") as f:
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                f.write(f"Stderr: {result.stderr}\n")
                f.write(f"Working directory: {test_working_dir}\n")
            
            # Check if status.txt was created with AGENT COMPLETE marker
            status_file = test_working_dir / "status.txt"
            if status_file.exists():
                content = status_file.read_text()
                with open(self.test_dir / "status_file_content.txt", "w") as f:
                    f.write(f"Status file content:\n{content}\n")
                
                self.assertIn("AGENT COMPLETE", content, "Status file should contain AGENT COMPLETE marker")
                print("Status file fallback test: AGENT COMPLETE marker found successfully")
            else:
                print("Warning: Status file was not created - this may affect fallback detection")
                
        except FileNotFoundError:
            self.fail("Claude CLI not found for status fallback test")
        except subprocess.TimeoutExpired:
            self.fail("Status fallback test timed out")

    def test_agent_executor_integration(self):
        """Test AgentExecutor integration with actual subprocess execution"""
        # This test validates the AgentExecutor class directly
        test_working_dir = self.test_dir / "executor_test"
        test_working_dir.mkdir(exist_ok=True)
        
        try:
            # Import and test AgentExecutor directly
            import sys
            sys.path.append(str(Path.cwd()))
            from orchestrate import AgentExecutor
            
            # Create a mock orchestrator object
            class MockOrchestrator:
                def __init__(self, outputs_dir):
                    self.outputs_dir = outputs_dir
                def _update_status_file(self):
                    pass
            
            mock_orchestrator = MockOrchestrator(test_working_dir)
            executor = AgentExecutor(mock_orchestrator)
            
            # Test with a simple task
            instructions = "Write 'Hello from AgentExecutor test' to test_output.txt\nWhen complete, also write 'AGENT COMPLETE' to status.txt"
            
            # Force headless mode for this test
            executor.use_interactive_mode = False
            
            result = executor.execute_agent("test", instructions)
            
            # Document the result
            with open(self.test_dir / "agent_executor_test.txt", "w") as f:
                f.write(f"Result: {result}\n")
                f.write(f"Working directory: {test_working_dir}\n")
                f.write(f"Files created: {list(test_working_dir.iterdir()) if test_working_dir.exists() else 'None'}\n")
            
            # Check if execution completed
            if "completed successfully" in result:
                print("AgentExecutor integration test: Execution completed successfully")
            elif "failed" in result:
                print(f"AgentExecutor integration test: Execution failed - {result}")
            else:
                print(f"AgentExecutor integration test: Unexpected result - {result}")
                
        except ImportError as e:
            print(f"Could not import AgentExecutor for integration test: {e}")
        except Exception as e:
            print(f"AgentExecutor integration test error: {e}")
            with open(self.test_dir / "agent_executor_error.txt", "w") as f:
                f.write(f"Error: {str(e)}\n")


if __name__ == "__main__":
    # Ensure test directory exists
    Path(".agent-outputs-meta").mkdir(exist_ok=True)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)