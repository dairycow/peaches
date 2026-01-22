# MISTAKES.md - AI Development Mistakes

## Overview
Track mistakes made by AI agents during development to prevent recurrence and improve workflow patterns.

## Severity Levels
- **INFO**: Style violations, minor issues, recommendations
- **WARNING**: Potential issues, non-critical bugs, patterns that could cause problems
- **ERROR**: Blocking issues, would fail tests, deployment failures, production impact

## Usage
Use `/capture-mistakes` command in OpenCode to automatically detect and log mistakes from recent AI-generated changes.

---

## 2025-01-22 - Initial Implementation

### INFO: Missing MISTAKES.md documentation
- **Location**: `MISTAKES.md:1`
- **Issue**: No structured approach to track AI-generated mistakes
- **Impact**: Repeating similar mistakes across sessions, missed learning opportunities
- **Resolution**: Created MISTAKES.md with timeline format, added `/capture-mistakes` OpenCode command

### ERROR: Type mismatch in announcement_scraper.py
- **Location**: `app/analysis/announcement_scraper.py:28`
- **Issue**: Assigning int to str variable causes incompatible types
- **Impact**: Runtime error, scraper would crash when processing data
- **Resolution**: Ensure string conversion when assigning integer values to string variables

### WARNING: Missing ScanStatus parameters
- **Location**: `app/scanner/scanner.py:38`
- **Issue**: ScanStatus called without required parameters (last_scan_time, last_scan_results, active_scans)
- **Impact**: Scanner would fail to initialise, missing status tracking
- **Resolution**: Pass all required parameters when creating ScanStatus instance

### INFO: Missing type annotation
- **Location**: `app/gateway_scanner.py:21`
- **Issue**: Variable _scanner_callbacks lacks type annotation
- **Impact**: Reduced code clarity, harder for static analysis tools
- **Resolution**: Add type annotation: `_scanner_callbacks: dict[<type>, <type>]`
