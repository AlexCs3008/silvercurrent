# 0004 — System prompts live as markdown files, loaded at runtime

*Status: accepted · 2026-05-04*

## Context

Each runtime agent (Router, Operator, Analyst, Optimizer) has a system prompt. Prompts evolve: as we add tools, fix failure modes, tune tone, or expand the knowledge base, the prompt is the most-edited surface in the codebase. Where they live and how they're loaded shapes how easy it is to iterate.

The two natural options:

1. Inline as Python string constants in the agent module (`ROUTER_PROMPT = """..."""`).
2. External `.md` files loaded at runtime (`prompts/router.md`).

## Decision

Each agent's system prompt is a separate `.md` file under `backend/src/silvercurrent/agents/prompts/`:

```
backend/src/silvercurrent/agents/prompts/
├── router.md
├── operator.md
├── analyst.md
└── optimizer.md
```

Loaded at module import via a small helper: `load_prompt("router")` reads the file and caches the string. Edits to a prompt require nothing more than a re-import (or process restart in dev).

Prompts may use simple `{placeholder}` substitution for runtime context (e.g., `{user_criteria}`) — substituted with `str.format` at call time, not at load time. No template engine, no Jinja.

## Consequences

**Good**

- Prompts are the most-edited surface; treating them as first-class files (with their own diffs, line numbers, and review history) makes prompt evolution legible. A blame on `prompts/operator.md` line 47 tells you why a clause exists.
- Markdown rendering in editors and on GitHub means structured prompts (headers, lists, tables) read naturally without escaping.
- Non-Python contributors (or Claude Code in a `prompt-tuner` session) can edit prompts without touching code paths.
- Eval harnesses can A/B test prompts by swapping file contents — no code change.
- Separates prompt content from orchestration logic. The agent module stays small and focused on tool wiring.

**Trade-offs**

- Two files to coordinate when adding an agent (the `.py` + the `.md`) instead of one. Negligible.
- Runtime file I/O on first import. Cached after, so it's irrelevant.
- Tests must remember to read the real prompt file or mock it. We mock at the call boundary, not the load boundary, so this stays clean.

## Conventions

- Prompts use markdown headers and lists, but should be tested for rendering — Anthropic models handle markdown well, but verify on each major edit.
- `{placeholder}` substitution is documented in a comment block at the top of each prompt file: `<!-- placeholders: {user_criteria}, {active_listing_summary} -->`.
- No conditional logic inside prompts — if behavior should differ between modes (Analyst conversational vs. batch), use two prompt files (`analyst-conversational.md`, `analyst-batch.md`) and pick at call time.
