# ai-agents

a small commerce assistant built on google's agent development kit (adk). it answers
questions about products, payment fees, and currency, remembers who it's talking to, and
places shipping orders. orders above a set size pause for human approval first.

## layout

- `ai_agents/`: the agent (config, tools, the agent definition, the resumable app, and
  the approval helpers).
- `examples/`: standalone scripts for the approval, memory, and mcp features.
- `tests/`: offline tests that run without calling the model.

## setup

needs python 3.10+ and a gemini api key from https://aistudio.google.com/apikey.

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env   # then add your key
```

## run

```bash
adk web            # browser ui, pick "ai_agents"
adk run ai_agents  # terminal chat
```

ask it things like "what's the price of a macbook pro 14?" or "ship 10 containers to
rotterdam"; the second one waits for your approval. sessions persist in sqlite, so an
order awaiting approval survives a restart (the db lives in a per-user data dir; set
`ADK_DB_PATH` to override).

the example scripts read `GOOGLE_API_KEY` from the shell:

```bash
export GOOGLE_API_KEY=...
python examples/approval_agent.py
python examples/memory_agent.py
python examples/mcp_agent.py   # also needs node/npx and the .[mcp] extra
```

## tests

```bash
uv run pytest
uv run ruff check .
```

MIT.
