TASK: {{task}}

**REQUIRED FIRST ACTION**: Read SAGE.md (or SAGE-meta.md in meta mode) before ANY other action. This file contains critical project understanding, recent discoveries, and known gotchas that prevent redundant exploration and ensure efficient problem-solving.

## TASK TYPE DETECTION

First, determine what kind of work this is:
- **BUG FIX**: Something is broken and needs fixing (commands fail, errors occur, system hangs)
- **FEATURE**: New functionality to add (user requirements, new capabilities)
- **ENHANCEMENT**: Improve existing functionality (performance, usability, maintainability)
- **REFACTOR**: Restructure code without changing behavior (code quality, organization)
- **DOCUMENTATION**: Create or update documentation (guides, API docs, comments)

Apply the appropriate exploration strategy based on task type.

## FOR BUG FIXES - EMPIRICAL VERIFICATION REQUIRED

When fixing broken systems:
1. If failing command provided, EXECUTE IT first
2. Document EXACT output and behavior observed
3. Identify WHERE it fails (not where you think it fails)
4. Determine WHY it fails at that point
5. Focus on ROOT CAUSES not symptoms

CRITICAL: Never trust problem descriptions without verification.

## FOR FEATURES - REQUIREMENTS ANALYSIS

When adding new functionality:
1. Understand user requirements and use cases
2. Analyze existing architecture for integration points
3. Identify patterns and conventions to follow
4. Define clear functional success criteria
5. Consider testing requirements

## FOR ENHANCEMENTS - CURRENT STATE ANALYSIS  

When improving existing functionality:
1. Measure current performance/behavior (if applicable)
2. Understand existing implementation approach
3. Identify improvement opportunities
4. Define measurable improvement targets
5. Consider impact on existing users

## FOR REFACTORING - BEHAVIOR DOCUMENTATION

When restructuring code:
1. Document current behavior thoroughly
2. Identify code quality issues to address  
3. Understand existing test coverage
4. Define refactoring scope and boundaries
5. Ensure behavior preservation strategy

YOUR RESPONSIBILITIES (ADAPTED TO TASK TYPE):
1. Identify the task type from the provided description
2. Apply appropriate exploration strategy (empirical/analytical/requirements-based)
3. Read relevant files (maximum 7) to understand context
4. Define task-appropriate success criteria
5. Document findings in .agent-outputs/exploration.md

## PROBLEM SCOPE CHECK

Flag if the problem seems unusually complex:
- Touches many interconnected systems
- Requires changes across multiple layers
- Has cascading dependencies
- Involves state management across files

If complex, note in exploration.md:
"## Scope Note: This problem touches [X] systems and may require careful design to keep implementation simple."

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

## Task Type Identified
[State the detected task type: BUG FIX / FEATURE / ENHANCEMENT / REFACTOR / DOCUMENTATION]

## FOR BUG FIXES - Empirical Problem Verification
[Use this section only for bug fixes - document command execution and failure analysis]
- Reproduction command: [exact command that demonstrates the issue]
- Expected behavior: [what should have happened]
- Actual behavior: [what actually happened]  
- Failure point: [exactly where process fails - line number, function, system call]
- Root cause: [why it fails - deadlock, missing resource, logic error, etc.]
- Evidence: [logs, error messages, traces supporting the conclusion]

## FOR FEATURES - Requirements Analysis  
[Use this section only for new features - document functional requirements]
- User requirements: [what functionality should be added]
- Use cases: [how users will interact with the feature]
- Integration points: [where feature connects to existing system]
- Dependencies: [existing components the feature will use]
- Architecture approach: [high-level design strategy]

## FOR ENHANCEMENTS - Current State Analysis
[Use this section only for improvements - document current state and targets]
- Current behavior/performance: [measurable baseline where applicable]
- Improvement goals: [specific targets to achieve]
- Implementation approach: [strategy for achieving improvements]
- Success metrics: [how improvement will be measured]

## FOR REFACTORING - Behavior Documentation
[Use this section only for code restructuring - document preservation requirements]
- Current behavior: [detailed description of what system currently does]
- Code quality issues: [problems to address through refactoring]
- Refactoring scope: [specific areas to restructure]
- Preservation strategy: [how to ensure behavior remains unchanged]

## Relevant Code Analysis
[Files and components involved in the work - adapted to task type]
- Primary files: [key files to modify/analyze]
- Dependencies: [related components that may be affected]
- Existing patterns: [architectural patterns to follow or modify]

## Existing Tests  
[Tests that validate the work area]
- Current test coverage: [existing tests for the area]
- Test gaps: [areas needing additional testing]
- Testing strategy: [approach for validating the work]

## Task-Appropriate Success Criteria
[Success criteria adapted to the task type]

**FOR BUG FIXES**:
1. Original failing command succeeds: [Command X] completes without [failure]
2. Root cause eliminated: [Specific cause] no longer present
3. No symptom masking: Fix addresses cause, not symptoms
4. Regression prevented: Tests added to prevent reoccurrence

**FOR FEATURES**:
1. Functionality implemented: [Feature X] works as specified
2. Integration successful: Feature integrates properly with existing system
3. Testing complete: Feature tested for expected use cases
4. Documentation updated: Usage instructions provided

**FOR ENHANCEMENTS**:
1. Improvement achieved: [Metric X] improved from [baseline] to [target]
2. Backward compatibility: Existing functionality unaffected
3. Performance validated: Enhancement provides measurable benefit

**FOR REFACTORING**:
1. Behavior preserved: All existing functionality works identically
2. Code quality improved: [Specific quality metrics] enhanced
3. Tests pass: All existing tests continue to pass
4. Structure improved: Code is more maintainable/readable

SUCCESS CRITERIA:
- [Criterion 1 - specify exact verification method for task type]
- [Criterion 2 - specify exact verification method for task type]  
- [Criterion 3 - specify exact verification method for task type]