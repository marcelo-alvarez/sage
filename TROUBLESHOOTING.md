# Web UI Troubleshooting Guide

This guide addresses common issues with the Claude Orchestrator Web UI and their solutions.

## Server Startup Issues

### Port Conflicts

**Problem**: Default ports 5678 (dashboard) or 8000 (API) are already in use.

**Symptoms**:
- Error messages about port binding failures
- Dashboard or API server fails to start
- Log shows "Port X busy, using fallback port Y"

**Solution**: 
The orchestrator automatically resolves port conflicts by trying alternative ports:
- Dashboard server: Tries ports 5678-5698, then 6000-6020
- API server: Tries ports 8000-8020, then 9000-9020

**Manual Resolution**:
```bash
# Check what's using the ports
lsof -i :5678
lsof -i :8000

# Kill processes if safe to do so
kill -9 <PID>

# Or let the orchestrator use fallback ports (recommended)
cc-orchestrate serve
```

### Dashboard Server Not Starting

**Problem**: Dashboard server fails to start or takes too long to initialize.

**Symptoms**:
- Timeout waiting for dashboard server
- Browser fails to open dashboard
- "Dashboard server is not ready" messages

**Solution**:
```bash
# Check if dashboard_server.py exists in current directory
ls -la dashboard_server.py

# If missing, ensure you're in the correct project directory
pwd
cd /path/to/your/orchestrator/project

# Restart with verbose logging
cc-orchestrate serve
```

## API Server Issues

### API Server Unresponsive

**Problem**: API server becomes unresponsive during operation (most common issue).

**Symptoms**:
- Repeated "API server on port X is unresponsive" warnings every 30 seconds
- Dashboard shows "Connection Lost" indicator
- Gate controls and file viewer stop working

**Root Causes**:
1. **Single-threaded blocking**: Previous versions used blocking HTTP server
2. **File I/O bottlenecks**: Synchronous file reads block request processing
3. **Subprocess timeouts**: Long-running commands block the server thread

**Solutions**:
1. **Use Force Refresh**: Click the force refresh button (🔄) in the dashboard to reconnect
2. **Restart API Server**:
   ```bash
   # Stop all servers
   cc-orchestrate stop
   
   # Restart servers
   cc-orchestrate serve
   ```
3. **Check API Health**:
   ```bash
   curl http://localhost:8000/api/health
   ```

**Recent Improvements** (if using latest version):
- ThreadingHTTPServer for concurrent request handling
- Thread-safe file operations with timeouts
- Non-blocking subprocess execution
- 30-second request timeouts to prevent hanging

### Connection Timeouts

**Problem**: Dashboard shows connection errors or long loading times.

**Symptoms**:
- "Connection failed" messages
- Dashboard UI becomes unresponsive
- Network timeouts in browser console

**Solution**:
```bash
# Check if API server is running
curl -v http://localhost:8000/api/status

# Check server health
curl http://localhost:8000/api/health

# Restart if needed
cc-orchestrate stop
cc-orchestrate serve
```

## Browser Compatibility

### JavaScript Errors

**Problem**: Dashboard functionality doesn't work due to browser compatibility issues.

**Symptoms**:
- Buttons don't respond
- File viewer shows raw content instead of rendered markdown
- Auto-refresh stops working

**Solution**:
1. **Use Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
2. **Clear Browser Cache**:
   ```
   Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
   ```
3. **Check Browser Console**: Open Developer Tools (F12) for error messages
4. **Disable Extensions**: Try in incognito/private mode

### CSS/Font Loading Issues

**Problem**: Dashboard appears broken or uses wrong fonts.

**Symptoms**:
- Misaligned layout
- Missing custom fonts (CyberTechno, Space Mono)
- Broken typography

**Solution**:
1. **Check Network**: Ensure internet connection for Google Fonts
2. **Font Fallbacks**: Dashboard uses system fonts if custom fonts fail
3. **Hard Refresh**: Clear browser cache with Ctrl+Shift+F5

