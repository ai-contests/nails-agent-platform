from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TEST_MEMORY_DB = Path(tempfile.gettempdir()) / f"nails_agent_pytest_{os.getpid()}.db"
os.environ.setdefault("NAILS_MEMORY_DB_PATH", str(TEST_MEMORY_DB))

SEED_DATA_FILES = (
    ROOT / "data" / "nail_styles_store.json",
    ROOT / "data" / "reference_hand_profiles.json",
    ROOT / "data" / "nail_visual_features.json",
)


@pytest.fixture(scope="session", autouse=True)
def preserve_seed_data_files():
    """Keep tests from leaving tracked demo seed JSON files dirty."""
    if TEST_MEMORY_DB.exists():
        TEST_MEMORY_DB.unlink()
    snapshots = {path: path.read_bytes() if path.exists() else None for path in SEED_DATA_FILES}
    yield
    for path, content in snapshots.items():
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    if TEST_MEMORY_DB.exists():
        TEST_MEMORY_DB.unlink()
