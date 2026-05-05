"""Analyst agent stub — see `docs/agents/agent-topology.md` §4.

Tool-heavy agent that runs valuation, financing, projection, and risk analysis
on a specific listing. Two modes: conversational, and user-triggered batch
(produces a Deal Sheet).
"""

from __future__ import annotations


class AnalystAgent:
    """Deal-specific analysis agent. All numerical claims come from tool calls."""
