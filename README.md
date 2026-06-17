# ai-agents

A small commerce assistant built on Google's Agent Development Kit (ADK). It answers
questions about products, payment fees, and currency, remembers who it's talking to, and
places shipping orders. Orders above a set size pause for human approval first.

## Layout

- `ai_agents/`: the agent (config, tools, the agent definition, the resumable app, and the
  approval helpers).
- `examples/`: standalone scripts for the approval, memory, and MCP features.
- `tests/`: offline tests that run without calling the model.

## Setup

Needs Python 3.10+ and a Gemini API key from https://aistudio.google.com/apikey.

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env   # then add your key
```

## Run

```bash
adk web            # browser UI, pick "ai_agents"
adk run ai_agents  # terminal chat
```

Ask it things like "What's the price of a MacBook Pro 14?" or "Ship 10 containers to
Rotterdam"; the second one waits for your approval. Sessions persist in SQLite, so an order
awaiting approval survives a restart (the DB lives in a per-user data dir; set `ADK_DB_PATH`
to override).

The example scripts read `GOOGLE_API_KEY` from the shell:

```bash
export GOOGLE_API_KEY=...
python examples/approval_agent.py
python examples/memory_agent.py
python examples/mcp_agent.py   # also needs Node/npx and the .[mcp] extra
```

## Tests

```bash
uv run pytest
uv run ruff check .
```

MIT.
