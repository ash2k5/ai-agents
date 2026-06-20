# 1. flat package layout, no src/

- Status: accepted
- Date: 2026-06-20

## Context
ai-agents runs as an app (the `adk web` / `adk run` demo and an optional MCP server). It is not
published to PyPI. The src layout mainly helps published packages, where it stops tests importing the
working copy instead of the installed one.

## Decision
Keep the package at the repo root as `ai_agents/`, with `tests/` and `examples/` alongside. The
pyproject hatchling build points at that package.

## Consequences
Imports and paths stay flat. If this is ever published, move to `src/ai_agents/` for the import
isolation.
