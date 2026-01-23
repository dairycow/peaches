---
description: Capture AI-generated mistakes for documentation
agent: build
subtask: true
---

Review recent AI-generated changes and identify mistakes to add to docs/MISTAKES.md.

**Your tasks:**

1. **Check for recent AI changes:**
   - Run: `git log --oneline -5 --all`
   - Identify recent commits or uncommitted changes made by AI

2. **Analyse for common Python mistakes:**

   **a) Async Pattern Violations:**
   - Search for direct vn.py calls without `run_in_executor`:
     Run: `grep -r "self.engine\|self.gateway" app/ --include="*.py" | grep -v "run_in_executor\|asyncio\|executor"`
   - Check for blocking operations in async functions

   **b) Error Handling Issues:**
   - Search for bare `except:` without specific exception types
   - Look for missing logging in exception handlers

   **c) Type Hint Issues:**
   - Run: `uv run mypy app/ 2>&1 | grep -A 2 "error:"`
   - Check for missing type hints on public APIs

   **d) Code Style Violations:**
   - Run: `uv run ruff check app/ --select N, SIM, ARG, UP`
   - Look for patterns flagged by linter

   **e) Testing Issues:**
   - Search for mocks in test files (should be avoided per AGENTS.md)
   - Run: `uv run pytest --collect-only 2>&1 | grep -i "error\|warning"`
   - Check for tests that would fail

   **f) Documentation Issues:**
   - Run: `uv run ruff check app/ --select D`
   - Look for missing docstrings on public functions/classes
   - Check for outdated comments (self-documenting code preferred)

3. **Categorise and format mistakes:**

   For each mistake found, format it as:

   ```markdown
   ### [SEVERITY]: [Mistake description]
   - **Location**: `path/to/file:line_number`
   - **Issue**: [Brief description of the problem]
   - **Impact**: [What would happen if not fixed]
   - **Resolution**: [How it was or should be fixed]
   ```

   Severity levels:
   - **INFO**: Style violations, minor issues, recommendations
   - **WARNING**: Potential issues, non-critical bugs, problematic patterns
   - **ERROR**: Blocking issues, test failures, deployment failures, production impact

4. **Generate output:**

   Present findings in this format:

   ```
   Found X potential mistakes:

   [List each with severity and location]

    Should these be added to docs/MISTAKES.md?
   If yes, I will append them with today's date.
   ```

5. **Update docs/MISTAKES.md if approved:**

    If user confirms:
    - Read current docs/MISTAKES.md
    - Add new section with today's date: `## YYYY-MM-DD - [Worktree name or description]`
    - Append all identified mistakes in chronological order
    - Write updated docs/MISTAKES.md

**Important:**
- Use Australian English spelling (e.g., analyse, initialise, organise)
- Be concise - keep descriptions brief and actionable
- Include line numbers for easy navigation
- Reference AGENTS.md sections when mistakes violate documented patterns
- If no mistakes found, report "No mistakes detected in recent changes"
- Focus on code-level and testing mistakes (configuration/deployment handled separately)
