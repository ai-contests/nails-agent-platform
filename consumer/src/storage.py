"""Storage helpers for consumer-side modules.

Minimal stub providing what `nail_feature_extractor` needs:
  - DATA_DIR / IMAGES_DIR / UPLOADS_DIR  Path constants
  - image_path(name)  → resolves an image identifier to an absolute Path
  - read_data(name)   → loads `data/<name>.json` as parsed JSON
  - write_json(path, payload) → atomic-ish JSON write
  - now_iso()         → UTC+8 ISO timestamp

A teammate may replace this with a more capable version later; the public
surface above must stay stable.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_TZ8 = timezone(timedelta(hours=8))

# Anchor at the consumer/ package directory (one level above src/).
_CONSUMER_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _CONSUMER_ROOT / "data"
IMAGES_DIR = _CONSUMER_ROOT / "images"
UPLOADS_DIR = _CONSUMER_ROOT / "uploads"


def now_iso() -> str:
    return datetime.now(_TZ8).isoformat(timespec="seconds")


def image_path(name: str | Path) -> Path:
    """Resolve an image identifier to an absolute Path on disk.

    Accepts:
      - an absolute path (returned as-is if it exists)
      - a relative path like "images/foo.png" or "uploads/UHI001.png"
      - a bare filename — searched in uploads/ then images/
    """
    p = Path(name)
    if p.is_absolute():
        return p
    for base in (_CONSUMER_ROOT, UPLOADS_DIR, IMAGES_DIR):
        candidate = base / p
        if candidate.exists():
            return candidate
    # Last resort: return the bare-filename path under uploads/ so the caller
    # gets a sensible error message via Image.open.
    return UPLOADS_DIR / p


def read_data(name: str) -> Any:
    """Load `consumer/data/<name>.json` and return the parsed object."""
    path = DATA_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, payload: Any) -> None:
    """Write JSON to disk, creating parent dirs as needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
