---
description: Update project documentation
agent: build
---

Search for all markdown files in the project (excluding .venv, node_modules, .git), analyse the codebase structure, identify documentation debt, and automatically update documentation files using a hybrid approach.

**Your tasks:**

1. **Discover all markdown files:**
   - Run: `find /home/hf/peaches -type f -name "*.md" -not -path "*/\.venv/*" -not -path "*/node_modules/*" -not -path "*/\.git/*" -not -path "*/\.pytest_cache/*" -not -path "*/\.mypy_cache/*" -not -path "*/\.ruff_cache/*" -not -path "*/htmlcov/*"`
   - List all existing documentation files

2. **Analyse codebase structure:**
   - Run: `find /home/hf/peaches/app -type f -name "*.py" | head -50`
   - Run: `tree -L 3 -d /home/hf/peaches/app 2>/dev/null || find /home/hf/peaches/app -type d -maxdepth 3 | sort`
   - Identify main components: api/, analysis/, cli/, scanners/, strategies/, services/

3. **Read existing documentation:**
   - Read: `/home/hf/peaches/README.md`
   - Read: `/home/hf/peaches/AGENTS.md`
   - Read: `/home/hf/peaches/.opencode/skills/cli-analysis/SKILL.md`

4. **Check documentation debt:**

   **a) API Documentation:**
   - Scan `app/api/v1/` for routers
   - Compare endpoints documented in README.md vs actual endpoints
   - Check for missing endpoint documentation

   **b) Strategies Documentation:**
   - List files in `app/strategies/` and `app/analysis/strategies/`
   - Check if each strategy is documented with:
     - Description and purpose
     - Parameters and their defaults
     - Usage examples
     - Entry/exit logic
    - Create `docs/STRATEGIES.md` if missing or incomplete

   **c) Scanners Documentation:**
   - List files in `app/scanners/` and `app/analysis/scanners/`
   - Check if each scanner is documented with:
     - What it detects (e.g., price-sensitive announcements, gaps)
     - Parameters and configuration
     - Usage examples
    - Create `docs/SCANNERS.md` if missing or incomplete

   **d) Services Documentation:**
   - List files in `app/services/`
   - Check for documentation on:
     - Gateway service
     - Strategy trigger service
     - Notification service
     - Scanner service
     - Import scheduler
    - Create `docs/SERVICES.md` if missing

   **e) CLI Documentation:**
   - Check `app/cli/` for CLI tools
   - Verify usage is documented (may be in SKILL.md)
   - Create `CLI.md` if comprehensive docs needed

   **f) Configuration Documentation:**
   - Read `/home/hf/peaches/config/settings.yaml` if exists
   - Check if all config options are documented in README.md or AGENTS.md

   **g) Docstring Coverage:**
   - Run: `uv run ruff check app/ --select D`
   - Check for missing docstrings on public APIs
   - Add docstrings where missing

5. **Update documentation (HYBRID APPROACH):**

   **a) Update README.md:**
   - Ensure Quick Start section is complete
   - Keep API endpoints overview (detailed docs in API.md if needed)
   - Keep Configuration section
   - Ensure all user-facing commands are documented
   - Update file locations if changed

   **b) Update AGENTS.md:**
   - Ensure development workflow is current
   - Keep code quality guidelines
   - Ensure code patterns are comprehensive
   - Add any new patterns discovered
   - Update file locations

    **c) Create/update docs/STRATEGIES.md:**
   - Document all trading strategies
   - Include strategy parameters, logic, examples
   - Reference backtest CLI usage
   - Link to code files

    **d) Create/update docs/SCANNERS.md:**
   - Document all market scanners
   - Include parameters and usage
   - Link to code files

    **e) Create/update docs/SERVICES.md:**
   - Document internal service architecture
   - Explain service interactions
   - Include configuration notes

   **f) Create/update CLI.md:**
   - Document all CLI tools
   - Include usage examples
   - Reference skill files

 6. **Generate completion summary:**
     - List all files updated/created with line counts
     - Count documentation debt items addressed
     - Verify all new docs meet quality standards (concise, no bloat, Australian English)
     - Highlight any remaining gaps
     - Provide recommendations for ongoing maintenance

 **Important:**
 - Use the existing code style from README.md and AGENTS.md
 - Use Australian English spelling (e.g., colour, analyse, initialise, organise)
 - Be concise - avoid comprehensive documentation that bloats files
 - No emojis
 - Each new doc file should be under 200 lines
 - Check for content duplication across docs before adding
 - Include code examples where helpful
 - Cross-reference between documents
 - Update file references to use absolute paths where appropriate
 - Follow the project's formatting conventions (100 char line length where applicable)

