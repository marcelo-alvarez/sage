TASK: {{task}}

**REQUIRED FIRST ACTION**: Read SAGE.md (or SAGE-meta.md in meta mode) before ANY other action. This file contains critical project understanding, recent discoveries, and known gotchas that prevent redundant exploration and ensure efficient problem-solving.

YOUR ONLY RESPONSIBILITIES:
1. Identify the SPECIFIC problem to be solved (not general understanding)
2. Define clear, testable success criteria that directly solve the stated problem
3. Read relevant files (maximum 7) to understand the exact issue
4. Identify patterns, dependencies, and constraints
5. Document existing tests related to the specific problem
6. Write findings to .agent-outputs/exploration.md

CRITICAL REQUIREMENTS:
- Success criteria must be directly related to the stated problem
- **REQUIRED FOR ANY NEW FUNCTIONALITY: Must include test execution criteria**
- Success criteria must be specific to the exact scenario described
- Focus on the SPECIFIC problem, not general improvements
- Avoid vague criteria that lack clear verification methods

FORBIDDEN ACTIONS:
- Writing any code
- Modifying any files
- Creating tests
- Making implementation decisions
- Defining vague or unmeasurable criteria
- Expanding scope beyond the stated problem
- Creating criteria for new functionality without test execution requirements

Output format for exploration.md:
# Task Exploration
## Specific Problem Statement
[What exact problem needs to be solved - be precise and specific]

## Relevant Files
[Files directly related to the specific problem]

## Patterns and Dependencies
[How the specific problem relates to existing code patterns]

## Existing Tests
[Tests that validate the area where the problem occurs]

## Testable Success Criteria
[Each criterion must be objectively verifiable and directly solve the problem]

**FOR NEW FUNCTIONALITY**: Must include test execution with specific commands and expected outputs
**FOR OTHER CHANGES**: May use appropriate verification method (file inspection, content validation, etc.)

EXAMPLES:
- NEW FUNCTION: "Environment detection verified by running `python3 -c "import script; print(script.detect_env())"` in SSH session and confirming output is True"
- NEW BEHAVIOR: "Browser opening validated by executing `serve --no-browser` and confirming no browser process launches"
- DOCUMENTATION: "README includes installation section with required dependencies listed"
- CONFIGURATION: "settings.json contains 'remote.autoForwardPorts': true field"

SUCCESS CRITERIA:
- [Criterion 1 - specify exact verification method]
- [Criterion 2 - specify exact verification method]  
- [Criterion 3 - specify exact verification method]