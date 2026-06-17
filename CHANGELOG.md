# Changelog

## 0.1.0 (2026-06-06)

- Commerce assistant on Google ADK + Gemini: product, payment-fee, and currency lookups,
  per-session memory, and shipping orders.
- Human-in-the-loop approval for large orders on a resumable app, with SQLite-backed sessions
  that survive a restart.
- Runnable examples for the approval, memory, and MCP features.
- Offline tests for the tools, config, and approval helpers, plus an end-to-end approval
  pause/resume through a real ADK Runner.
- Config via env vars: `GOOGLE_API_KEY`, and the optional `GOOGLE_MODEL`, `ADK_DB_PATH`, and
  `LARGE_ORDER_THRESHOLD`.
