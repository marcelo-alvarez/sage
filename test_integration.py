#!/usr/bin/env python3
"""
Integration Test Suite for VSCode Port Forwarding

Comprehensive end-to-end test that validates complete dashboard functionality
with VSCode port forwarding. Starts both servers and tests the full workflow.
"""

import subprocess
import time
import signal
import sys
import threading
import requests
from pathlib import Path
import atexit


class IntegrationTestSuite:
    """Complete integration test for VSCode port forwarding"""
    
    def __init__(self):
        self.dashboard_process = None
        self.api_process = None
        self.test_results = {
            'environment_check': False,
            'dashboard_server_start': False,
            'api_server_start': False,
            'port_forwarding_test': False,
            'end_to_end_communication': False
        }
        self.cleanup_registered = False
    
    def register_cleanup(self):
        """Register cleanup function to stop servers on exit"""
        if not self.cleanup_registered:
            atexit.register(self.cleanup)
            self.cleanup_registered = True
    
    def cleanup(self):
        """Stop all running servers"""
        if self.dashboard_process:
            try:
                self.dashboard_process.terminate()
                self.dashboard_process.wait(timeout=5)
            except:
                try:
                    self.dashboard_process.kill()
                except:
                    pass
            self.dashboard_process = None
        
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
            except:
                try:
                    self.api_process.kill()
                except:
                    pass
            self.api_process = None
    
    def check_environment(self):
        """Check if environment is suitable for testing"""
        try:
            # Run environment check script
            result = subprocess.run([
                sys.executable, 'check_vscode_environment.py'
            ], capture_output=True, text=True, timeout=30)
            
            self.test_results['environment_check'] = result.returncode == 0
            
            if result.returncode == 0:
                print("✓ Environment check passed")
            else:
                print("✗ Environment check failed")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
            
            return self.test_results['environment_check']
            
        except Exception as e:
            print(f"✗ Environment check error: {e}")
            return False
    
    def start_dashboard_server(self, port=5678):
        """Start the dashboard server in background"""
        try:
            print(f"Starting dashboard server on port {port}...")
            
            self.dashboard_process = subprocess.Popen([
                sys.executable, 'test_dashboard_server.py', str(port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if process is still running
            if self.dashboard_process.poll() is None:
                # Test if port is accessible
                try:
                    response = requests.get(f'http://localhost:{port}', timeout=10)
                    self.test_results['dashboard_server_start'] = response.status_code in [200, 302]
                    print(f"✓ Dashboard server started successfully")
                except requests.RequestException:
                    print("✗ Dashboard server started but not accessible")
                    self.test_results['dashboard_server_start'] = False
            else:
                print("✗ Dashboard server failed to start")
                self.test_results['dashboard_server_start'] = False
                # Print error output
                stdout, stderr = self.dashboard_process.communicate()
                if stderr:
                    print("Error:", stderr)
            
            return self.test_results['dashboard_server_start']
            
        except Exception as e:
            print(f"✗ Dashboard server start error: {e}")
            return False
    
    def start_api_server(self, port=8000):
        """Start the API server in background"""
        try:
            print(f"Starting API server on port {port}...")
            
            # Import and start the API server
            self.api_process = subprocess.Popen([
                sys.executable, 'api_server.py', '--port', str(port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if process is still running
            if self.api_process.poll() is None:
                # Test if API endpoint is accessible
                try:
                    response = requests.get(f'http://localhost:{port}/api/status', timeout=10)
                    self.test_results['api_server_start'] = response.status_code == 200
                    print(f"✓ API server started successfully")
                except requests.RequestException:
                    print("✗ API server started but not accessible")
                    self.test_results['api_server_start'] = False
            else:
                print("✗ API server failed to start")
                self.test_results['api_server_start'] = False
                # Print error output
                stdout, stderr = self.api_process.communicate()
                if stderr:
                    print("Error:", stderr)
            
            return self.test_results['api_server_start']
            
        except Exception as e:
            print(f"✗ API server start error: {e}")
            return False
    
    def test_port_forwarding(self):
        """Test port forwarding functionality"""
        try:
            print("Testing port forwarding...")
            
            # Run port forwarding test script
            result = subprocess.run([
                sys.executable, 'test_port_forwarding.py'
            ], capture_output=True, text=True, timeout=60)
            
            self.test_results['port_forwarding_test'] = result.returncode == 0
            
            if result.returncode == 0:
                print("✓ Port forwarding tests passed")
            else:
                print("✗ Port forwarding tests failed")
                print("STDOUT:", result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
            
            return self.test_results['port_forwarding_test']
            
        except Exception as e:
            print(f"✗ Port forwarding test error: {e}")
            return False
    
    def test_end_to_end_communication(self):
        """Test complete end-to-end communication workflow"""
        try:
            print("Testing end-to-end communication...")
            
            # Test 1: Dashboard serves content
            dashboard_response = requests.get('http://localhost:5678/dashboard.html', timeout=10)
            dashboard_ok = dashboard_response.status_code == 200
            
            # Test 2: API serves status
            api_response = requests.get('http://localhost:8000/api/status', timeout=10)
            api_ok = api_response.status_code == 200
            
            # Test 3: Cross-port communication (simulate dashboard calling API)
            cross_port_response = requests.get('http://localhost:8000/api/status?mode=regular', timeout=10)
            cross_port_ok = cross_port_response.status_code == 200
            
            # Test 4: Verify dashboard content includes expected elements
            content_ok = False
            if dashboard_ok:
                content = dashboard_response.text
                required_elements = [
                    'Claude Code Orchestrator',
                    'workflow-timeline',
                    'agents-grid',
                    'http://localhost:8000/api/status'  # Check API endpoint reference
                ]
                content_ok = all(element in content for element in required_elements)
            
            self.test_results['end_to_end_communication'] = all([
                dashboard_ok, api_ok, cross_port_ok, content_ok
            ])
            
            print(f"  Dashboard content: {'✓' if dashboard_ok else '✗'}")
            print(f"  API endpoint: {'✓' if api_ok else '✗'}")
            print(f"  Cross-port communication: {'✓' if cross_port_ok else '✗'}")
            print(f"  Dashboard content validation: {'✓' if content_ok else '✗'}")
            
            if self.test_results['end_to_end_communication']:
                print("✓ End-to-end communication test passed")
            else:
                print("✗ End-to-end communication test failed")
            
            return self.test_results['end_to_end_communication']
            
        except Exception as e:
            print(f"✗ End-to-end communication test error: {e}")
            return False
    
    def run_integration_tests(self):
        """Run complete integration test suite"""
        print("VSCode Port Forwarding Integration Test Suite")
        print("=" * 60)
        
        self.register_cleanup()
        
        try:
            # Step 1: Check environment
            print("\n1. Environment Check")
            print("-" * 30)
            if not self.check_environment():
                print("Environment check failed. Continuing with limited testing...")
            
            # Step 2: Start dashboard server
            print("\n2. Dashboard Server")
            print("-" * 30)
            if not self.start_dashboard_server():
                print("Cannot continue without dashboard server")
                return False
            
            # Step 3: Start API server
            print("\n3. API Server")
            print("-" * 30)
            if not self.start_api_server():
                print("Cannot continue without API server")
                return False
            
            # Step 4: Test port forwarding
            print("\n4. Port Forwarding Tests")
            print("-" * 30)
            self.test_port_forwarding()
            
            # Step 5: End-to-end communication
            print("\n5. End-to-End Communication")
            print("-" * 30)
            self.test_end_to_end_communication()
            
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
        print("\n" + "=" * 60)
        print("INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print()
        
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            readable_name = test_name.replace('_', ' ').title()
            print(f"{readable_name:<30} {status}")
        
        print("\nVSCode Port Forwarding Assessment:")
        if all(self.test_results.values()):
            print("✓ VSCode port forwarding is working correctly")
            print("✓ Dashboard and API servers can communicate properly")
            print("✓ All integration tests passed")
        elif self.test_results['port_forwarding_test'] and self.test_results['end_to_end_communication']:
            print("✓ Core port forwarding functionality is working")
            print("⚠ Some environment checks failed but basic functionality works")
        else:
            print("✗ VSCode port forwarding may not be working correctly")
            print("✗ Check VSCode remote development setup")
            print("✗ Ensure you're running in a supported remote environment")


def main():
    """Main entry point for integration tests"""
    
    # Check that required files exist
    required_files = [
        'test_dashboard_server.py',
        'test_port_forwarding.py', 
        'check_vscode_environment.py',
        'dashboard.html',
        'api_server.py'
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print("Error: Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        sys.exit(1)
    
    # Run integration tests
    test_suite = IntegrationTestSuite()
    success = test_suite.run_integration_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()