## File System Issues

### Agent Output Files Not Found

**Problem**: Dashboard shows "File not found" or empty content.

**Symptoms**:
- File viewer shows error messages
- Missing workflow status information
- Empty agent output displays

**Solution**:
```bash
# Check if .agent-outputs directory exists
ls -la .agent-outputs/

# Verify you're in the correct project directory
pwd

# Check file permissions
chmod 644 .agent-outputs/*.md

# Restart from correct directory
cd /path/to/your/project
cc-orchestrate serve
```

### Permission Errors

**Problem**: Server cannot read/write agent output files.

**Symptoms**:
- "Permission denied" errors in logs
- Unable to save gate decisions
- File viewer shows access errors

**Solution**:
```bash
# Fix permissions for agent output directory
chmod -R 755 .agent-outputs/
chmod -R 644 .agent-outputs/*.md

# Ensure proper ownership
chown -R $USER:$USER .agent-outputs/
```

## Performance Issues

### Slow File Loading

**Problem**: Large workflow files take too long to load in the file viewer.

**Symptoms**:
- Long delays when clicking file links
- Browser tab becomes unresponsive
- Timeout errors

**Solution**:
1. **File Size Limits**: Dashboard handles files up to ~10MB efficiently
2. **Browser Memory**: Close unnecessary tabs
3. **Network Issues**: Check local network connectivity

### High Memory Usage

**Problem**: Dashboard or server consumes excessive memory over time.

**Symptoms**:
- System slowdown during long sessions
- Browser tab crashes
- Server process killed by system

**Solution**:
```bash
# Restart servers to clear memory
cc-orchestrate stop
cc-orchestrate serve

# Monitor memory usage
ps aux | grep -E "(api_server|dashboard_server|orchestrate)"
```

## Meta Mode Issues

### Process Isolation Problems

**Problem**: Meta mode commands interfere with regular mode operations.

**Symptoms**:
- Commands affect wrong workflow files
- Process manager confusion
- Mixed .agent-outputs and .agent-outputs-meta content

**Solution**:
```bash
# Use correct meta mode commands
cc-morchestrate serve    # Not cc-orchestrate serve

# Check process separation
cc-orchestrate stop      # Stops only regular mode
cc-morchestrate stop     # Stops only meta mode

# Verify correct directories
ls -la .agent-outputs-meta/  # Meta mode files
ls -la .agent-outputs/       # Regular mode files
```

## Health Monitoring

### Understanding Health Checks

**Health Check Frequency**: Every 30 seconds
**Timeout**: 5 seconds per check
**Endpoints Checked**:
- Dashboard: `http://localhost:5678/`
- API: `http://localhost:8000/api/status`

**Log Interpretation**:
- `INFO` messages: Normal operation
- `WARNING` messages: Server unresponsive (retry in 30s)
- `ERROR` messages: Critical issues requiring restart

### Manual Health Verification

```bash
# Test dashboard health
curl -f http://localhost:5678/health

# Test API health
curl -f http://localhost:8000/api/health

# Test full API status
curl -f http://localhost:8000/api/status
```

## Getting Additional Help

### Log File Locations

Check these log files for detailed error information:
- `orchestrator-serve.log` - Server startup and health monitoring
- `api-server.log` - API server request/response logs
- `dashboard-server.log` - Dashboard server logs

### Useful Commands

```bash
# Check all orchestrator processes
ps aux | grep orchestrate

# Kill all orchestrator processes
cc-orchestrate stop
cc-morchestrate stop

# Start with verbose logging
cc-orchestrate serve

# Test connectivity
curl -v http://localhost:5678/dashboard.html
curl -v http://localhost:8000/api/status
```

### Report Issues

If problems persist:
1. Check log files for specific error messages
2. Note your operating system and browser versions
3. Include steps to reproduce the issue
4. Verify you're using the latest version of the orchestrator