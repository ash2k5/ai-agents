# changelog

## 0.1.0 (2026-06-06)

- commerce assistant on google adk + gemini: product, payment-fee, and currency lookups,
  per-session memory, and shipping orders.
- human-in-the-loop approval for large orders on a resumable app, with sqlite-backed
  sessions that survive a restart.
- runnable examples for the approval, memory, and mcp features.
- offline tests for the tools, config, and approval helpers, plus an end-to-end approval
  pause/resume through a real adk runner.
- config via env vars: `GOOGLE_API_KEY`, and the optional `GOOGLE_MODEL`, `ADK_DB_PATH`,
  and `LARGE_ORDER_THRESHOLD`.
