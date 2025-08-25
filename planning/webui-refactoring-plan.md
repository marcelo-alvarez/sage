# Post-Merge Refactoring Plan (Revised)

## Current State Assessment

### What's Actually Working Well
- **Process Management**: PID tracking, clean shutdown, ProcessManager integration
- **Server Coordination**: Dashboard (5678) and API (8000) servers work together
- **Core Commands**: Start, Continue, Status, Clean execute via web UI
- **Gate Controls**: All three gate types (criteria, completion, user_validation) functional
- **File Viewer**: Removed in favor of log modals (cleaner architecture)
- **Mode Switching**: Regular vs meta mode with visual indicators
- **Error Recovery**: Basic retry logic and connection monitoring
- **Log Modals**: Agent reports and execution logs accessible via workflow icons
- **Server Logs**: Three-tab view for orchestrator-serve, api-server, dashboard-server logs
- **Health Monitoring**: 30-second health checks with status logging

### What's Partially Working (Needs Polish)
- **Mode-aware completion detection**: Works but meta mode path resolution needs consistency
- **Status synchronization**: Multiple status readers but generally functional
- **Connection recovery**: Auto-recovery attempts work but could be more robust
- **Gate state determination**: Logic works but scattered across multiple files

### What's Actually Broken
- **WebSocket implementation**: Not implemented (polling works adequately)
- **Session persistence**: State lost on browser refresh
- **Multi-user support**: Single user only (by design)
- **Emergency restart**: Sometimes leaves zombie processes

### Technical Debt (Acceptable for v1)
- **Performance**:
  - 30-second polling acceptable (< 100ms response time)
  - Full file reads on status checks (small files, negligible impact)
  - No caching (files small enough to not matter)

- **Code Organization**:
  - orchestrate.py: 2000+ lines but functional
  - dashboard.html: 1500+ lines inline JavaScript (works fine)
  - Duplicated status reading logic (StatusReader helps but not fully unified)
  - No unit tests (manual testing has been thorough)

## Critical Fixes Before Production

### Fix 1: Unified Status Reading
**Files**: `workflow_status.py`, `api_server.py`, `orchestrate.py`
**Issue**: Multiple implementations of status reading causing occasional inconsistencies
**Solution**: 
- StatusReader class exists and works - just ensure all components use it
- Pass project_root consistently to all status operations
**Test**: Status identical whether read by CLI, API, or dashboard

### Fix 2: Meta Mode Path Consistency
**Files**: `api_server.py`, `orchestrate.py`
**Issue**: `.agent-outputs` vs `.agent-outputs-meta` path resolution inconsistent
**Solution**:
- Centralize mode detection in StatusReader
- Use `_get_current_mode()` consistently
- Ensure all file operations respect mode flag
**Test**: Meta mode workflows complete without path errors

### Fix 3: Process Cleanup Reliability
**Files**: `process_manager.py`, `orchestrate.py`
**Issue**: Zombie processes occasionally survive restart/stop commands
**Solution**:
- ProcessManager already has robust cleanup - ensure it's used everywhere
- Add process group management for child processes
- Implement force-kill after graceful timeout
**Test**: No orphan processes after stop/restart commands

## Accepted Technical Debt (Won't Fix Now)

### Performance (Good Enough)
- Polling instead of WebSockets (works fine, low overhead)
- No caching layer (unnecessary for small files)
- Synchronous file operations (fast enough for current scale)

### Features (Not Critical)
- Session persistence (users can refresh status anytime)
- Multi-user support (designed as single-user tool)
- Keyboard shortcuts (nice-to-have)
- Dark mode toggle (already dark by default)
- File search/filter (only ~6 files to manage)

### Code Quality (Works But Messy)
- Large monolithic files (refactor only when adding features)
- Inline JavaScript (actually easier to maintain in one file)
- Global state in dashboard.html (acceptable for single-page app)
- Mixed responsibility in api_server.py (handles multiple endpoints fine)

## Future Improvements (Priority Order)

### Phase 1: State Management (First Sprint After Merge)
Create unified state management:
- Single source of truth for workflow state
- Centralized gate activation rules
- Consistent status updates across all components
- Estimated effort: 2-3 days

