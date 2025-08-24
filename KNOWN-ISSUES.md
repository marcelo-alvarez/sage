# Known Issues and Limitations

This document outlines current limitations and known issues in the Claude Orchestrator Web UI implementation.

## Architecture Limitations

### Polling vs. WebSocket Design

**Current Implementation**: 30-second HTTP polling for status updates
**Limitation**: Not real-time; changes may take up to 30 seconds to appear in the UI

**Design Decision Rationale**:
- Simplicity: Avoids WebSocket connection management complexity
- Reliability: HTTP polling is more resilient to network interruptions
- State Consistency: Reduces risk of UI state getting out of sync with file system
- Development Speed: Faster to implement and debug than WebSocket integration

**Impact**:
- Status updates have 30-second maximum latency
- Network traffic every 30 seconds even when idle
- Not suitable for real-time monitoring scenarios

**Future Enhancement**: WebSocket implementation planned for v3.0

### File System Dependency

**Current Implementation**: Direct file system reads for all content
**Limitation**: Performance degrades with large workflow files (>10MB)

**Impact**:
- Large markdown files (>5MB) may cause browser performance issues
- File viewer becomes sluggish with deeply nested project structures
- No file size warnings or progressive loading

**Workarounds**:
- Keep individual agent output files under 1MB when possible
- Break large documentation into separate sections
- Use markdown links instead of embedding large content blocks

### Thread Safety Considerations

**Status**: Partially addressed in recent versions
**Remaining Issues**:
- Concurrent file writes during workflow execution may cause brief read inconsistencies
- File locks not implemented for .agent-outputs directory
- Race conditions possible during rapid gate decision changes

**Impact**: 
- Occasional "file not found" errors during active workflow transitions
- Dashboard may briefly show stale data during file updates

## Web UI Specific Limitations

### Browser Compatibility

**Supported Browsers**:
- Chrome/Chromium 90+
- Firefox 88+  
- Safari 14+
- Edge 90+

**Known Issues**:
- **Internet Explorer**: Not supported (ES6+ features used)
- **Chrome 85-89**: Minor CSS grid layout issues in file viewer
- **Safari 13**: Custom font loading may fail on slow connections
- **Mobile Browsers**: Layout not optimized for mobile screens (responsive design incomplete)

### JavaScript Dependencies

**External Dependencies**:
- Markdown-it library (CDN-hosted)
- Lucide icons (CDN-hosted)
- Google Fonts (CDN-hosted)

**Offline Limitations**:
- No offline functionality when CDN resources are unavailable
- Markdown rendering falls back to plain text without markdown-it
- Icons display as text without Lucide library
- Typography degrades without custom font loading

### File Viewer Limitations

**Large File Handling**:
- Files >5MB may cause browser tab freezing
- No progressive loading or virtual scrolling
- Memory usage increases linearly with file size

**Content Type Support**:
- **Supported**: Markdown, plain text, JSON
- **Limited**: HTML (displayed as raw code, no rendering)
- **Unsupported**: Binary files, images, videos
- **Future Enhancement**: Syntax highlighting for code files planned

### Modal System Constraints

**File Viewer Modal**:
- Fixed width layout not ideal for very wide content
- No split-screen or side-by-side file comparison
- Scrolling performance issues with files >1000 lines

**Responsive Design**:
- Modal overlays not optimized for tablets (768px-1024px)
- Small screen layouts may truncate content
- Touch navigation not implemented

## Meta Mode Limitations

### Process Isolation Boundaries

**Current Implementation**: Separate .agent-outputs-meta/ directory and process tracking
**Limitations**:
- No prevention of accidental cross-mode file access
- Process manager doesn't enforce strict isolation
- Meta mode workflows can still affect global system state

**Edge Cases**:
- Running both regular and meta mode serves simultaneously may cause port conflicts
- File system permissions not isolated between modes
- Shared Python environment may cause module conflicts

### Visual Indicators

**Current Status**: Basic red background tint and banner for meta mode
**Limitations**:
- Minimal visual distinction between modes
- No modal warnings when switching between regular and meta mode interfaces
- Easy to accidentally operate in wrong mode

## Performance Characteristics

### Memory Usage

**Dashboard Client**:
- Base memory usage: ~50MB (Chrome)
- Scales linearly with file content loaded: +10MB per 1MB file
- No memory cleanup for closed file viewer modals

**API Server**:
- Single-threaded baseline: ~20MB
- ThreadingHTTPServer version: ~40MB
- Memory leaks possible with long-running sessions (>24 hours)

### Network Traffic

**Polling Overhead**:
- 1 request every 30 seconds to `/api/status` (~2KB response)
- Additional requests on user interaction (gate decisions, file views)
- No request batching or compression

**File Transfer**:
- Complete file content transferred on every view
- No client-side caching of agent output files
- Large files re-downloaded on every modal open

## Configuration Limitations

### Port Management

**Automatic Resolution**: Works well for development
**Production Limitations**:
- No configuration file for preferred port ranges
- No support for reverse proxy configuration
- No SSL/TLS support for HTTPS deployment

### Environment Variables

**Limited Configuration Options**:
- Only meta mode toggle via environment variable
- No debug logging level configuration
- No timeout customization for API requests

## Security Considerations

### Local Network Exposure

**Current Behavior**: Binds to localhost only
**Limitation**: Cannot easily share dashboard across network

**Security Implications**:
- No authentication system
- File system access not restricted
- All project files accessible via API endpoints
- No session management or user isolation

### File System Access

**Broad Access**: API server can read any file in project directory
**Security Boundary**: Limited to current working directory
**Risk**: Sensitive files in project directory are accessible via web interface

## Testing and Validation Gaps

### Automated Testing

**Current Coverage**:
- Basic functionality validation via test scripts
- No integration tests for concurrent usage
- No performance regression testing

**Missing Test Areas**:
- Browser compatibility testing across versions
- Load testing with large files
- Network resilience testing (connection drops, slow networks)
- Long-running session testing (memory leaks, stability)

### Error Recovery

**Limited Error Handling**:
- File read errors may cause complete UI failure
- API server crashes not automatically recovered
- No graceful degradation when external dependencies (CDN) fail

## Planned Improvements

### Short Term (Next Release)
- File size warnings before opening large files
- Better error messages for common failure scenarios
- Mobile-responsive layout improvements

### Medium Term (6 months)
- WebSocket implementation for real-time updates
- Client-side file caching
- Syntax highlighting for code files
- Configuration file support

### Long Term (1 year+)
- Authentication and authorization system
- Network deployment support with reverse proxy
- Offline functionality
- Multi-user collaboration features

## Workarounds and Best Practices

### Performance Optimization
- Keep agent output files under 1MB each
- Use markdown links instead of large embedded content
- Restart servers daily for long-running workflows

### Reliability Improvements
- Always run from project root directory
- Use meta mode for orchestrator development/testing
- Monitor log files for early warning of issues

### Development Workflow
- Test WebUI functionality after significant workflow changes
- Use headless mode for automated/CI workflows
- Keep separate terminals for server logs and command execution

---

*Last Updated: Version 2.0 - WebUI Branch*
*For technical support, refer to TROUBLESHOOTING.md*