REQUIRED READING ORDER:
1. Read .agent-outputs/exploration.md to understand the specific problem context
2. Read .agent-outputs/success-criteria.md to understand the approved success criteria

YOUR ONLY RESPONSIBILITIES:
1. Create an implementation plan that directly achieves the approved success criteria
2. List exact files to modify (only those necessary for the specific problem)
3. Reference the approved success criteria exactly (DO NOT change or expand them)
4. Write plan to .agent-outputs/plan.md

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

## Problem Reference
[Restate the specific problem from exploration.md]

## Success Criteria (Approved)
[Copy exactly from success-criteria.md - DO NOT modify]

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