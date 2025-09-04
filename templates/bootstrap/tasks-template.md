# [Project Name] Tasks - Detailed Implementation Plan

*Use the task pattern that matches the work type identified during bootstrap*

## FOR BUG FIXES - Diagnostic Pattern

### Task 1: Diagnose [Problem Name]
[Single paragraph describing the diagnostic work needed: execute the failing command [exact command], document exact behavior observed, identify precisely where it fails (line number, function, system call), investigate why it fails at that point (deadlock, missing resource, logic error), gather evidence supporting the root cause conclusion, and document all findings with empirical evidence per guide.md Problem Diagnosis Protocol - approximately 500-1000 characters without line breaks]

### USER VALIDATION A: [Diagnosis Confirmation]
**THE USER MUST MANUALLY VALIDATE THE DIAGNOSED ROOT CAUSE BEFORE PROCEEDING**. [Detailed description of diagnostic evidence to review] by checking: (1) [exact reproduction command and observed behavior], (2) [specific failure point identification], (3) [root cause evidence verification], documenting validation decision in checklist comments, and only proceeding if root cause is clearly identified and empirically supported - STOP IMMEDIATELY if diagnosis is unclear, symptoms-focused, or lacks evidence. This validation ensures solutions target actual problems not symptoms.

### Task 2: Fix [Root Cause Name]  
[Single paragraph describing the solution work needed: eliminate the specific root cause identified in Task 1 by [specific elimination approach], modify only the files containing the verified problem source [file names], implement changes that directly address the causal mechanism, and ensure no symptom-masking approaches like timeouts or retries are added per guide.md Solution Approaches - approximately 500-1000 characters without line breaks]

### USER TEST B: [Original Problem Resolution Test]
**THE USER MUST MANUALLY VERIFY THE ORIGINAL PROBLEM IS RESOLVED**. Execute the exact failing command from Task 1 diagnosis [specific command] and confirm: (1) [command now succeeds without original failure], (2) [expected behavior occurs], (3) [no symptom masking detected], recording all test results in test log, proceeding only if original problem is completely resolved - HALT if original issue persists or symptoms were merely hidden.

## FOR FEATURES - Design Pattern

### Task 1: Explore and Design [Feature Name]
[Single paragraph describing the design work needed: analyze user requirements [specific requirements], research existing architectural patterns, design integration approach with existing systems [specific integration points], plan data models and API interfaces, consider scalability and performance implications, and document complete feature architecture per guide.md Feature Design Protocol - approximately 500-1000 characters without line breaks]

### USER REVIEW A: [Design Approval]
**THE USER MUST REVIEW AND APPROVE THE FEATURE DESIGN BEFORE IMPLEMENTATION**. [Detailed description of design elements to review] by checking: (1) [requirements coverage and user scenarios], (2) [integration approach and architectural fit], (3) [scalability and maintainability considerations], documenting approval decision in checklist comments, and only proceeding if design is complete and architecturally sound - STOP IMMEDIATELY if design is incomplete, conflicts with existing patterns, or doesn't meet requirements.

### Task 2: Implement [Feature Name]
[Single paragraph describing the implementation work needed: create [specific components] following approved design, implement proper error handling and input validation, add comprehensive logging and monitoring, ensure integration with existing systems works correctly [specific integration points], and include comprehensive unit and integration tests per guide.md Feature Implementation - approximately 500-1000 characters without line breaks]

### Task 3: Test [Feature Name]
[Single paragraph describing the testing work needed: create comprehensive test suite covering all user scenarios [specific scenarios], test integration with existing systems, validate error handling and edge cases, perform load/performance testing where applicable, and document all test results per guide.md Feature Testing - approximately 500-1000 characters without line breaks]

### USER TEST B: [Feature Acceptance Test]
**THE USER MUST VALIDATE THE FEATURE MEETS ALL REQUIREMENTS**. Test the implemented feature by: (1) [execute key user scenarios and workflows], (2) [verify integration with existing features], (3) [test error handling and edge cases], recording all test results in acceptance log, proceeding only if all requirements are met and feature works as designed - HALT if any requirements are not satisfied or integration issues exist.

## FOR ENHANCEMENTS - Analysis Pattern

### Task 1: Analyze Current [System Name] State
[Single paragraph describing the analysis work needed: measure current performance/behavior [specific metrics], document existing implementation approach, identify bottlenecks or improvement opportunities, establish measurable baseline metrics, research improvement strategies and best practices, and define specific improvement targets per guide.md Enhancement Analysis - approximately 500-1000 characters without line breaks]

