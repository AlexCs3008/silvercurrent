"""Router agent stub — see `docs/agents/agent-topology.md` §2.

Classifies an incoming user message and dispatches to a specialist
(Operator, Analyst, or Optimizer). Never answers substantively itself.
"""

from __future__ import annotations


class RouterAgent:
    """Classification-only agent; dispatches to a specialist."""
