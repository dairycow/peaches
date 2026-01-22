# MISTAKES.md Workflow Implementation Summary

## Implementation Date
2025-01-22

## Files Created

### 1. `/home/hf/peaches/MISTAKES.md` (40 lines)
Project-level mistake tracking document with timeline format.

**Features:**
- Severity levels (INFO/WARNING/ERROR)
- Structured format: Location, Issue, Impact, Resolution
- Chronological organisation
- Usage instructions
- Initial example mistakes added

**Location pattern:** `app/module/file.py:line_number`

### 2. `/home/hf/peaches/.opencode/commands/capture-mistakes.md` (88 lines)
OpenCode command for automated mistake detection and logging.

**Capabilities:**
- Analyses recent git changes
- Detects common Python pattern violations:
  - Async violations (missing run_in_executor for vn.py calls)
  - Error handling issues (bare except, missing logging)
  - Type hint problems (mypy errors)
  - Code style violations (ruff checks)
  - Testing issues (mocks, test failures)
  - Documentation gaps (missing docstrings)
- Formats mistakes in MISTAKES.md structure
- Prompts for approval before updating MISTAKES.md
- Uses subagent mode to avoid polluting main context

### 3. Updated `/home/hf/peaches/AGENTS.md`
Added AI Mistake Tracking section with:
- MISTAKES.md reference
- Capture workflow instructions
- Mistake categories
- Severity level definitions

## Usage

### Manual Trigger
```bash
# In OpenCode TUI
/capture-mistakes
```

The command will:
1. Check recent AI changes via git
2. Run analysis tools (mypy, ruff, grep patterns)
3. Present findings with severity and location
4. Ask for approval to append to MISTAKES.md
5. Update MISTAKES.md if approved

### Manual Entry
If you catch a mistake manually, add it directly to MISTAKES.md:

```markdown
### [SEVERITY]: [Mistake description]
- **Location**: `path/to/file:line_number`
- **Issue**: [Brief description]
- **Impact**: [Consequences if not fixed]
- **Resolution**: [How to fix]
```

## Mistake Categories Tracked

### Code Patterns
- Async violations (blocking vn.py calls)
- Error handling (missing try/except, wrong logging)
- Type hints (missing annotations, type errors)
- Style issues (naming, complexity, refactoring opportunities)

### Testing
- Missing tests for new features
- Improper mocking (per AGENTS.md, should avoid mocks)
- Test failures
- Test coverage gaps

### Documentation
- Missing docstrings on public APIs
- Outdated comments (self-documenting code preferred)
- Outdated AGENTS.md entries

## Severity Levels

- **INFO**: Style violations, minor issues, recommendations
- **WARNING**: Potential issues, non-critical bugs, problematic patterns
- **ERROR**: Blocking issues, test failures, deployment failures, production impact

## Integration with Existing Workflow

### Worktree Development
When working in a worktree:
```bash
# Start new worktree
./create-worktree.sh feature/new-feature

# Work on feature...

# Before merging back
/capture-mistakes  # Review and log any mistakes

# Merge back
./merge-worktree.sh feature/new-feature
```

### Pre-commit Workflow
As part of `make check`:
```bash
make check  # Runs format, lint, type-check, test
# Then run:
/capture-mistakes  # Review for AI-generated mistakes
```

## Example Mistakes (Added During Implementation)

### INFO: Missing MISTAKES.md documentation
No structured approach to track AI mistakes - resolved by creating MISTAKES.md

### ERROR: Type mismatch in announcement_scraper.py
Assigning int to str variable causes incompatible types - needs type conversion

### WARNING: Missing ScanStatus parameters
Scanner called without required parameters - would cause runtime failure

### INFO: Missing type annotation
Variable lacks type annotation - reduces code clarity

## Benefits

1. **Learning from mistakes**: Prevents repeating same errors
2. **Pattern detection**: Identifies recurring issues across sessions
3. **Improved workflow**: Structured approach to quality improvement
4. **Team collaboration**: MISTAKES.md can be committed to git (if desired)
5. **Context preservation**: Mistakes documented with file locations and resolutions

## Maintenance

- Review MISTAKES.md periodically to identify patterns
- Consider updating AGENTS.md if mistakes reveal missing guidelines
- Commit MISTAKES.md changes to git if team-wide learning desired
- Keep entries concise (aim for under 200 lines total)
- Archive old entries if file grows too large

## Future Enhancements (Optional)

1. Add `/view-mistakes` command to filter by severity/category
2. Add `/resolve-mistake` command to mark entries as resolved
3. Integrate with CI/CD to automatically detect mistakes in PRs
4. Generate statistics on mistake patterns over time
5. Link mistakes to specific worktrees for better tracking
