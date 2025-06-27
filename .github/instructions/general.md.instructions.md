---
applyTo: '**'
---
**When assisting with this project, always:**

1. **Follow the Project Specification**  
   - Strictly adhere to all requirements, workflows, and architectural decisions as described in specification.md.  
   - Do not deviate from the outlined roadmap, feature priorities, or technical constraints.

2. **Adopt Test-Driven Development (TDD)**  
   - Always begin by writing a unit test that defines the desired behavior for any new feature or bugfix.  
   - Only then implement the feature or fix, followed by an integration test to ensure end-to-end correctness.  
   - Ensure all tests are compatible with `pytest` and contribute to achieving >90% code coverage.

3. **Assume the Development Environment**  
   - Code is developed in Visual Studio Code on Windows 11, using the PowerShell terminal.  
   - Provide Windows-specific commands and paths when relevant.

4. **Clean Up Helper Files**  
   - After implementing features or running scripts, always remove or clean up any temporary, helper, or test files created during development.  
   - Ensure the repository remains tidy and free of unnecessary artifacts.
---
applyTo: '*.py'
---
**Use Strict Typing in Python**  
   - Add explicit type annotations to all Python classes, methods, and functions.  
   - Prefer `mypy`-compatible type hints and use `from __future__ import annotations` where appropriate.

**Summary:**  
Always follow the detailed project specification, use strict typing, practice TDD (unit test first, then implementation, then integration test), assume VS Code on Windows 11 with PowerShell, and clean up all helper files after use.

