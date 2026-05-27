"""TASK-3: Grid image detection tests."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from nails_agent.tools.fetchers.xhs_mcp_fetcher import XHSMCPFetcher


def _make_image(tmp_path: Path, name: str, size: tuple[int, int]) -> Path:
    p = tmp_path / name
    Image.new("RGB", size).save(p)
    return p


def test_grid_image_wide(tmp_path: Path):
    p = _make_image(tmp_path, "wide.png", (3000, 1000))
    assert XHSMCPFetcher._is_grid_image(p) is True


def test_grid_image_tall(tmp_path: Path):
    p = _make_image(tmp_path, "tall.png", (400, 1200))
    assert XHSMCPFetcher._is_grid_image(p) is True


def test_single_nail_not_filtered(tmp_path: Path):
    p = _make_image(tmp_path, "normal.png", (800, 1200))
    assert XHSMCPFetcher._is_grid_image(p) is False


def test_square_not_filtered(tmp_path: Path):
    p = _make_image(tmp_path, "square.png", (1000, 1000))
    assert XHSMCPFetcher._is_grid_image(p) is False


def test_nonexistent_file(tmp_path: Path):
    assert XHSMCPFetcher._is_grid_image(tmp_path / "nope.png") is False
