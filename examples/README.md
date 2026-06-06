# Examples

Standalone, runnable scripts that each demonstrate one ADK capability. They import the
`ai_agents` package, so run them from the repository root with `GOOGLE_API_KEY` set in
your shell.

| Script | Shows | Extra requirement |
|--------|-------|-------------------|
| `approval_agent.py` | Human-in-the-loop approval on a resumable app (pause/resume for large orders) | none |
| `memory_agent.py` | Cross-session recall via the memory service and the `load_memory` tool | none |
| `mcp_agent.py` | Model Context Protocol tool integration (MCP "everything" server) | Node.js / `npx` on PATH |

```bash
python examples/approval_agent.py
python examples/memory_agent.py
python examples/mcp_agent.py
```
