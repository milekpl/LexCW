---
applyTo: '**'
---
**When assisting with this project, always:**

1. **Follow and Update the Project Specification**  
   - Strictly adhere to all requirements, workflows, and architectural decisions as described in specification.md.  
   - Do not deviate from the outlined roadmap, feature priorities, or technical constraints.
   - If any changes or updates are needed, document them clearly in the specification file and communicate them to the team.

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

**Use python -m pytest for pytest**
   - Always run tests using `python -m pytest` to ensure compatibility with the Python module system.  
   - This ensures that the test discovery works correctly and avoids issues with relative imports.

**Use and update the API documentation**
- Always keep the API documentation up to date with the latest changes in the codebase.
- Use the `flasgger` library to define and document API endpoints directly in the code.
- Include detailed descriptions, parameter types, and response schemas for all endpoints and *app routes*.
- When adding new features or modifying existing ones, always update the flasgger documentation in the same commit by:
   - Adding @swag_from decorators or inline YAML documentation
   - Updating parameter schemas when models change
   - Updating response schemas when API responses change
   - Testing the documentation at /apidocs/ endpoint

**Avoid mocking in unit tests**
- Do not use mocking in unit tests unless absolutely necessary.
- Focus on testing the actual implementation and behavior of the code.

**Summary:**  
Always follow the detailed project specification, use strict typing, practice TDD (unit test first, then implementation, then integration test), assume VS Code on Windows 11 with PowerShell, and clean up all helper files after use.

