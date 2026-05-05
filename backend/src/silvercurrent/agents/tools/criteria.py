"""`get_user_criteria` — surface Mr. Alonso's acquisition criteria to the agents."""

from __future__ import annotations

from pathlib import Path

from silvercurrent.agents.tools._envelope import Envelope, fail, ok

_REPO_ROOT = Path(__file__).resolve().parents[5]
_CRITERIA_PATH = _REPO_ROOT / "docs" / "criteria.md"


async def get_user_criteria() -> Envelope:
    """Return the contents of `docs/criteria.md` as text.

    The file may still contain `<TODO>` placeholders — that's fine. The Operator
    is instructed to handle missing values gracefully ("the user hasn't filled
    in their criteria for X yet"). Phase 3 (Analyst) is when real values matter.
    """
    if not _CRITERIA_PATH.exists():
        return fail(f"criteria file not found at {_CRITERIA_PATH}")
    try:
        text = _CRITERIA_PATH.read_text(encoding="utf-8")
    except OSError as e:
        return fail(f"failed to read criteria file: {e}")
    return ok({"criteria_markdown": text, "path": str(_CRITERIA_PATH.relative_to(_REPO_ROOT))})
