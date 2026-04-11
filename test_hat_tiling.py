#!/usr/bin/env python3
"""Tests for hat_tiling_poster module."""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from hat_tiling_poster import (
    generate_hat_tiling,
    generate_poster,
    render_hat_tiles,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# generate_hat_tiling
# ---------------------------------------------------------------------------

class TestGenerateHatTiling:
    def test_returns_list_of_tuples(self):
        tiles = generate_hat_tiling(1)
        assert isinstance(tiles, list)
        assert len(tiles) > 0

    def test_each_tile_has_position_and_reflected_flag(self):
        tiles = generate_hat_tiling(1)
        for item in tiles:
            assert isinstance(item, (list, tuple))
            assert len(item) >= 3
            # Last element should be a bool (reflected flag)
            assert isinstance(item[-1], bool)

    def test_more_iterations_more_tiles(self):
        t1 = generate_hat_tiling(1)
        t2 = generate_hat_tiling(2)
        assert len(t2) > len(t1)

    def test_zero_iterations(self):
        tiles = generate_hat_tiling(0)
        assert isinstance(tiles, list)
        assert len(tiles) > 0


# ---------------------------------------------------------------------------
# render_hat_tiles
# ---------------------------------------------------------------------------

class TestRenderHatTiles:
    def test_returns_clipped_tiles(self):
        tiles = generate_hat_tiling(1)
        rendered = render_hat_tiles(tiles, 100, 100, 5, 200, 200)
        assert isinstance(rendered, list)
        assert len(rendered) > 0

    def test_rendered_tiles_have_points_and_flag(self):
        tiles = generate_hat_tiling(1)
        rendered = render_hat_tiles(tiles, 100, 100, 5, 200, 200)
        for item in rendered:
            assert isinstance(item, (list, tuple))
            assert len(item) >= 2


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(iterations=1, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_tiling_group(self):
        svg = generate_poster(iterations=1, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='hat-tiling']")
        assert grp is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(iterations=1, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert grp is not None

    def test_contains_educational_group(self):
        svg = generate_poster(iterations=1, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert grp is not None

    def test_tiling_has_polygons(self):
        svg = generate_poster(iterations=1, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='hat-tiling']")
        polys = grp.findall(f"{{{ns}}}polygon")
        assert len(polys) >= 1

    def test_default_dimensions(self):
        svg = generate_poster(iterations=1)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(iterations=1, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(iterations=1, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Einstein" in xml_str or "einstein" in xml_str

    def test_educational_text_present(self):
        svg = generate_poster(iterations=1, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "David Smith" in xml_str or "discovery" in xml_str.lower()

    def test_title_present(self):
        svg = generate_poster(iterations=1, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Hat" in xml_str

    def test_theme_support(self):
        for theme in ["classic", "blueprint", "chalkboard"]:
            svg = generate_poster(iterations=1, width_mm=100, height_mm=150,
                                  theme=theme)
            assert svg.tag.endswith("svg")


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(iterations=1, width_mm=100, height_mm=150)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            write_svg(svg, path)
            assert os.path.getsize(path) > 0
            tree = ET.parse(path)
            root = tree.getroot()
            assert root.tag.endswith("svg")
        finally:
            os.unlink(path)


class TestWritePng:
    def test_writes_png_file(self):
        cairosvg = pytest.importorskip("cairosvg")  # noqa: F841
        svg = generate_poster(iterations=1, width_mm=100, height_mm=150)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            write_png(svg, path, dpi=72)
            assert os.path.getsize(path) > 0
            with open(path, "rb") as fh:
                header = fh.read(8)
            assert header == b"\x89PNG\r\n\x1a\n"
        finally:
            os.unlink(path)
