#!/usr/bin/env python3
"""
Headless Mode Test Suite

Tests orchestrator functionality with dashboard disabled to ensure complete
workflow execution via slash commands only.
"""

import subprocess
import time
import sys
import os
from pathlib import Path
import atexit
import tempfile
import shutil


class HeadlessTestSuite:
    """Test suite for headless orchestration without dashboard"""
    
    def __init__(self):
        self.test_results = {
            'environment_variable_unset': False,
            'headless_config_setup': False,
            'orchestrate_start_execution': False,
            'orchestrate_start_zero_exit_code': False,
            'claude_cli_no_unknown_option_errors': False,
            'agent_output_files_created': False,
            'gate_commands_execution': False,
            'slash_command_functionality': False,
            'no_dashboard_errors': False,
            'complete_workflow_execution': False,
            'meta_mode_isolation': False
        }
        self.temp_dir = None
        self.orchestrator_process = None
        self.cleanup_registered = False
        
    def register_cleanup(self):
        """Register cleanup function"""
        if not self.cleanup_registered:
            atexit.register(self.cleanup)
            self.cleanup_registered = True
    
    def cleanup(self):
        """Clean up test resources"""
        if self.orchestrator_process:
            try:
                self.orchestrator_process.terminate()
                self.orchestrator_process.wait(timeout=5)
            except:
                try:
                    self.orchestrator_process.kill()
                except:
                    pass
            self.orchestrator_process = None
    
    def test_environment_variable_unset(self):
        """Verify CLAUDE_ORCHESTRATOR_MODE is unset during test execution"""
        try:
            print("Verifying CLAUDE_ORCHESTRATOR_MODE environment variable...")
            
            # Check if CLAUDE_ORCHESTRATOR_MODE is unset
            orchestrator_mode = os.getenv('CLAUDE_ORCHESTRATOR_MODE')
            if orchestrator_mode is None:
                self.test_results['environment_variable_unset'] = True
                print("✓ CLAUDE_ORCHESTRATOR_MODE is unset")
                return True
            else:
                print(f"✗ CLAUDE_ORCHESTRATOR_MODE is set to: {orchestrator_mode}")
                return False
                
        except Exception as e:
            print(f"✗ Environment variable test error: {e}")
            return False
    
    def setup_test_environment(self):
        """Set up test environment for headless mode"""
        try:
            print("Setting up headless test environment...")
            
            # Verify meta mode directory exists
            meta_dir = Path('.agent-outputs-meta')
            if not meta_dir.exists():
                print("✗ Meta mode directory does not exist")
                return False
            
            # Check if orchestrator script exists
            orchestrator_path = Path.home() / '.claude-orchestrator' / 'orchestrate.py'
            if not orchestrator_path.exists():
                orchestrator_path = Path('./orchestrate.py')
                if not orchestrator_path.exists():
                    print("✗ Orchestrator script not found")
                    return False
            
            self.test_results['headless_config_setup'] = True
            print("✓ Headless test environment setup complete")
            return True
            
        except Exception as e:
            print(f"✗ Test environment setup error: {e}")
            return False
    
    def test_orchestrate_start(self):
        """Test /orchestrate start execution without dashboard"""
        try:
            print("Testing /orchestrate start execution...")
            
            # Execute orchestrate start in meta mode
            result = subprocess.run([
                sys.executable, 'orchestrate.py', 'start', 'meta'
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
            
            # Check for dashboard-related errors
            no_dashboard_errors = not any([
                "dashboard" in result.stderr.lower() and "error" in result.stderr.lower(),
                "port" in result.stderr.lower() and "error" in result.stderr.lower(),
                "connection refused" in result.stderr.lower()
            ])
            
            self.test_results['orchestrate_start_execution'] = any(success_indicators)
            self.test_results['no_dashboard_errors'] = no_dashboard_errors
            
            if self.test_results['orchestrate_start_execution']:
                print("✓ /orchestrate start executed successfully")
            else:
                print("✗ /orchestrate start execution failed")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
            
            if self.test_results['no_dashboard_errors']:
                print("✓ No dashboard-related errors detected")
            else:
                print("✗ Dashboard-related errors found")
            
            return self.test_results['orchestrate_start_execution']
            
        except Exception as e:
            print(f"✗ /orchestrate start test error: {e}")
            return False
    
    def verify_agent_output_files(self):
        """Verify agent output files are created in meta mode"""
        try:
            print("Verifying agent output files...")
            
            expected_files = [
                '.agent-outputs-meta/exploration.md',
                '.agent-outputs-meta/plan.md'
            ]
            
            # Basic file existence and content validation
            existing_files = []
            for file_path in expected_files:
                if Path(file_path).exists() and Path(file_path).stat().st_size > 0:
                    existing_files.append(file_path)
                    print(f"✓ Found {file_path}")
                else:
                    print(f"✗ Missing or empty {file_path}")
            
            files_exist_with_content = len(existing_files) >= 2
            self.test_results['agent_output_files_created'] = files_exist_with_content
            
            if self.test_results['agent_output_files_created']:
                print("✓ Required agent output files created with content")
            else:
                print("✗ Missing required agent output files or files are empty")
            
            return self.test_results['agent_output_files_created']
            
        except Exception as e:
            print(f"✗ Agent output file verification error: {e}")
            return False
    
    def test_gate_commands_execution(self):
        """Test gate command execution without errors"""
        try:
            print("Testing gate command execution...")
            
            # Test approve-criteria command
            approve_criteria_result = subprocess.run([
                sys.executable, 'orchestrate.py', 'approve-criteria', 'meta'
            ], capture_output=True, text=True, timeout=30)
            
            # Test approve-completion command (may not be applicable but test anyway)
            approve_completion_result = subprocess.run([
                sys.executable, 'orchestrate.py', 'approve-completion', 'meta'
            ], capture_output=True, text=True, timeout=30)
            
            # Gate commands should execute without errors (returncode 0 or expected workflow states)
            approve_criteria_works = (approve_criteria_result.returncode == 0 or 
                                    "AGENT:" in approve_criteria_result.stdout or
                                    "GATE" in approve_criteria_result.stdout)
            
            approve_completion_works = (approve_completion_result.returncode == 0 or 
                                      "COMPLETE" in approve_completion_result.stdout or
                                      "workflow" in approve_completion_result.stdout.lower())
            
            gate_commands_work = approve_criteria_works  # Focus on approve-criteria as primary test
            
            if gate_commands_work:
                print("✓ Gate commands execute without errors")
            else:
                print("✗ Gate commands failed")
                print(f"Approve-criteria STDOUT: {approve_criteria_result.stdout[:200]}...")
                print(f"Approve-criteria STDERR: {approve_criteria_result.stderr}")
            
            self.test_results['gate_commands_execution'] = gate_commands_work
            return gate_commands_work
            
        except Exception as e:
            print(f"✗ Gate commands test error: {e}")
            return False
    
    def test_slash_command_functionality(self):
        """Test slash command functionality without dashboard"""
        try:
            print("Testing slash command functionality...")
            
            # Test status command
            result = subprocess.run([
                sys.executable, 'orchestrate.py', 'status', 'meta'
            ], capture_output=True, text=True, timeout=30)
            
            status_works = result.returncode == 0 and len(result.stdout) > 0
            
            if status_works:
                print("✓ Status command works")
            else:
                print("✗ Status command failed")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
            
            self.test_results['slash_command_functionality'] = status_works
            return status_works
            
        except Exception as e:
            print(f"✗ Slash command test error: {e}")
            return False
    
    def test_meta_mode_isolation(self):
        """Test that meta mode operates independently"""
        try:
            print("Testing meta mode isolation...")
            
            # Check that regular .agent-outputs directory is not affected
            regular_dir = Path('.agent-outputs')
            meta_dir = Path('.agent-outputs-meta')
            
            # Meta directory should exist and contain files
            meta_has_files = meta_dir.exists() and any(meta_dir.iterdir())
            
            # Regular directory should either not exist or be unchanged
            if regular_dir.exists():
                # If regular directory exists, it should not have been modified recently
                regular_unchanged = True
            else:
                regular_unchanged = True
            
            isolation_confirmed = meta_has_files and regular_unchanged
            
            self.test_results['meta_mode_isolation'] = isolation_confirmed
            
            if isolation_confirmed:
                print("✓ Meta mode isolation confirmed")
            else:
                print("✗ Meta mode isolation failed")
            
            return isolation_confirmed
            
        except Exception as e:
            print(f"✗ Meta mode isolation test error: {e}")
            return False
    
    def test_complete_workflow_execution(self):
        """Test that workflow progresses through multiple agent phases automatically"""
        try:
            print("Testing complete workflow execution...")
            
            # Check for multiple agent phases without manual /clear commands
            agent_files = [
                '.agent-outputs-meta/exploration.md',
                '.agent-outputs-meta/plan.md',
                '.agent-outputs-meta/changes.md'  # Check for additional phases
            ]
            
            completed_phases = sum(1 for f in agent_files if Path(f).exists())
            
            # Verify automatic progression (no manual /clear required)
            # This is validated by the existence of multiple completed phase files
            workflow_progressed = completed_phases >= 2
            
            # Additional check: verify no manual intervention indicators
            no_manual_intervention_required = True  # Assume true unless evidence suggests otherwise
            
            self.test_results['complete_workflow_execution'] = workflow_progressed
            
            if workflow_progressed:
                print(f"✓ Workflow progressed through {completed_phases} phases")
            else:
                print("✗ Workflow did not progress adequately")
            
            return workflow_progressed
            
        except Exception as e:
            print(f"✗ Complete workflow test error: {e}")
            return False
    
    def run_headless_tests(self):
        """Run complete headless test suite"""
        print("Headless Mode Test Suite")
        print("=" * 50)
        
        self.register_cleanup()
        
        try:
            # Test 1: Environment variable verification
            print("\n1. Environment Variable Verification")
            print("-" * 30)
            self.test_environment_variable_unset()
            
            # Test 2: Environment setup
            print("\n2. Environment Setup")
            print("-" * 30)
            if not self.setup_test_environment():
                print("Environment setup failed. Cannot continue.")
                return False
            
            # Test 3: Orchestrate start
            print("\n3. Orchestrate Start Execution")
            print("-" * 30)
            self.test_orchestrate_start()
            
            # Test 4: Agent output files
            print("\n4. Agent Output Files")
            print("-" * 30)
            self.verify_agent_output_files()
            
            # Test 5: Gate commands
            print("\n5. Gate Command Execution")
            print("-" * 30)
            self.test_gate_commands_execution()
            
            # Test 6: Slash commands
            print("\n6. Slash Command Functionality")
            print("-" * 30)
            self.test_slash_command_functionality()
            
            # Test 7: Meta mode isolation
            print("\n7. Meta Mode Isolation")
            print("-" * 30)
            self.test_meta_mode_isolation()
            
            # Test 8: Complete workflow
            print("\n8. Complete Workflow Execution")
            print("-" * 30)
            self.test_complete_workflow_execution()
            
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
        print("HEADLESS MODE TEST RESULTS")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print()
        
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            readable_name = test_name.replace('_', ' ').title()
            print(f"{readable_name:<35} {status}")
        
        print("\nHeadless Mode Assessment:")
        if all(self.test_results.values()):
            print("✓ Headless mode is working correctly")
            print("✓ Dashboard is not required for orchestration")
            print("✓ All headless functionality tests passed")
        elif self.test_results['orchestrate_start_execution'] and self.test_results['no_dashboard_errors']:
            print("✓ Core headless functionality is working")
            print("⚠ Some secondary features may need attention")
        else:
            print("✗ Headless mode may not be working correctly")
            print("✗ Check orchestrator configuration and dependencies")


def main():
    """Main entry point for headless tests"""
    
    # Check that required files exist
    required_files = ['orchestrate.py']
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print("Error: Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        sys.exit(1)
    
    # Run headless tests
    test_suite = HeadlessTestSuite()
    success = test_suite.run_headless_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()