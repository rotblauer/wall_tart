#!/usr/bin/env python3
"""Tests for spectre_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from spectre_poster import (
    SPECTRE_VERTICES,
    _SPECTRE_GRID_COORDS,
    _hex_to_cart,
    _signed_area,
    verify_chirality,
    generate_spectre_tiling,
    generate_poster,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# Spectre vertex geometry
# ---------------------------------------------------------------------------

class TestSpectreVertices:
    def test_exactly_14_vertices(self):
        assert len(SPECTRE_VERTICES) == 14

    def test_exactly_14_grid_coords(self):
        assert len(_SPECTRE_GRID_COORDS) == 14

    def test_all_edges_equal_length(self):
        """Every consecutive edge (including wrap-around) should have length 1."""
        for i in range(14):
            x0, y0 = SPECTRE_VERTICES[i]
            x1, y1 = SPECTRE_VERTICES[(i + 1) % 14]
            length = math.hypot(x1 - x0, y1 - y0)
            assert abs(length - 1.0) < 1e-9, (
                f"Edge {i}→{(i+1)%14} has length {length}, expected 1.0"
            )

    def test_is_chiral(self):
        """The signed area of the original and reflected tile must differ."""
        assert verify_chirality(SPECTRE_VERTICES)

    def test_hex_to_cart(self):
        """Check a few known hex→Cartesian conversions."""
        assert _hex_to_cart(0, 0) == (0.0, 0.0)
        x, y = _hex_to_cart(1, 0)
        assert abs(x - 1.0) < 1e-9 and abs(y) < 1e-9
        x, y = _hex_to_cart(0, 1)
        assert abs(x - 0.5) < 1e-9
        assert abs(y - math.sqrt(3) / 2) < 1e-9

    def test_vertex_cartesian_values(self):
        """Spot-check several Cartesian vertex positions."""
        # Vertex 0: (0,0) → (0, 0)
        assert abs(SPECTRE_VERTICES[0][0]) < 1e-9
        assert abs(SPECTRE_VERTICES[0][1]) < 1e-9
        # Vertex 3: (3,0) → (3, 0)
        assert abs(SPECTRE_VERTICES[3][0] - 3.0) < 1e-9
        assert abs(SPECTRE_VERTICES[3][1]) < 1e-9
        # Vertex 13: (0,1) → (0.5, √3/2)
        assert abs(SPECTRE_VERTICES[13][0] - 0.5) < 1e-9
        assert abs(SPECTRE_VERTICES[13][1] - math.sqrt(3) / 2) < 1e-9


# ---------------------------------------------------------------------------
# Tiling generation
# ---------------------------------------------------------------------------

class TestGenerateSpectreTiling:
    def test_returns_list(self):
        tiles = generate_spectre_tiling(0, 0, 10, 2)
        assert isinstance(tiles, list)
        assert len(tiles) > 0

    def test_more_iterations_more_tiles(self):
        t1 = generate_spectre_tiling(0, 0, 10, 2)
        t2 = generate_spectre_tiling(0, 0, 10, 5)
        assert len(t2) > len(t1)

    def test_minimum_150_tiles(self):
        tiles = generate_spectre_tiling(0, 0, 10, 8)
        assert len(tiles) >= 150, f"Only {len(tiles)} tiles generated"

    def test_tiles_are_14_vertex_polygons(self):
        tiles = generate_spectre_tiling(0, 0, 10, 3)
        for tile in tiles:
            assert len(tile) == 14


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_tiling_group(self):
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='spectre-tiling']")
        assert grp is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert grp is not None

    def test_contains_educational_group(self):
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert grp is not None

    def test_tiling_has_polygons(self):
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='spectre-tiling']")
        polys = grp.findall(f"{{{ns}}}polygon")
        assert len(polys) >= 1

    def test_default_dimensions(self):
        svg = generate_poster(iterations=3)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(iterations=3, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(iterations=3, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Spectre" in xml_str

    def test_title_present(self):
        svg = generate_poster(iterations=3, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Spectre" in xml_str
        assert "Monotile" in xml_str

    def test_theme_support(self):
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150,
                              theme="blueprint")
        assert svg.tag.endswith("svg")


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150)
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
        svg = generate_poster(iterations=3, width_mm=100, height_mm=150)
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
