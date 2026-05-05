"""Envelope shape returned by every agent tool.

Tools always return an `Envelope` so the calling agent can branch on `ok` and
surface failures to the user instead of silently substituting a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Envelope:
    """Result envelope for a tool call: either successful data or an error."""

    ok: bool
    data: Any | None = None
    error: str | None = None


def ok(data: Any) -> Envelope:
    """Build a successful envelope wrapping `data`."""
    return Envelope(ok=True, data=data, error=None)


def fail(error: str) -> Envelope:
    """Build a failure envelope carrying a user-surfaceable error message."""
    return Envelope(ok=False, data=None, error=error)
