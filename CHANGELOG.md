# Changelog

All notable changes to this project are recorded here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-06

### Added
- Commerce assistant on Google ADK + Gemini: product, payment-fee, and currency
  lookups, per-session user memory, and shipping orders.
- Human-in-the-loop approval for large orders on a resumable app, with SQLite-backed
  sessions that survive a restart.
- Runnable examples for the approval, memory, and MCP capabilities.
- Offline test suite covering the tools, config, and approval helpers, plus an
  end-to-end approval pause/resume driven through a real ADK Runner.
- Configuration via environment variables: `GOOGLE_API_KEY`, and the optional
  `GOOGLE_MODEL` (validated at startup), `ADK_DB_PATH`, and `LARGE_ORDER_THRESHOLD`.
