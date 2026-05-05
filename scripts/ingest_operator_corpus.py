"""CLI for re-indexing the Operator agent's knowledge base.

Run from the repo root:

    cd backend
    uv run python ../scripts/ingest_operator_corpus.py [--rebuild]

Reads source files from `corpus/operator/` (relative to the repo root),
chunks them, and writes vectors to the Chroma collection named `operator`
under `Settings.chroma_persist_dir`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from silvercurrent.config import get_settings
from silvercurrent.ingestion.corpus import ingest_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus" / "operator"


def main() -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Ingest the Operator knowledge base into Chroma.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop the existing collection and re-index from scratch (vs. upserting).",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=CORPUS_DIR,
        help=f"Directory of source files to ingest (default: {CORPUS_DIR}).",
    )
    args = parser.parse_args()

    if not args.corpus_dir.exists():
        print(f"error: corpus dir does not exist: {args.corpus_dir}", file=sys.stderr)
        return 2

    settings = get_settings()
    # Resolve `chroma_persist_dir` against the repo root. Strip a single
    # leading `./` if present (without lstrip, which would eat the leading dot
    # of `.chroma`).
    raw = settings.chroma_persist_dir
    relative = raw[2:] if raw.startswith("./") else raw
    persist_dir = (REPO_ROOT / relative).resolve()

    print(f"Ingesting from {args.corpus_dir}")
    print(f"Persisting to  {persist_dir}")
    print(f"Collection     operator")
    print(f"Rebuild        {args.rebuild}")
    print()

    stats = ingest_corpus(
        corpus_dir=args.corpus_dir,
        persist_dir=persist_dir,
        collection_name="operator",
        rebuild=args.rebuild,
    )

    print(f"Done.  files: {stats.files_processed} processed, {stats.files_skipped} skipped")
    print(f"       chunks: {stats.chunks_created} created ({stats.total_chars:,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
