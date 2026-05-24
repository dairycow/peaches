# dairycow/peaches — Archived

> **This repository has been archived. All functionality has been migrated to:**

> **[mktmind/profiles](https://github.com/mktmind/profiles)**

## Migration Summary

The ASX announcement scraping, real-time scanning, and event-driven analysis code from this repository has been consolidated into the `mktmind/profiles` repository under the following structure:

| Original (peaches) | New Location (profiles) |
|---|---|
| `app/analysis/models.py` | `src/schemas/announcements.py` |
| `app/analysis/parsing.py` | `src/schemas/normalisers.py` |
| `app/analysis/announcement_scraper.py` | `src/announcements/historical.py` |
| `app/scanners/asx/announcements.py` | `src/announcements/scanner.py` |
| `app/events/bus.py` | `src/events/integration.py` |
| `app/cli/analysis_cli.py` | `src/cli.py` |

## What Was Moved

- **Pydantic models and normalisers** — Unified `Announcement`, `AnnouncementResult`, and shared normalisers
- **Historical scraper** — Multi-year, per-company announcement fetching with caching
- **Real-time scanner** — Daily price-sensitive announcement scanning
- **Event bus and pipeline** — Event-driven announcement classification
- **Deterministic classifiers** — ASX form parsers (603/604/605, 3X/3Y, 4D/4E, 5B)
- **CLI tools** — Unified command-line interface

## What Was Not Migrated

- **Gap scanning and backtesting** — These components depended on external databases (CoolTrader) and are not part of the company profiling workflow. If you need these, they can be extracted and re-architected as a separate strategy framework.

## Documentation

Updated architecture documentation is available in the profiles repo:

- **Architecture**: [mktmind/profiles/docs/architecture.md](https://github.com/mktmind/profiles/blob/main/docs/architecture.md)

## Migration Date

2024-05-24

## Contact

For questions about the migration or the new codebase, refer to the [mktmind/profiles](https://github.com/mktmind/profiles) repository.