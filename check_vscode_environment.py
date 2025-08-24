#!/usr/bin/env python3
"""
VSCode Environment Detection Script

Detects VSCode remote development environment and checks port forwarding
capabilities and configuration.
"""

import os
import sys
import socket
import subprocess
import json
from pathlib import Path


class VSCodeEnvironmentChecker:
    """Detect and analyze VSCode remote development environment"""
    
    def __init__(self):
        self.environment_info = {
            'vscode_detected': False,
            'environment_type': 'unknown',
            'port_forwarding_available': False,
            'environment_variables': {},
            'network_info': {}
        }
    
    def detect_vscode_environment(self):
        """Detect if running in VSCode and what type of environment"""
        
        # Check environment variables that indicate VSCode
        vscode_indicators = {
            'VSCODE_IPC_HOOK_CLI': 'VSCode CLI integration',
            'TERM_PROGRAM': 'Terminal program (vscode expected)',
            'VSCODE_GIT_ASKPASS_MAIN': 'VSCode Git integration',
            'VSCODE_GIT_IPC_HANDLE': 'VSCode Git IPC',
            'CODESPACES': 'GitHub Codespaces',
            'REMOTE_CONTAINERS': 'VSCode Remote Containers',
            'SSH_CLIENT': 'SSH connection (possible VSCode SSH)',
            'VSCODE_REMOTE_USER': 'VSCode remote user'
        }
        
        detected_indicators = {}
        for var, description in vscode_indicators.items():
            if var in os.environ:
                detected_indicators[var] = {
                    'value': os.environ[var],
                    'description': description
                }
        
        self.environment_info['environment_variables'] = detected_indicators
        self.environment_info['vscode_detected'] = len(detected_indicators) > 0
        
        # Determine environment type
        if 'CODESPACES' in detected_indicators:
            self.environment_info['environment_type'] = 'github_codespaces'
        elif 'REMOTE_CONTAINERS' in detected_indicators:
            self.environment_info['environment_type'] = 'vscode_remote_containers'
        elif 'SSH_CLIENT' in detected_indicators:
            self.environment_info['environment_type'] = 'vscode_ssh_remote'
        elif any('VSCODE' in var for var in detected_indicators):
            self.environment_info['environment_type'] = 'vscode_remote'
        else:
            self.environment_info['environment_type'] = 'local_or_unknown'
    
    def check_port_forwarding_capability(self):
        """Check if port forwarding is available and working"""
        
        # Test if we can bind to test ports
        test_ports = [5678, 8000, 9999]  # Include a random port for testing
        port_status = {}
        
        for port in test_ports:
            try:
                # Try to bind to the port briefly
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('localhost', port))
                    port_status[port] = 'available'
            except OSError as e:
                if "Address already in use" in str(e):
                    port_status[port] = 'in_use'
                else:
                    port_status[port] = f'error: {e}'
        
        self.environment_info['network_info']['port_status'] = port_status
        
        # Check if we can access localhost
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                sock.connect(('localhost', 80))  # Try a common port
                localhost_accessible = True
        except:
            localhost_accessible = False
        
        self.environment_info['network_info']['localhost_accessible'] = localhost_accessible
        
        # Port forwarding is likely available if we're in a VSCode remote environment
        # and can access localhost
        self.environment_info['port_forwarding_available'] = (
            self.environment_info['vscode_detected'] and 
            localhost_accessible and
            self.environment_info['environment_type'] != 'local_or_unknown'
        )
    
    def check_vscode_settings(self):
        """Check for VSCode port forwarding related settings"""
        
        # Look for VSCode settings that might affect port forwarding
        settings_paths = [
            Path.home() / '.vscode-server' / 'data' / 'User' / 'settings.json',
            Path.home() / '.vscode' / 'settings.json',
            Path.cwd() / '.vscode' / 'settings.json'
        ]
        
        vscode_settings = {}
        
        for settings_path in settings_paths:
            if settings_path.exists():
                try:
                    with open(settings_path, 'r') as f:
                        settings = json.load(f)
                        # Look for port forwarding related settings
                        forwarding_settings = {
                            key: value for key, value in settings.items()
                            if 'port' in key.lower() or 'forward' in key.lower() or 'remote' in key.lower()
                        }
                        if forwarding_settings:
                            vscode_settings[str(settings_path)] = forwarding_settings
                except (json.JSONDecodeError, PermissionError):
                    pass
        
        self.environment_info['vscode_settings'] = vscode_settings
    
    def get_network_configuration(self):
        """Get network configuration information"""
        
        network_config = {}
        
        # Get hostname
        try:
            network_config['hostname'] = socket.gethostname()
        except:
            network_config['hostname'] = 'unknown'
        
        # Get IP addresses
        try:
            hostname = socket.gethostname()
            network_config['ip_addresses'] = socket.gethostbyname_ex(hostname)[2]
        except:
            network_config['ip_addresses'] = []
        
        # Check if common forwarding ports are in use
        common_ports = [22, 80, 443, 3000, 5000, 5678, 8000, 8080, 9000]
        port_usage = {}
        
        for port in common_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    port_usage[port] = 'listening' if result == 0 else 'available'
            except:
                port_usage[port] = 'unknown'
        
        network_config['port_usage'] = port_usage
        self.environment_info['network_info'].update(network_config)
    
    def run_full_check(self):
        """Run complete environment check"""
        print("VSCode Environment Detection")
        print("=" * 50)
        
        # Detect VSCode environment
        self.detect_vscode_environment()
        
        # Check port forwarding capability
        self.check_port_forwarding_capability()
        
        # Check VSCode settings
        self.check_vscode_settings()
        
        # Get network configuration
        self.get_network_configuration()
        
        return self.environment_info
    
    def print_results(self):
        """Print formatted results of environment check"""
        
        print(f"VSCode Detected: {self.environment_info['vscode_detected']}")
        print(f"Environment Type: {self.environment_info['environment_type']}")
        print(f"Port Forwarding Available: {self.environment_info['port_forwarding_available']}")
        print()
        
        # Environment variables
        if self.environment_info['environment_variables']:
            print("VSCode Environment Variables:")
            for var, info in self.environment_info['environment_variables'].items():
                print(f"  {var}: {info['value'][:50]}... ({info['description']})")
            print()
        
        # Network information
        print("Network Information:")
        network = self.environment_info['network_info']
        print(f"  Hostname: {network.get('hostname', 'unknown')}")
        print(f"  Localhost accessible: {network.get('localhost_accessible', 'unknown')}")
        
        if 'port_usage' in network:
            print("  Port Usage (common ports):")
            for port, status in network['port_usage'].items():
                if status == 'listening':
                    print(f"    Port {port}: {status} ✓")
                elif port in [5678, 8000]:  # Highlight our target ports
                    print(f"    Port {port}: {status}")
        
        # VSCode settings
        if self.environment_info.get('vscode_settings'):
            print("\nVSCode Port Forwarding Settings:")
            for path, settings in self.environment_info['vscode_settings'].items():
                print(f"  {path}:")
                for key, value in settings.items():
                    print(f"    {key}: {value}")
        
        # Recommendations
        print("\nRecommendations:")
        if not self.environment_info['vscode_detected']:
            print("  - This doesn't appear to be a VSCode remote environment")
            print("  - Port forwarding tests may not work as expected")
        elif not self.environment_info['port_forwarding_available']:
            print("  - Port forwarding may not be properly configured")
            print("  - Check VSCode remote development setup")
        else:
            print("  - Environment looks good for port forwarding tests")
            print("  - You can proceed with running the port forwarding tests")


def main():
    """Main entry point for environment check"""
    
    checker = VSCodeEnvironmentChecker()
    checker.run_full_check()
    checker.print_results()
    
    # Return appropriate exit code
    sys.exit(0 if checker.environment_info['port_forwarding_available'] else 1)


if __name__ == "__main__":
    main()