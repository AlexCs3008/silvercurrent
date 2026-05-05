# 0003 — `uv` over Poetry for Python tooling

*Status: accepted · 2026-05-04*

## Context

Python projects in 2026 have several env/dependency tools: `pip` + `venv`, Poetry, Hatch, PDM, and `uv` (from Astral). We need one for the backend and ingestion code. The choice matters because we'll run it dozens of times a session: install a dep, run a test, lint a file.

## Decision

Use `uv` exclusively. All commands flow through it: `uv sync`, `uv add <pkg>`, `uv run pytest`, `uv run ruff check`. No `pip install` directly into venvs, no Poetry, no manual `python -m venv`.

The lockfile is `uv.lock` (committed). `pyproject.toml` is the single source of truth for dependencies, dev dependencies, tool config (ruff, mypy, pytest), and project metadata.

## Consequences

**Good**

- An order of magnitude faster than Poetry on cold install. `uv sync` on a fresh checkout finishes in seconds, not minutes.
- Single binary, written in Rust. No "is Poetry installed?" / "which Python is Poetry using?" rabbit holes.
- Resolves cleanly with `pyproject.toml` standards (PEP 621). No Poetry-specific `[tool.poetry]` lock-in.
- Plays well with Docker layer caching — `uv sync --frozen` is idempotent.
- Built-in `uv run` activates the env transparently for one-off commands, reducing "did I activate the venv?" mistakes.

**Trade-offs**

- Younger ecosystem than Poetry. Some niche tools assume Poetry's directory layout. So far none we depend on.
- Astral could pivot or sunset it. Mitigation: it's a thin layer over standards (`pyproject.toml`, `uv.lock`); migrating off later is a script, not a rewrite.

## Alternatives considered

- **Poetry**: incumbent, mature, but slow and increasingly idiosyncratic. Dependency resolution can take minutes. We'd rather pay the small "young tool" risk for the speed.
- **`pip` + `venv` directly**: simplest but no lockfile by default. Adding `pip-tools` gets us most of the way, but we lose unified install/run ergonomics.
- **PDM**: solid, similar shape to `uv`, but slower and smaller community.

## Operational notes

- CI installs `uv` via the official action.
- `Dockerfile` for the backend uses `uv sync --frozen --no-cache` in an early layer, then copies source after, so dep changes invalidate cache without source changes.
- Project rule: never run `pip install` inside a uv-managed env. Ever.