### USER VALIDATION A: [Analysis Confirmation]
**THE USER MUST CONFIRM ANALYSIS AND IMPROVEMENT TARGETS**. Review analysis results by checking: (1) [baseline measurements are accurate and representative], (2) [improvement targets are realistic and measurable], (3) [proposed enhancement strategy is sound], documenting validation decision and only proceeding if analysis is thorough and targets are achievable - STOP IMMEDIATELY if baseline is unclear or targets are unrealistic.

### Task 2: Implement [Enhancement Name]
[Single paragraph describing the enhancement work needed: implement specific improvements [detailed improvement approach], optimize performance bottlenecks identified in analysis, ensure backward compatibility is maintained, add monitoring to track improvement metrics, validate that existing functionality is preserved, and document all changes per guide.md Enhancement Implementation - approximately 500-1000 characters without line breaks]

### USER TEST B: [Enhancement Validation Test]
**THE USER MUST VALIDATE IMPROVEMENTS ARE ACHIEVED**. Measure enhancement results by: (1) [re-measure metrics and compare to baseline], (2) [verify improvement targets were met], (3) [confirm existing functionality unaffected], recording all measurements in validation log, proceeding only if improvements are demonstrated and no regressions introduced - HALT if targets not met or existing features broken.

## FOR REFACTORING - Preservation Pattern

### Task 1: Document [Code Area] Current Behavior
[Single paragraph describing the documentation work needed: thoroughly document current behavior through testing [specific test approaches], identify all external interfaces and dependencies, catalog existing test coverage and any test gaps, document performance characteristics and expected behavior, identify specific code quality issues to address, and create comprehensive behavior baseline per guide.md Refactoring Documentation - approximately 500-1000 characters without line breaks]

### USER VALIDATION A: [Behavior Documentation Confirmation]
**THE USER MUST CONFIRM BEHAVIOR DOCUMENTATION IS COMPLETE**. Review documentation by checking: (1) [behavior documentation covers all functionality], (2) [refactoring scope is clearly defined and appropriate], (3) [preservation strategy will maintain all existing behavior], documenting validation decision and only proceeding if documentation is comprehensive and refactoring plan preserves functionality - STOP IMMEDIATELY if documentation is incomplete or refactoring risks breaking existing behavior.

### Task 2: Refactor [Code Area] 
[Single paragraph describing the refactoring work needed: restructure code to improve quality while maintaining identical behavior, apply consistent formatting and naming conventions, improve code organization and modularity, eliminate code duplication and technical debt, ensure all existing tests continue to pass, and validate behavior remains unchanged per guide.md Refactoring Implementation - approximately 500-1000 characters without line breaks]

### USER TEST B: [Behavior Preservation Test]
**THE USER MUST VERIFY BEHAVIOR IS UNCHANGED AFTER REFACTORING**. Validate refactoring by: (1) [run all existing tests and confirm they pass], (2) [compare functionality to documented baseline behavior], (3) [verify code quality improvements achieved], recording all validation results in test log, proceeding only if behavior is preserved and quality improvements demonstrated - HALT if any behavior changes detected or tests fail.

## TASK TYPE GUIDANCE

### FORBIDDEN BUG FIX PATTERNS:
- ❌ "Add timeout to prevent hanging" 
- ❌ "Implement better error handling"
- ❌ "Add monitoring to detect issues"
- ❌ "Improve coordination mechanisms"

### REQUIRED BUG FIX PATTERNS:
- ✅ "Execute failing command [X] and identify root cause"
- ✅ "Eliminate deadlock at identified location [file:line]"  
- ✅ "Fix logic error causing failure in [specific function]"

### FORBIDDEN FEATURE PATTERNS:
- ❌ "Add some user management functionality"
- ❌ "Make the UI better somehow"
- ❌ "Improve the API"

### REQUIRED FEATURE PATTERNS:
- ✅ "Implement user registration with email validation and password hashing"
- ✅ "Create dashboard displaying metrics X, Y, Z with real-time updates"
- ✅ "Add REST API endpoints for CRUD operations on user profiles"

### FORBIDDEN ENHANCEMENT PATTERNS:
- ❌ "Make it faster"
- ❌ "Improve performance"
- ❌ "Optimize the code"

### REQUIRED ENHANCEMENT PATTERNS:
- ✅ "Reduce API response time from 500ms to <100ms through caching"
- ✅ "Increase throughput from 100 to 1000 requests/second via connection pooling"
- ✅ "Decrease memory usage by 50% through efficient data structures"