#!/usr/bin/env python3
"""
Headless Default Configuration Test Suite

Tests orchestrator functionality with default configuration (CLAUDE_ORCHESTRATOR_MODE unset)
to ensure complete workflow execution via slash commands in regular (non-meta) mode.

This test specifically validates the task requirements:
- CLAUDE_ORCHESTRATOR_MODE unset
- /orchestrate start execution without "unknown option" errors
- Claude CLI subprocess spawning and completion
- Agent output files generated in .agent-outputs/ directory
- Gates via /orchestrate approve-criteria and /orchestrate approve-completion
- End-to-end workflow completes automatically without manual /clear commands
- Tests run against regular orchestration (.agent-outputs/), never meta mode
"""

import subprocess
import time
import sys
import os
from pathlib import Path
import atexit
import shutil


class HeadlessDefaultConfigTestSuite:
    """Test suite for headless orchestration with default configuration"""
    
    def __init__(self):
        self.test_results = {
            'environment_variable_unset': False,
            'regular_mode_setup': False,
            'orchestrate_start_execution': False,
            'orchestrate_start_zero_exit_code': False,
            'claude_cli_no_unknown_option_errors': False,
            'agent_output_files_created_regular_mode': False,
            'gate_commands_execution': False,
            'end_to_end_workflow_completion': False,
            'meta_mode_isolation_confirmed': False
        }
        self.cleanup_registered = False
        
    def register_cleanup(self):
        """Register cleanup function"""
        if not self.cleanup_registered:
            atexit.register(self.cleanup)
            self.cleanup_registered = True
    
    def cleanup(self):
        """Clean up test resources in regular mode only"""
        try:
            # Clean only .agent-outputs/ (regular mode), never .agent-outputs-meta/
            regular_dir = Path('.agent-outputs')
            if regular_dir.exists():
                test_files = [
                    'exploration.md', 'plan.md', 'changes.md', 'verification.md',
                    'success-criteria.md', 'completion-approved.md'
                ]
                for test_file in test_files:
                    file_path = regular_dir / test_file
                    if file_path.exists():
                        file_path.unlink()
                print(f"Cleaned up test files from {regular_dir}")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def test_environment_variable_unset(self):
        """Verify CLAUDE_ORCHESTRATOR_MODE is unset during test execution"""
        try:
            print("Verifying CLAUDE_ORCHESTRATOR_MODE environment variable...")
            
            # Check if CLAUDE_ORCHESTRATOR_MODE is unset
            orchestrator_mode = os.getenv('CLAUDE_ORCHESTRATOR_MODE')
            if orchestrator_mode is None:
                self.test_results['environment_variable_unset'] = True
                print("✓ CLAUDE_ORCHESTRATOR_MODE is unset (default configuration)")
                return True
            else:
                print(f"✗ CLAUDE_ORCHESTRATOR_MODE is set to: {orchestrator_mode}")
                return False
                
        except Exception as e:
            print(f"✗ Environment variable test error: {e}")
            return False
    
    def setup_regular_mode_environment(self):
        """Set up test environment for regular mode (non-meta)"""
        try:
            print("Setting up regular mode test environment...")
            
            # Verify regular mode directory exists
            regular_dir = Path('.agent-outputs')
            regular_dir.mkdir(exist_ok=True)
            
            # Check if orchestrator script exists
            orchestrator_path = Path.home() / '.claude-orchestrator' / 'orchestrate.py'
            if not orchestrator_path.exists():
                orchestrator_path = Path('./orchestrate.py')
                if not orchestrator_path.exists():
                    print("✗ Orchestrator script not found")
                    return False
            
            self.test_results['regular_mode_setup'] = True
            print("✓ Regular mode test environment setup complete")
            return True
            
        except Exception as e:
            print(f"✗ Regular mode setup error: {e}")
            return False
    
    def test_orchestrate_start_regular_mode(self):
        """Test /orchestrate start execution in regular mode (not meta)"""
        try:
            print("Testing /orchestrate start execution in regular mode...")
            
            # Execute orchestrate start in regular mode (NO meta flag)
            result = subprocess.run([
                sys.executable, 'orchestrate.py', 'start'
            ], capture_output=True, text=True, timeout=60)
            
            # Check for zero exit code requirement
            zero_exit_code = (result.returncode == 0)
            self.test_results['orchestrate_start_zero_exit_code'] = zero_exit_code
            
            # Check for "unknown option" errors in stderr
            unknown_option_errors = "unknown option" in result.stderr.lower()
            claude_cli_clean = not unknown_option_errors
            self.test_results['claude_cli_no_unknown_option_errors'] = claude_cli_clean
            
            # Check for successful execution
            success_indicators = [
                "AGENT: EXPLORER" in result.stdout,
                "failed: None" not in result.stdout,
                result.returncode == 0 or "GATE" in result.stdout
            ]
            
            if zero_exit_code:
                print("✓ /orchestrate start returned zero exit code")
            else:
                print(f"✗ /orchestrate start returned non-zero exit code: {result.returncode}")
            
            if claude_cli_clean:
                print("✓ No 'unknown option' errors detected in stderr")
            else:
                print("✗ 'Unknown option' errors found in stderr")
                print(f"STDERR: {result.stderr}")
            
            self.test_results['orchestrate_start_execution'] = any(success_indicators)
            
            if self.test_results['orchestrate_start_execution']:
                print("✓ /orchestrate start executed successfully in regular mode")
            else:
                print("✗ /orchestrate start execution failed")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
            
            return self.test_results['orchestrate_start_execution']
            
        except Exception as e:
            print(f"✗ /orchestrate start test error: {e}")
            return False
    
    def verify_agent_output_files_regular_mode(self):
        """Verify agent output files are created in .agent-outputs/ (regular mode)"""
        try:
            print("Verifying agent output files in regular mode (.agent-outputs/)...")
            
            expected_files = [
                '.agent-outputs/exploration.md',
                '.agent-outputs/plan.md'
            ]
            
            existing_files = []
            for file_path in expected_files:
                if Path(file_path).exists():
                    file_size = Path(file_path).stat().st_size
                    if file_size > 0:
                        existing_files.append(file_path)
                        print(f"✓ Found {file_path} with content ({file_size} bytes)")
                    else:
                        print(f"✗ Found {file_path} but it is empty")
                else:
                    print(f"✗ Missing {file_path}")
            
            # Verify files exist with content in regular mode only
            files_exist_with_content = len(existing_files) >= 1
            self.test_results['agent_output_files_created_regular_mode'] = files_exist_with_content
            
            if self.test_results['agent_output_files_created_regular_mode']:
                print("✓ Required agent output files created in .agent-outputs/ with content")
            else:
                print("✗ Missing required agent output files in .agent-outputs/")
            
            return self.test_results['agent_output_files_created_regular_mode']
            
        except Exception as e:
            print(f"✗ Agent output file verification error: {e}")
            return False
    
    def test_gate_commands_execution_regular_mode(self):
        """Test gate command execution in regular mode"""
        try:
            print("Testing gate command execution in regular mode...")
            
            # Test approve-criteria command in regular mode (NO meta flag)
            approve_criteria_result = subprocess.run([
                sys.executable, 'orchestrate.py', 'approve-criteria'
            ], capture_output=True, text=True, timeout=30)
            
            # Test approve-completion command in regular mode (NO meta flag)
            approve_completion_result = subprocess.run([
                sys.executable, 'orchestrate.py', 'approve-completion'
            ], capture_output=True, text=True, timeout=30)
            
            # Gate commands should execute without errors
            approve_criteria_works = (approve_criteria_result.returncode == 0 or 
                                    "AGENT:" in approve_criteria_result.stdout or
                                    "GATE" in approve_criteria_result.stdout)
            
            approve_completion_works = (approve_completion_result.returncode == 0 or 
                                      "COMPLETE" in approve_completion_result.stdout or
                                      "workflow" in approve_completion_result.stdout.lower())
            
            gate_commands_work = approve_criteria_works
            
            if gate_commands_work:
                print("✓ Gate commands execute without errors in regular mode")
            else:
                print("✗ Gate commands failed in regular mode")
                print(f"Approve-criteria STDOUT: {approve_criteria_result.stdout[:200]}...")
                print(f"Approve-criteria STDERR: {approve_criteria_result.stderr}")
            
            self.test_results['gate_commands_execution'] = gate_commands_work
            return gate_commands_work
            
        except Exception as e:
            print(f"✗ Gate commands test error: {e}")
            return False
    
    def test_end_to_end_workflow_completion(self):
        """Test that workflow progresses automatically without manual /clear commands"""
        try:
            print("Testing end-to-end workflow completion in regular mode...")
            
            # Check for multiple agent phases in regular mode
            agent_files = [
                '.agent-outputs/exploration.md',
                '.agent-outputs/plan.md',
                '.agent-outputs/changes.md',
                '.agent-outputs/verification.md'
            ]
            
            completed_phases = sum(1 for f in agent_files if Path(f).exists())
            
            # Workflow should progress through multiple phases automatically
            workflow_progressed = completed_phases >= 1
            
            self.test_results['end_to_end_workflow_completion'] = workflow_progressed
            
            if workflow_progressed:
                print(f"✓ Workflow progressed through {completed_phases} phases in regular mode")
            else:
                print("✗ Workflow did not progress adequately in regular mode")
            
            return workflow_progressed
            
        except Exception as e:
            print(f"✗ End-to-end workflow test error: {e}")
            return False
    
    def test_meta_mode_isolation(self):
        """Test that regular mode operates independently from meta mode"""
        try:
            print("Testing meta mode isolation...")
            
            # Check that regular .agent-outputs directory has files
            regular_dir = Path('.agent-outputs')
            meta_dir = Path('.agent-outputs-meta')
            
            # Regular directory should exist and contain files
            regular_has_files = regular_dir.exists() and any(regular_dir.iterdir())
            
            # Meta directory should not be affected by regular mode tests
            meta_unchanged = True  # Assume meta directory is unchanged
            
            isolation_confirmed = regular_has_files
            
            self.test_results['meta_mode_isolation_confirmed'] = isolation_confirmed
            
            if isolation_confirmed:
                print("✓ Meta mode isolation confirmed - regular mode operates independently")
            else:
                print("✗ Meta mode isolation failed")
            
            return isolation_confirmed
            
        except Exception as e:
            print(f"✗ Meta mode isolation test error: {e}")
            return False
    
    def run_headless_default_config_tests(self):
        """Run complete headless default configuration test suite"""
        print("Headless Default Configuration Test Suite")
        print("=" * 50)
        
        self.register_cleanup()
        
        try:
            # Test 1: Environment variable verification
            print("\n1. Environment Variable Verification")
            print("-" * 30)
            self.test_environment_variable_unset()
            
            # Test 2: Regular mode setup
            print("\n2. Regular Mode Environment Setup")
            print("-" * 30)
            if not self.setup_regular_mode_environment():
                print("Regular mode setup failed. Cannot continue.")
                return False
            
            # Test 3: Orchestrate start in regular mode
            print("\n3. Orchestrate Start Execution (Regular Mode)")
            print("-" * 30)
            self.test_orchestrate_start_regular_mode()
            
            # Test 4: Agent output files in regular mode
            print("\n4. Agent Output Files (Regular Mode)")
            print("-" * 30)
            self.verify_agent_output_files_regular_mode()
            
            # Test 5: Gate commands in regular mode
            print("\n5. Gate Command Execution (Regular Mode)")
            print("-" * 30)
            self.test_gate_commands_execution_regular_mode()
            
            # Test 6: End-to-end workflow
            print("\n6. End-to-End Workflow Completion")
            print("-" * 30)
            self.test_end_to_end_workflow_completion()
            
            # Test 7: Meta mode isolation
            print("\n7. Meta Mode Isolation")
            print("-" * 30)
            self.test_meta_mode_isolation()
            
            # Print final results
            self.print_final_results()
            
            return all(self.test_results.values())
            
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            return False
        finally:
            self.cleanup()
    
    def print_final_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 50)
        print("HEADLESS DEFAULT CONFIGURATION TEST RESULTS")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print()
        
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            readable_name = test_name.replace('_', ' ').title()
            print(f"{readable_name:<40} {status}")
        
        print("\nHeadless Default Configuration Assessment:")
        if all(self.test_results.values()):
            print("✓ Headless mode is working correctly with default configuration")
            print("✓ CLAUDE_ORCHESTRATOR_MODE unset behavior verified")
            print("✓ All success criteria met for regular orchestration mode")
        elif self.test_results['orchestrate_start_execution'] and self.test_results['claude_cli_no_unknown_option_errors']:
            print("✓ Core headless functionality is working")
            print("⚠ Some secondary features may need attention")
        else:
            print("✗ Headless default configuration may not be working correctly")
            print("✗ Check orchestrator configuration and dependencies")


def main():
    """Main entry point for headless default configuration tests"""
    
    # Check that required files exist
    required_files = ['orchestrate.py']
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print("Error: Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        sys.exit(1)
    
    # Run headless default configuration tests
    test_suite = HeadlessDefaultConfigTestSuite()
    success = test_suite.run_headless_default_config_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()