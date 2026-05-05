"""Operator agent stub — see `docs/agents/agent-topology.md` §3.

Knowledge-base-heavy agent answering "how do I buy" questions over a curated
ETA corpus (search-fund primer, Buy Then Build, SBA SOP 50 10, etc.).
"""

from __future__ import annotations


class OperatorAgent:
    """ETA-knowledge agent backed by a Chroma RAG corpus."""