### Phase 2: Error Handling (Second Sprint)
Improve error recovery:
- Better connection retry logic
- Graceful degradation when servers unavailable
- User-friendly error messages
- Estimated effort: 2 days

### Phase 3: Testing (When Time Allows)
Add tests for critical paths only:
- Process lifecycle (start/stop/cleanup)
- Gate decision processing
- Mode isolation
- Status reading consistency
- Estimated effort: 3-4 days

### Phase 4: Code Organization (Refactor Opportunistically)
Only when modifying areas:
- Split orchestrate.py into logical modules (only if adding major features)
- Extract dashboard JavaScript (only if adding complex UI features)
- Create proper Python package structure (only for distribution)

## Success Metrics for Web UI v1.0

### Ship Blockers (Must Have)
- ✅ No orphan processes ever
- ✅ Gates work without terminal
- ✅ Status updates reflect reality
- ✅ Basic error recovery works
- ⚠️ Meta mode paths consistent (NEEDS FIX #2)
- ⚠️ Process cleanup reliable (NEEDS FIX #3)

### Good Enough (Ship With These)
- ✅ Visual mode indicators work
- ✅ Error messages display
- ✅ Manual refresh available
- ✅ Logs accessible via modals
- ✅ Health monitoring active
- ⚠️ Documentation minimal but sufficient

### Future Nice-to-Haves
- ❌ Real-time streaming (polling works fine)
- ❌ Session persistence (not critical)
- ❌ Full test coverage (manual testing sufficient)
- ❌ Perfect code structure (works as-is)
- ❌ WebSocket support (unnecessary complexity)

## Maintenance Strategy

### Fix Immediately (Blocks Usage)
- Process orphaning issues
- Mode isolation failures
- Data corruption between modes
- Complete failures to start/stop

### Fix Soon (Annoyances)
- Inconsistent status updates
- Slow connection recovery
- Unclear error messages
- Missing progress indicators

### Leave Alone (If It Works)
- Large file sizes
- Performance under 1 second
- Code duplication that works
- Polling mechanisms

### Refactor Only When Touched
- When fixing bugs in an area
- When adding new features
- When onboarding new developers
- When performance becomes an issue

## Implementation Timeline

### Week 1: Critical Fixes
- Day 1-2: Implement Fix #1 (Unified Status Reading)
- Day 3-4: Implement Fix #2 (Meta Mode Paths)
- Day 5: Implement Fix #3 (Process Cleanup)

### Week 2: Testing & Documentation
- Day 1-2: Test all fixes thoroughly
- Day 3: Update README with accurate information
- Day 4: Create minimal user guide
- Day 5: Final testing and merge

### Post-Merge (As Needed)
- Month 1: Gather user feedback
- Month 2: Implement Phase 1 improvements if issues arise
- Month 3+: Consider Phase 2-4 based on actual usage patterns

## Recommendation

**Ship the web UI after completing the three critical fixes:**

1. **Unified Status Reading** - Ensures consistency across all interfaces
2. **Meta Mode Path Consistency** - Prevents mode-specific failures  
3. **Process Cleanup Reliability** - Guarantees clean shutdowns

Everything else can be improved iteratively based on real user feedback. The current implementation is functional enough for v1.0 release once these fixes are complete.

## Code Snippets for Critical Fixes

### Fix 1: Unified Status Reading
```python
# In workflow_status.py
class StatusReader:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, project_root=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_workflow_status(self, mode='regular'):
        # Single implementation used everywhere
        pass
```

### Fix 2: Meta Mode Paths
```python
# In workflow_status.py
def get_outputs_dir(mode='regular'):
    """Centralized outputs directory resolution"""
    if mode == 'meta':
        return Path('.agent-outputs-meta')
    return Path('.agent-outputs')

def get_claude_dir(mode='regular'):
    """Centralized claude directory resolution"""
    if mode == 'meta':
        return Path('.claude-meta')
    return Path('.claude')
```

### Fix 3: Process Cleanup
```python
# In process_manager.py
def cleanup_with_timeout(self, process_name, timeout=5):
    """Graceful shutdown with force-kill fallback"""
    process = self.processes.get(process_name)
    if process:
        # Try graceful termination
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Force kill if still running
            process.kill()
            process.wait()
    return True
```