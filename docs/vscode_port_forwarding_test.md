# VSCode Port Forwarding Test Documentation

This document provides comprehensive instructions for testing VSCode automatic port forwarding functionality for the Claude Code Orchestrator dashboard.

## Overview

The Claude Code Orchestrator uses a two-port architecture:
- **Port 8000**: API server (backend)
- **Port 5678**: Dashboard (frontend)

When running in VSCode remote environments (Codespaces, SSH, Remote Containers), VSCode should automatically forward these ports to enable local browser access to the remote dashboard.

## Test Suite Components

### 1. Environment Check (`check_vscode_environment.py`)
Detects VSCode remote environment and verifies port forwarding capabilities.

**Purpose:**
- Identify VSCode remote development environment type
- Check network configuration and port availability
- Verify VSCode settings related to port forwarding

**Usage:**
```bash
python check_vscode_environment.py
```

### 2. Dashboard Server (`test_dashboard_server.py`)
Simple HTTP server that serves the dashboard on port 5678.

**Purpose:**
- Provide test server for port 5678
- Enable VSCode automatic port detection
- Serve dashboard.html with proper routing

**Usage:**
```bash
python test_dashboard_server.py [port]
```

### 3. Port Forwarding Tests (`test_port_forwarding.py`)
Automated test suite for port forwarding functionality.

**Purpose:**
- Test port accessibility through forwarding
- Verify cross-port communication
- Validate dashboard content loading

**Usage:**
```bash
python test_port_forwarding.py
```

### 4. Integration Test Suite (`test_integration.py`)
Complete end-to-end test that starts both servers and validates full workflow.

**Purpose:**
- Comprehensive testing of complete system
- Start both dashboard and API servers
- Test real-world usage scenarios

**Usage:**
```bash
python test_integration.py
```

## Quick Start Testing

### Prerequisites
- VSCode remote development environment (Codespaces, SSH, or Remote Containers)
- Python 3.x
- All test files in project root directory

### Simple Test
1. Run the integration test suite:
   ```bash
   python test_integration.py
   ```

2. The test will:
   - Check your environment
   - Start dashboard server on port 5678
   - Start API server on port 8000
   - Test port forwarding functionality
   - Report results

### Manual Verification
1. Start the dashboard server:
   ```bash
   python test_dashboard_server.py
   ```

2. Start the API server (in another terminal):
   ```bash
   python api_server.py
   ```

3. Check VSCode port forwarding:
   - Look for port forwarding notifications in VSCode
   - Check VSCode Ports panel (View → Command Palette → "Ports: Focus on Ports View")
   - Verify forwarded URLs are created

4. Test browser access:
   - Click the forwarded URL for port 5678 in VSCode
   - Verify dashboard loads in your local browser
   - Check that dashboard can communicate with API

## Expected VSCode Behavior

### Automatic Port Detection
VSCode should automatically detect when servers start on ports 5678 and 8000:
- Port forwarding notifications appear
- Ports are added to the Ports panel
- Forwarded URLs are generated

### Port Forwarding Panel
In VSCode, access via View → Command Palette → "Ports: Focus on Ports View":
- Port 5678: Should show "Running" status with forwarded URL
- Port 8000: Should show "Running" status with forwarded URL
- Both should be marked as "Auto Forward: On"

### Browser Access
Clicking forwarded URLs should:
- Open dashboard in local browser
- Display complete dashboard interface
- Enable functional API communication

## Test Environment Types

### GitHub Codespaces
- Port forwarding typically works automatically
- Forwarded URLs use codespaces domain
- Both public and private forwarding supported

### VSCode SSH Remote
- Requires SSH connection with port forwarding enabled
- Forwarded URLs use localhost with dynamic ports
- May require SSH key configuration

### VSCode Remote Containers
- Port forwarding works within container context
- Forwarded URLs use localhost
- Container must expose required ports

## Troubleshooting

### Common Issues

#### Port 5678 Not Forwarded
**Symptoms:**
- Dashboard server starts but URL not accessible
- VSCode doesn't show port in Ports panel

