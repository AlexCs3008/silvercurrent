"""Save uploaded listing documents under `data/listings/{listing_id}/`.

The storage path is relative to the repo root so it survives moves of the
backend working directory. Files are content-addressed by sha256 within the
listing's directory — re-uploading the same file overwrites itself harmlessly
rather than creating duplicates.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

# Resolve to the repo root: __file__ is .../backend/src/silvercurrent/documents/storage.py
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = _REPO_ROOT / "data" / "listings"

# Drop characters that aren't safe in file extensions (path separators, dots
# beyond the leading one, etc.). The actual on-disk name is the sha256 + ext;
# the original filename is kept in the DB row for display.
_EXT_SAFE_RE = re.compile(r"[^a-zA-Z0-9]")


@dataclass(frozen=True)
class StoredFile:
    """Result of `save_uploaded`: relative storage path + integrity metadata."""

    storage_path: str  # relative to repo root, forward slashes
    sha256: str
    byte_size: int


def _safe_extension(filename: str) -> str:
    """Return the original file's extension, sanitized; empty when none."""
    if "." not in filename:
        return ""
    raw = filename.rsplit(".", 1)[1].lower()
    cleaned = _EXT_SAFE_RE.sub("", raw)[:8]
    return f".{cleaned}" if cleaned else ""


def save_uploaded(
    *,
    listing_id: UUID,
    filename: str,
    content: bytes,
) -> StoredFile:
    """Persist `content` under `data/listings/{listing_id}/{sha256}{ext}`."""
    sha = hashlib.sha256(content).hexdigest()
    listing_dir = _DATA_DIR / str(listing_id)
    listing_dir.mkdir(parents=True, exist_ok=True)
    target = listing_dir / f"{sha}{_safe_extension(filename)}"
    target.write_bytes(content)
    relative = target.relative_to(_REPO_ROOT).as_posix()
    return StoredFile(storage_path=relative, sha256=sha, byte_size=len(content))


def absolute_path(storage_path: str) -> Path:
    """Resolve a stored relative path to an absolute filesystem path."""
    return (_REPO_ROOT / storage_path).resolve()


def delete_file(storage_path: str) -> None:
    """Best-effort delete; missing files are silently ignored."""
    p = absolute_path(storage_path)
    with contextlib.suppress(FileNotFoundError):
        p.unlink()


def delete_listing_dir(listing_id: UUID) -> None:
    """Best-effort cleanup of `data/listings/{listing_id}/`. Idempotent."""
    listing_dir = _DATA_DIR / str(listing_id)
    if not listing_dir.exists():
        return
    for child in listing_dir.iterdir():
        with contextlib.suppress(FileNotFoundError, IsADirectoryError):
            child.unlink()
    # Non-empty (e.g., stray subdir) — leave it for manual cleanup if rmdir fails.
    with contextlib.suppress(OSError):
        listing_dir.rmdir()
