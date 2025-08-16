# Claude Code Orchestrator Dashboard

A visual web interface for monitoring the Claude Code Orchestrator workflow progress.

## Overview

The dashboard provides a real-time visualization of the orchestration workflow, showing the current state of each agent and the overall progress through the workflow phases:

**Explorer** → **Criteria Gate** → **Planner** → **Coder** → **Scribe** → **Verifier** → **Completion Gate**

## Features

### Visual Workflow Timeline
- Interactive timeline showing all workflow phases
- Color-coded status indicators:
  - **Gray**: Pending (not started)
  - **Blue**: In Progress (currently active)
  - **Green**: Completed
  - **Orange**: Gates (human decision points)
- Progress connectors between phases
- Animated pulse effect for active phases

### Agent Status Cards
- Individual cards for each agent (Explorer, Planner, Coder, Scribe, Verifier)
- Status badges showing current state
- Detailed descriptions of each agent's responsibilities
- Hover effects and visual feedback

### Mode Switching
- Toggle between Regular mode (`.agent-outputs/`) and Meta mode (`.agent-outputs-meta/`)
- Visual indicator of current mode
- Separate state tracking for each mode

### Responsive Design
- Mobile-friendly layout
- Tablet and desktop optimizations
- Adaptive grid system
- Touch-friendly controls

## Usage

### Opening the Dashboard

1. **Local File Access**:
   ```bash
   # Open directly in browser
   open dashboard.html
   # or
   xdg-open dashboard.html  # Linux
   # or double-click the file in file explorer
   ```

2. **Web Server** (optional for enhanced features):
   ```bash
   # Python 3
   python -m http.server 8000
   # Then visit http://localhost:8000/dashboard.html
   
   # Node.js (if you have npx)
   npx serve .
   ```

### Interface Controls

#### Mode Switcher
- **Toggle Switch** (top-right): Switch between Regular and Meta modes
- **Regular Mode**: Shows standard orchestration workflow
- **Meta Mode**: Shows meta-orchestration workflow (used for development)

#### Action Buttons
- **Refresh Status**: Updates the display with current workflow state
- **Simulate Progress**: Demonstrates workflow progression (for testing)

### Status Indicators

#### Workflow Timeline Icons
- 🔍 **Explorer**: Task analysis and exploration
- 🚪 **Criteria Gate**: Human review of success criteria
- 📋 **Planner**: Implementation planning
- 💻 **Coder**: Code implementation
- 📝 **Scribe**: Documentation creation
- ✅ **Verifier**: Testing and verification
- 🏁 **Completion Gate**: Final approval

#### Agent Status Badges
- **PENDING**: Agent has not started
- **IN PROGRESS**: Agent is currently active
- **COMPLETED**: Agent has finished successfully

## Technical Details

### File Integration (Simulated)

The dashboard simulates reading from orchestrator state files:

```
.agent-outputs/              # Regular mode
├── current-status.md        # Current workflow state
├── exploration.md           # Explorer findings
├── plan.md                  # Implementation plan
├── changes.md               # Code changes made
├── documentation.md         # Generated documentation
└── verification.md          # Test results

.agent-outputs-meta/         # Meta mode
├── current-status.md        # Meta workflow state
└── [same files as above]    # Meta-mode outputs
```

### Browser Compatibility

Tested and compatible with:
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

### Auto-Refresh

The dashboard automatically refreshes status every 30 seconds to stay current with workflow changes.

## Integration with Orchestrator

### Current Status Format

The dashboard reads and displays information in the format used by `current-status.md`:

```markdown
# Orchestration Status

⏳ Explorer        pending
✅ Criteria Gate   completed
🔄 Planner         in_progress
⏳ Coder           pending
⏳ Verifier        pending
⏳ Completion Gate pending

Current task: Create dashboard HTML interface implementing the visual work
```

### State File Monitoring

In a production environment, the dashboard would:
1. Monitor `.agent-outputs/` and `.agent-outputs-meta/` directories
2. Parse markdown status files automatically
3. Update display when files change
4. Handle missing or malformed files gracefully

## Customization

### Styling
All styles are embedded in the HTML file. Key CSS variables for customization:

```css
/* Color scheme */
--primary-color: #3498db;
--success-color: #27ae60;
--warning-color: #f39c12;
--pending-color: #95a5a6;

/* Layout */
--container-max-width: 1200px;
--border-radius: 12px;
--card-padding: 25px;
```

### Mock Data Structure
The JavaScript includes configurable mock data:

```javascript
const mockStatusData = {
    regular: {
        currentTask: "Task description",
        workflow: [/* workflow phases */],
        agents: [/* agent details */]
    },
    meta: {
        // Meta-mode data structure
    }
};
```

## Troubleshooting

### Common Issues

1. **File not loading**: Ensure the HTML file is in the project root directory
2. **Styles not applying**: Check that the file wasn't truncated during creation
3. **JavaScript errors**: Open browser developer tools (F12) to check console
4. **Mode switching not working**: Verify JavaScript is enabled in browser

### Browser Developer Tools

Use F12 to access developer tools:
- **Console**: Check for JavaScript errors
- **Network**: Verify file loading (if using web server)
- **Elements**: Inspect HTML structure and styles

## Future Enhancements

Potential improvements for production use:
- Real file system integration
- WebSocket connection for live updates
- Configuration file support
- Export/print functionality
- Historical workflow data
- Performance metrics
- Agent execution logs