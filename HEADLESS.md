# Headless Mode Documentation

## Overview

Headless mode is an experimental feature that enables automated orchestration execution without manual intervention. While interactive mode is currently the default, headless mode will eventually become the default execution mode once stabilized.

## Why Headless Mode Will Replace Interactive Mode

### Context Isolation Benefits

The primary advantage of headless mode is **context isolation**. Each agent in headless mode starts with a fresh Claude Code conversation context, preventing the context accumulation issues that plague interactive mode:

- **Interactive Mode Problem**: Conversation history grows continuously, leading to performance degradation and potential token limit issues over long sessions
- **Headless Mode Solution**: Each agent execution uses `claude -p` with a fresh context, ensuring consistent performance throughout the workflow

### Technical Architecture

Headless mode achieves context isolation by:
1. Spawning separate Claude Code processes for each agent
2. Using file-based communication between agents (`.agent-outputs/` directory)
3. Avoiding conversation history accumulation that occurs in interactive mode
4. Providing predictable execution performance regardless of workflow length

## Current Status and Limitations

### Experimental Nature

Headless mode is currently experimental with the following known limitations:

#### 5+ Minute Opacity Issue

The most significant current limitation is the **5+ minute opacity period** during agent execution:
- When an agent runs in headless mode, there is no visible progress indication
- The process appears to "hang" for 5+ minutes while Claude works
- No intermediate output or status updates are shown
- Users cannot see what the agent is doing until completion

This opacity makes it difficult to:
- Debug issues during agent execution
- Understand progress on long-running tasks
- Identify when agents encounter problems
- Provide meaningful feedback during development

### Other Current Limitations

- Error handling and debugging are more difficult
- Less visibility into agent decision-making process
- Requires more robust error recovery mechanisms
- Not suitable for tasks requiring human oversight during execution

## Environment Configuration

### Using Environment Variables

Set the execution mode using the `CLAUDE_ORCHESTRATOR_MODE` environment variable:

```bash
# Use interactive mode (current default)
export CLAUDE_ORCHESTRATOR_MODE=interactive

# Use headless mode
export CLAUDE_ORCHESTRATOR_MODE=headless
```

### Command-Line Flags

Override environment settings using command-line flags:

```bash
# Force headless mode regardless of environment variable
/orchestrate start --headless

# Use default mode (respects environment variable)
/orchestrate start
```

## Enabling and Testing Headless Mode

### Step 1: Environment Setup

Create a test project or use an existing one:

```bash
# In your project directory
echo 'export CLAUDE_ORCHESTRATOR_MODE=headless' > .orchestrator.env
```

### Step 2: Start Headless Workflow

```bash
/orchestrate start --headless
```

### Step 3: Monitor Execution

Since headless mode has the opacity issue, you'll need to:
- Wait patiently during the 5+ minute execution periods
- Check `.agent-outputs/` directory for progress files
- Use `/orchestrate status` to check workflow state

### Step 4: Handle Gate Decisions

Headless mode will still pause at decision gates:
```
🚪 CRITERIA GATE: Human Review Required
• /orchestrate approve-criteria
• /orchestrate modify-criteria "your changes"
• /orchestrate retry-explorer
```

Make decisions using the standard gate commands.

## Testing Checklist

When testing headless mode:

- [ ] Verify `CLAUDE_ORCHESTRATOR_MODE` environment variable is respected
- [ ] Confirm `--headless` flag overrides environment settings
- [ ] Test complete workflow execution from start to finish
- [ ] Verify gate decisions work correctly
- [ ] Check that agent output files are created properly
- [ ] Confirm error handling doesn't break workflow
- [ ] Test meta-mode isolation (`/morchestrate` commands)

## Roadmap for Default Mode Transition

### Phase 1: Stability (Current)
- [ ] Resolve the 5+ minute opacity issue
- [ ] Improve error handling and debugging
- [ ] Add progress indicators and status updates
- [ ] Enhance timeout and recovery mechanisms

### Phase 2: Feature Parity
- [ ] Ensure all interactive mode features work in headless
- [ ] Add comprehensive logging and diagnostics
- [ ] Implement proper signal handling
- [ ] Add graceful shutdown capabilities

### Phase 3: Default Transition
- [ ] Change default mode from interactive to headless
- [ ] Update documentation to reflect new default
- [ ] Provide migration guide for existing users
- [ ] Deprecate interactive mode (with continued support)

### Phase 4: Full Adoption
- [ ] Make headless mode the only supported mode
- [ ] Remove interactive mode code paths
- [ ] Optimize for headless-only architecture

## Troubleshooting

### Common Issues

**Agent appears to hang for 5+ minutes**
- This is expected behavior due to the opacity limitation
- Wait for completion or check `.agent-outputs/` for progress files

**Environment variable not respected**
- Verify the variable is exported: `echo $CLAUDE_ORCHESTRATOR_MODE`
- Check that your shell configuration loads the variable
- Try using the `--headless` flag as an override

**Workflow fails in headless but works in interactive**
- Check agent output files in `.agent-outputs/` for error messages
- Try running with `CLAUDE_ORCHESTRATOR_DEBUG=true` for more details
- Switch back to interactive mode for debugging: `unset CLAUDE_ORCHESTRATOR_MODE`

### Debug Mode

Enable debug output for troubleshooting:

```bash
export CLAUDE_ORCHESTRATOR_DEBUG=true
/orchestrate start --headless
```

This will provide additional diagnostic information during execution.

## Migration Timeline

**Current State**: Interactive mode default, headless experimental  
**Target State**: Headless mode default, interactive deprecated  
**Timeline**: TBD based on resolution of opacity and stability issues  

Users should begin testing headless mode in non-critical workflows to prepare for the eventual transition.