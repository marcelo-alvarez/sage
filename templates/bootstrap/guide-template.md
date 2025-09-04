# [Project] Implementation Guide

## Diagnostic Methodology (REQUIRED FIRST)

### Problem Reproduction Protocol
1. Execute provided test commands exactly
2. Document actual vs expected behavior
3. Identify precise failure point
4. Gather evidence of failure mechanism

### Root Cause Analysis
- What IS happening (observable facts)
- Why it's happening (causal chain)
- What assumptions need challenging
- Evidence supporting conclusions

### Empirical Verification Standards
- NEVER trust problem descriptions without testing
- ALWAYS reproduce issues before analyzing
- REQUIRE specific commands that demonstrate failures
- DOCUMENT exact failure points (line numbers, system calls, etc.)

## Solution Approaches (ONLY AFTER DIAGNOSIS)

### Fixing vs Monitoring
- NEVER add timeouts to broken coordination
- NEVER add retries to failed logic
- FIX the root cause, don't paper over it

### Implementation Patterns
[Populated after diagnosis completes]

### Root Cause Elimination Strategies
[Specific approaches determined by diagnostic findings]

## Critical Anti-Patterns - NEVER DO THESE

### Symptom Treatment Instead of Root Cause Fixes
❌ Adding timeouts to hanging operations
❌ Adding retries to failing operations  
❌ Adding monitoring to broken systems
❌ Adding error handling to hide failures

### Assumption-Based Development
❌ Trusting problem descriptions without verification
❌ Implementing solutions before diagnosis
❌ Assuming you know where problems are
❌ Skipping empirical testing

## Correct Patterns - ALWAYS DO THESE

### Root Cause Elimination
✅ Identify why operation hangs, remove cause
✅ Understand why operation fails, fix logic
✅ Find what's broken, repair it
✅ Test empirically at every step

### Evidence-Based Development  
✅ Reproduce issues before analyzing
✅ Diagnose through testing not reading
✅ Verify fixes with original failing cases
✅ Document evidence for conclusions

## Success Criteria Templates

### For Diagnostic Tasks
1. Reproduction successful: [Command X] exhibits [failure behavior]
2. Failure point identified: Exact location in code/logs documented
3. Root cause determined: Causal chain from trigger to failure explained
4. Evidence documented: Logs/traces/test outputs support conclusion

### For Solution Tasks
1. Original command succeeds: [Command X] completes without [failure]
2. Root cause eliminated: [Specific cause] no longer present in code
3. No symptom masking: Fix addresses cause, not symptoms
4. Regression prevention: Tests added to prevent reoccurrence

## Project-Specific Implementation Details

[This section will be populated during bootstrap based on the specific project and problems being addressed]

### Architecture Context
[Key components and patterns relevant to the diagnosed problems]

### Testing Framework
[How to validate fixes in this specific project]

### Deployment Considerations
[Environment-specific factors that affect problem reproduction and solution verification]

## Validation Protocol

### Before Implementing Solutions
1. Root cause must be empirically verified through reproduction
2. Failure point must be precisely located in code/system
3. Evidence chain must be documented and reviewable
4. Solution approach must target verified cause, not symptoms

### After Implementing Solutions  
1. Original failing command must succeed
2. Root cause must be eliminated from codebase
3. No anti-patterns (timeouts, retries, monitoring) added
4. Regression tests must prevent reoccurrence

## Common Failure Patterns and Diagnostic Approaches

[This section grows over time as patterns are discovered]

### Pattern: Hanging Operations
- Diagnostic approach: Identify exact hang point, check for deadlocks, analyze synchronization
- Anti-pattern: Adding timeouts
- Correct pattern: Remove deadlock cause

### Pattern: Failing Commands
- Diagnostic approach: Run command, capture exact error, trace failure path
- Anti-pattern: Adding error handling to hide failure
- Correct pattern: Fix the logic that causes the failure

### Pattern: Performance Issues
- Diagnostic approach: Profile to identify bottleneck, measure actual performance
- Anti-pattern: Adding monitoring without fixing bottleneck
- Correct pattern: Optimize or eliminate the actual bottleneck