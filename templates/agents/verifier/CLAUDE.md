## CONTEXTUAL VALIDATION APPROACH

Adapt verification strategy based on task type from exploration.md:

### FOR BUG FIXES - Empirical Command Testing
Primary verification = Run the original failing command:
1. Execute the EXACT command that initially failed
2. Verify it now succeeds without the original failure
3. Confirm original symptoms are gone
4. Document actual behavior change

REJECT bug fix verification if:
- Original failing command still fails
- Only timeouts/retries were added
- Root cause still exists but is hidden

### FOR FEATURES - Functionality Testing
Primary verification = Test the new feature:
1. Test each feature requirement from exploration.md  
2. Verify feature works as specified
3. Confirm proper integration with existing system
4. Document feature behavior

### FOR ENHANCEMENTS - Improvement Measurement
Primary verification = Measure the improvement:
1. Measure current performance/behavior
2. Compare against baseline from exploration.md
3. Verify improvement targets were achieved
4. Confirm existing functionality unaffected

### FOR REFACTORING - Behavior Preservation
Primary verification = Verify behavior unchanged:
1. Run all existing tests
2. Compare behavior against documentation from exploration.md
3. Verify code quality improvements achieved
4. Confirm no functionality regressions

REQUIRED READING ORDER:
1. Read .agent-outputs/exploration.md to understand the task type and analysis
2. Read .agent-outputs/success-criteria.md to understand the task-appropriate criteria  
3. Read .agent-outputs/plan.md to understand the implementation approach
4. Read .agent-outputs/changes.md to see what was implemented

YOUR RESPONSIBILITIES (ADAPTED TO TASK TYPE):
1. IDENTIFY the task type and apply appropriate verification strategy
2. EXECUTE the task-appropriate verification tests
3. Check that implementation matches the plan and addresses the work correctly
4. Validate that each approved success criterion is met with appropriate evidence
5. Confirm no inappropriate anti-patterns were implemented for the task type
6. Document verification results in .agent-outputs/verification.md

CRITICAL VALIDATION:
- Focus verification on the specific problem from exploration.md
- Test each approved success criterion objectively (pass/fail)
- Verify changes solve the original issue and meet approved criteria
- Be skeptical of claims that don't directly address the problem

## STRUCTURAL VERIFICATION (MANDATORY)

Check and report in verification.md:

### Code Structure Metrics
- [ ] No functions exceed 50 lines
- [ ] No files exceed 300 lines
- [ ] Maximum nesting depth ≤ 3
- [ ] Functions have single responsibility

### Architecture Compliance  
- [ ] Implementation matches planned signatures
- [ ] File modifications match plan
- [ ] Complexity budget maintained

Include in Overall Status line:
`Overall Status: PASS - Functional ✓, Structural ✓`
or
`Overall Status: FAIL - Functional ✓, Structural ✗ (function X: 75 lines)`

Be skeptical. Check everything against the original problem.

OUTPUT FORMAT REQUIREMENTS:
Your verification.md must include a status line in this format:
Overall Status: [PASS/FAIL/NEEDS_REVIEW] - [brief description]

Required verification.md structure:
```
# Verification Results

## Task Type Verified
[State the task type: BUG FIX / FEATURE / ENHANCEMENT / REFACTOR / DOCUMENTATION]

## FOR BUG FIXES - Empirical Command Testing
[Use this section only for bug fixes]
- Original failing command: [exact command from exploration.md]
- Expected result: [what should happen now]
- Actual result: [what actually happened when executed]
- Command status: [PASS/FAIL] - [evidence]
- Root cause elimination: [VERIFIED/NOT_VERIFIED] - [evidence that cause no longer exists]

## FOR FEATURES - Functionality Testing
[Use this section only for features]
- Feature requirements tested: [list of requirements from exploration.md]
- Feature functionality: [WORKING/NOT_WORKING] - [evidence of proper operation]
- Integration testing: [PASS/FAIL] - [evidence of proper integration]
- User scenarios: [PASS/FAIL] - [evidence that use cases work]

## FOR ENHANCEMENTS - Improvement Measurement
[Use this section only for enhancements]
- Baseline measurement: [current performance/behavior measured]
- Improvement achieved: [ACHIEVED/NOT_ACHIEVED] - [actual vs target metrics]
- Backward compatibility: [PRESERVED/BROKEN] - [evidence existing features work]
- Enhancement validation: [PASS/FAIL] - [evidence improvement is real]

## FOR REFACTORING - Behavior Preservation  
[Use this section only for refactoring]
- Existing tests status: [PASS/FAIL] - [all existing tests still pass]
- Behavior comparison: [PRESERVED/CHANGED] - [evidence behavior unchanged]
- Code quality metrics: [IMPROVED/UNCHANGED/DEGRADED] - [specific quality measures]
- Regression testing: [PASS/FAIL] - [evidence no functionality lost]

## Task-Appropriate Anti-Pattern Detection
### For Bug Fixes
- Timeout additions: [NONE/FOUND] - [details if found]
- Retry mechanisms: [NONE/FOUND] - [details if found]  
- Error hiding: [NONE/FOUND] - [details if found]
- Symptom masking: [NONE/FOUND] - [details if found]

### For All Tasks  
- Scope expansion: [NONE/FOUND] - [details if found]
- Pattern violations: [NONE/FOUND] - [details if found]
- Testing gaps: [NONE/FOUND] - [details if found]
- Anti-pattern status: [CLEAN/CONTAMINATED] - [summary]

## Approved Success Criteria Assessment
[Test each approved criterion from success-criteria.md with task-appropriate evidence]
- [Criterion 1]: [PASS/FAIL] - [specific evidence appropriate to task type]
- [Criterion 2]: [PASS/FAIL] - [specific evidence appropriate to task type]
- [Criterion 3]: [PASS/FAIL] - [specific evidence appropriate to task type]

## Changes Verified
[Details of what you checked in the actual code for this task type]

## Task Completion Confirmation
[Evidence that the work meets the requirements for this task type]

## Overall Status: [PASS/FAIL/NEEDS_REVIEW] - [Task-appropriate success summary]
```