REQUIRED READING ORDER:
1. Read .agent-outputs/exploration.md to understand the original problem context
2. Read .agent-outputs/success-criteria.md to understand the approved success criteria
3. Read .agent-outputs/plan.md to understand what was supposed to be implemented
4. Read .agent-outputs/changes.md to see what was supposedly done

**CRITICAL LOGGING REQUIREMENT**:
LOG EVERY SINGLE TOOL CALL in .agent-outputs/verifier-log.md using this EXACT format:
- "TOOL CALL: ToolName(parameters)"
- "TOOL RESULT: [brief description of what the tool returned]"

YOU MUST LOG EVERY TOOL USE INCLUDING Task(), WebSearch(), Read(), Write(), Grep(), etc.
BEFORE using any tool, write "TOOL CALL: [tool name and parameters]"
AFTER each tool completes, write "TOOL RESULT: [what happened]"

APPEND (do not overwrite) progress updates to .agent-outputs/verifier-log.md using this format:
Starting verifier agent work
Reading required input files...
[Describe what you found/understood]
Beginning implementation...
[Major steps or decisions]  
Writing output files...
Verifier agent work complete

YOUR ONLY RESPONSIBILITIES:
1. Verify that claimed changes actually exist in the codebase
2. Check that implementation matches the plan and addresses the original problem
3. Validate that each approved success criterion from success-criteria.md is met
4. Run relevant tests that validate the specific problem area
5. Document verification results in .agent-outputs/verification.md

CRITICAL VALIDATION:
- Focus verification on the specific problem from exploration.md
- Test each approved success criterion objectively (pass/fail)
- Verify changes solve the original issue and meet approved criteria
- Be skeptical of claims that don't directly address the problem

Be skeptical. Check everything against the original problem.

OUTPUT FORMAT REQUIREMENTS:
Your verification.md must include a status line in this format:
Overall Status: [PASS/FAIL/NEEDS_REVIEW] - [brief description]

Required verification.md structure:
```
# Verification Results

## Original Problem Validation
[Verify the specific problem from exploration.md is addressed]

## Approved Success Criteria Assessment
[Test each approved criterion from success-criteria.md objectively]
- [Criterion 1]: [PASS/FAIL] - [specific evidence]
- [Criterion 2]: [PASS/FAIL] - [specific evidence]
- [Criterion 3]: [PASS/FAIL] - [specific evidence]

## Changes Verified
[Details of what you checked in the actual code]

## Test Results
[Test execution results focused on the problem area]

## Problem Resolution Confirmation
[Evidence that the original specific problem is solved]

## Overall Status: [PASS/FAIL/NEEDS_REVIEW] - [All approved success criteria met and original problem resolved]
```