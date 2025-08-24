#!/usr/bin/env python3
"""
VSCode Port Forwarding Test Script

Tests VSCode automatic port forwarding functionality for port 5678.
Verifies that ports are accessible and cross-port communication works.
"""

import requests
import socket
import time
import sys
import subprocess
import threading
from pathlib import Path


class PortForwardingTester:
    """Test suite for VSCode port forwarding functionality"""
    
    def __init__(self):
        self.results = {
            'port_5678_accessible': False,
            'port_8000_accessible': False,
            'dashboard_loads': False,
            'api_connectivity': False,
            'cross_port_communication': False
        }
        self.errors = []
    
    def test_port_accessibility(self, port, timeout=5):
        """Test if a port is accessible via HTTP"""
        try:
            response = requests.get(f'http://localhost:{port}', timeout=timeout)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            self.errors.append(f"Port {port} accessibility test failed: {e}")
            return False
    
    def test_port_listening(self, port):
        """Test if a port is listening/bound"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception as e:
            self.errors.append(f"Port {port} listening test failed: {e}")
            return False
    
    def test_dashboard_content(self):
        """Test if dashboard content loads properly"""
        try:
            # Test main dashboard path
            response = requests.get('http://localhost:5678/dashboard.html', timeout=10)
            if response.status_code == 200:
                content = response.text
                # Check for key dashboard elements
                required_elements = [
                    'Claude Code Orchestrator',
                    'Workflow Progress',
                    'Agent Details',
                    'workflow-timeline'
                ]
                
                missing_elements = [elem for elem in required_elements if elem not in content]
                if missing_elements:
                    self.errors.append(f"Dashboard missing elements: {missing_elements}")
                    return False
                return True
            else:
                self.errors.append(f"Dashboard returned status code: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.errors.append(f"Dashboard content test failed: {e}")
            return False
    
    def test_api_endpoint(self):
        """Test if API server on port 8000 is accessible"""
        try:
            response = requests.get('http://localhost:8000/api/status', timeout=10)
            if response.status_code == 200:
                # Try to parse JSON response
                data = response.json()
                return 'currentTask' in data or 'workflow' in data
            else:
                self.errors.append(f"API endpoint returned status code: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.errors.append(f"API endpoint test failed: {e}")
            return False
        except ValueError as e:
            self.errors.append(f"API response JSON parsing failed: {e}")
            return False
    
    def test_cross_port_communication(self):
        """Test communication between dashboard (5678) and API (8000)"""
        try:
            # This simulates what the dashboard JavaScript would do
            # Test if we can make requests from 5678 context to 8000
            
            # First verify both ports are accessible
            if not self.test_port_listening(5678):
                self.errors.append("Port 5678 not listening for cross-port test")
                return False
                
            if not self.test_port_listening(8000):
                self.errors.append("Port 8000 not listening for cross-port test")
                return False
            
            # Test API call that dashboard would make
            response = requests.get('http://localhost:8000/api/status?mode=regular', timeout=10)
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            self.errors.append(f"Cross-port communication test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("Starting VSCode Port Forwarding Tests")
        print("=" * 50)
        
        # Test 1: Port 5678 accessibility
        print("Testing port 5678 accessibility...")
        self.results['port_5678_accessible'] = self.test_port_accessibility(5678)
        print(f"✓ Port 5678 accessible: {self.results['port_5678_accessible']}")
        
        # Test 2: Port 8000 accessibility  
        print("Testing port 8000 accessibility...")
        self.results['port_8000_accessible'] = self.test_port_accessibility(8000)
        print(f"✓ Port 8000 accessible: {self.results['port_8000_accessible']}")
        
        # Test 3: Dashboard content loading
        if self.results['port_5678_accessible']:
            print("Testing dashboard content loading...")
            self.results['dashboard_loads'] = self.test_dashboard_content()
            print(f"✓ Dashboard loads: {self.results['dashboard_loads']}")
        else:
            print("⚠ Skipping dashboard content test (port 5678 not accessible)")
        
        # Test 4: API connectivity
        if self.results['port_8000_accessible']:
            print("Testing API connectivity...")
            self.results['api_connectivity'] = self.test_api_endpoint()
            print(f"✓ API connectivity: {self.results['api_connectivity']}")
        else:
            print("⚠ Skipping API connectivity test (port 8000 not accessible)")
        
        # Test 5: Cross-port communication
        print("Testing cross-port communication...")
        self.results['cross_port_communication'] = self.test_cross_port_communication()
        print(f"✓ Cross-port communication: {self.results['cross_port_communication']}")
        
        # Print results summary
        self.print_results()
        
        return all(self.results.values())
    
    def print_results(self):
        """Print detailed test results"""
        print("\n" + "=" * 50)
        print("TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.results.values() if result)
        total = len(self.results)
        
        print(f"Tests passed: {passed}/{total}")
        print()
        
        for test_name, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{test_name:<30} {status}")
        
        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        print("\nVSCode Port Forwarding Status:")
        if self.results['port_5678_accessible'] and self.results['port_8000_accessible']:
            print("✓ VSCode appears to be forwarding ports correctly")
        else:
            print("✗ VSCode port forwarding may not be working")
            print("  Check that you're running in a VSCode remote environment")
            print("  and that ports 5678 and 8000 have active servers")


def main():
    """Main entry point for port forwarding tests"""
    
    # Check if we're likely in a VSCode environment
    vscode_indicators = [
        'VSCODE_IPC_HOOK_CLI',
        'TERM_PROGRAM', 
        'VSCODE_GIT_ASKPASS_MAIN'
    ]
    
    vscode_detected = any(indicator in os.environ for indicator in vscode_indicators)
    if not vscode_detected:
        print("Warning: VSCode environment not detected")
        print("This test is designed for VSCode remote development environments")
        print("Results may not be accurate in other environments")
        print()
    
    # Run the test suite
    tester = PortForwardingTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    import os
    main()