**Solutions:**
- Check if port is actually in use: `netstat -an | grep 5678`
- Manually add port forwarding in VSCode Ports panel
- Restart dashboard server
- Check VSCode port forwarding settings

#### Cross-Port Communication Fails
**Symptoms:**
- Dashboard loads but shows no data
- API calls fail in browser console

**Solutions:**
- Verify API server is running on port 8000
- Check that both ports are forwarded
- Verify CORS settings in browser
- Test API endpoint directly: `curl http://localhost:8000/api/status`

#### Environment Not Detected
**Symptoms:**
- Environment check fails
- Port forwarding tests show warnings

**Solutions:**
- Ensure you're in a VSCode remote environment
- Check VSCode remote development extension is installed
- Verify remote connection is active
- Restart VSCode if necessary

### Manual Port Forwarding
If automatic forwarding fails, manually add ports in VSCode:

1. Open Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
2. Search for "Ports: Forward a Port"
3. Add port 5678
4. Add port 8000
5. Set both to "Public" or "Private" as needed

### Network Configuration
For SSH remote development:
```bash
# Verify SSH port forwarding is enabled
ssh -L 5678:localhost:5678 -L 8000:localhost:8000 user@remote-host
```

## Test Results Interpretation

### Success Indicators
- ✅ All integration tests pass
- ✅ Both ports show as forwarded in VSCode
- ✅ Dashboard accessible via forwarded URL
- ✅ API communication works properly

### Partial Success
- ⚠️ Servers start but forwarding requires manual setup
- ⚠️ Environment detection fails but basic functionality works
- ⚠️ Some cross-port communication issues

### Failure Indicators
- ❌ Servers fail to start
- ❌ No port forwarding detected
- ❌ Dashboard not accessible
- ❌ API communication completely fails

## Performance Considerations

### Network Latency
- Remote connections may have higher latency
- Dashboard polling may be slower
- Consider adjusting timeout values in tests

### Resource Usage
- Test servers are lightweight
- Multiple test runs should not impact performance
- Clean up processes if tests are interrupted

## Security Notes

### Port Forwarding Security
- Forwarded ports may be accessible to others
- Use "Private" port forwarding when possible
- Be aware of network security policies
- Don't forward sensitive services unnecessarily

### Test Data
- Test servers serve static content only
- No sensitive data is transmitted
- API server uses mock data for testing

## Development and Debugging

### Adding Custom Tests
Create additional test scripts by following the pattern:
```python
import requests
import socket

def test_custom_functionality():
    # Test specific port forwarding behavior
    response = requests.get('http://localhost:5678/custom-endpoint')
    return response.status_code == 200

if __name__ == "__main__":
    success = test_custom_functionality()
    exit(0 if success else 1)
```

### Debugging Test Failures
1. Run environment check first: `python check_vscode_environment.py`
2. Check server logs for errors
3. Verify network connectivity: `telnet localhost 5678`
4. Test individual components before integration
5. Check VSCode output panel for port forwarding messages

## Automation Integration

### CI/CD Integration
Tests can be integrated into CI/CD pipelines that use VSCode remote environments:

```yaml
# Example GitHub Actions step
- name: Test VSCode Port Forwarding
  run: |
    python check_vscode_environment.py
    python test_integration.py
```

### Continuous Testing
Set up periodic testing in remote development environments:
```bash
#!/bin/bash
# run_periodic_tests.sh
while true; do
    python test_port_forwarding.py
    sleep 300  # Test every 5 minutes
done
```

## Support and Contributing

### Reporting Issues
When reporting port forwarding issues, include:
- Environment type (Codespaces, SSH, Remote Containers)
- VSCode version and remote development extension versions
- Output from `check_vscode_environment.py`
- Test results and error messages
- Network configuration details

### Contributing Tests
To contribute additional test scenarios:
1. Follow existing test patterns
2. Include comprehensive error handling
3. Add documentation for new test cases
4. Ensure compatibility across environment types