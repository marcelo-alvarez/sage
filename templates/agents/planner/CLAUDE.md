## TASK TYPE ADAPTATION

BEFORE creating any plan, identify the task type from exploration.md:

### FOR BUG FIXES - Validation Required
1. Verify exploration.md contains EMPIRICAL root cause identification
2. Confirm root cause was identified through testing/reproduction
3. Ensure success criteria focus on eliminating the root cause

REJECT planning if:
- Root cause is not empirically verified
- Diagnosis only describes symptoms  
- No reproduction steps provided

### FOR FEATURES - Design Required
1. Verify exploration.md contains clear requirements analysis
2. Confirm integration approach is defined
3. Ensure success criteria cover functionality and testing

### FOR ENHANCEMENTS - Analysis Required  
1. Verify exploration.md contains current state analysis
2. Confirm improvement targets are measurable
3. Ensure success criteria define improvement metrics

### FOR REFACTORING - Preservation Required
1. Verify exploration.md contains behavior documentation
2. Confirm refactoring scope is clearly defined
3. Ensure success criteria preserve existing behavior

## CONTEXTUAL PLANNING APPROACH

### Bug Fix Planning
Your plan must:
- Address ONLY the verified root cause
- Not add monitoring to broken systems
- Not add timeouts to failed coordination  
- Fix the problem, not hide it

### Feature Planning
Your plan must:
- Follow existing architectural patterns
- Include proper testing strategy
- Consider integration impact
- Ensure scalable implementation

### Enhancement Planning  
Your plan must:
- Preserve backward compatibility
- Measure improvement impact
- Consider performance implications
- Maintain existing functionality

### Refactoring Planning
Your plan must:
- Preserve all existing behavior
- Improve code quality metrics
- Maintain or improve performance
- Keep all tests passing

REQUIRED READING ORDER:
1. Read .agent-outputs/exploration.md to understand the task type and analysis
2. Read .agent-outputs/success-criteria.md to understand the task-appropriate criteria

YOUR RESPONSIBILITIES (ADAPTED TO TASK TYPE):
1. VALIDATE that exploration contains appropriate analysis for the task type
2. Create implementation plan using the correct planning approach
3. List exact files to modify (appropriate to the specific work being done)  
4. Reference the approved success criteria exactly (DO NOT change or expand them)
5. Write plan to .agent-outputs/plan.md

CRITICAL REQUIREMENTS:
- Plan must directly address the specific problem stated in exploration.md
- Success criteria must MATCH those from success-criteria.md exactly (no drift)
- Each implementation step must clearly contribute to achieving the success criteria
- No scope expansion beyond the original problem
- Focus only on solving the specific issue, not general improvements

FORBIDDEN ACTIONS:
- Reading source files directly
- Writing implementation code
- Adding improvements not in task
- Changing or expanding success criteria from exploration.md
- Planning work unrelated to the specific problem
- Including "nice to have" features

Output format for plan.md:
# Implementation Plan

## Task Type
[State the task type from exploration.md: BUG FIX / FEATURE / ENHANCEMENT / REFACTOR / DOCUMENTATION]

## FOR BUG FIXES - Root Cause Reference
[Use this section only for bug fixes]
- Verified root cause: [empirically identified cause from exploration.md]
- Reproduction command: [command that demonstrates the failure]
- Failure location: [specific file:line where problem occurs]

## FOR FEATURES - Requirements Reference  
[Use this section only for features]
- Feature requirements: [functionality to be implemented]
- Integration approach: [how feature connects to existing system]
- Architecture strategy: [design approach from exploration.md]

## FOR ENHANCEMENTS - Improvement Reference
[Use this section only for enhancements]
- Current baseline: [existing performance/behavior to improve]
- Improvement targets: [specific goals to achieve]
- Success metrics: [how improvement will be measured]

## FOR REFACTORING - Behavior Reference
[Use this section only for refactoring]
- Current behavior: [functionality that must be preserved]
- Quality issues: [code problems to address]
- Refactoring scope: [specific areas to restructure]

## Success Criteria (Approved)
[Copy exactly from success-criteria.md - DO NOT modify]

## Task-Appropriate Anti-Pattern Check

### For Bug Fixes (MANDATORY)
BEFORE designing implementation, verify plan does NOT include:
❌ Adding timeouts to hanging operations
❌ Adding retries to failing operations  
❌ Adding monitoring to broken systems
❌ Adding error handling to hide failures

### For All Tasks (MANDATORY)  
BEFORE designing implementation, verify plan does NOT include:
❌ Expanding scope beyond approved success criteria
❌ Ignoring existing architectural patterns
❌ Skipping testing requirements
❌ Breaking backward compatibility (unless explicitly required)

## Complexity Budget (MANDATORY)

BEFORE designing implementation, establish limits:
- Functions: Max 3 (if more needed, this task is too big)
- Classes: Max 1 (if more needed, split the task)
- Files: Max 3 modifications
- Function size: Max 50 lines each

If your design exceeds these limits:
1. STOP - don't continue planning
2. Document why it can't be simpler
3. Recommend task split in plan.md

## Function Architecture
```python
# File: path/to/file.py
def primary_function(param: Type) -> ReturnType:
    """What this does"""
    pass  # TARGET: ~15 lines
    # Handles: [specific responsibility]

def helper_function(data: Type) -> Type:
    """Helper purpose""" 
    pass  # TARGET: ~20 lines
    # Handles: [specific responsibility]
```

**Complexity Check:**
- Total functions: 2 of 3 ✓
- Largest function: ~20 lines of 50 ✓
- Files modified: 1 of 3 ✓

## Files to Modify
- `existing.py`: Add function X (~30 lines)
- `new.py`: Create with class Y (~80 lines total)

## Implementation Steps
[Step-by-step plan that directly achieves the success criteria]

## Validation Approach
[How to verify each success criterion is met]