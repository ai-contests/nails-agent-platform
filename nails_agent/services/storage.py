"""Small JSON/image storage helpers for local demo data files."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("NAILS_DATA_DIR_V2", str(ROOT_DIR / "data")))


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def data_path(name: str | Path) -> Path:
    path = Path(name)
    if path.is_absolute():
        return path
    if path.suffix:
        return DATA_DIR / path
    return DATA_DIR / f"{path}.json"


def read_data(name: str | Path) -> list[dict[str, Any]]:
    path = data_path(name)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    data = json.loads(text)
    return data if isinstance(data, list) else []


def write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def image_path(path_or_url: str | Path) -> Path:
    path = Path(str(path_or_url))
    if path.is_absolute():
        return path
    for candidate in (
        Path.cwd() / path,
        ROOT_DIR / path,
        DATA_DIR / path,
        ROOT_DIR / "consumer" / path,
        ROOT_DIR / "web" / path,
    ):
        if candidate.exists():
            return candidate
    return ROOT_DIR / path
