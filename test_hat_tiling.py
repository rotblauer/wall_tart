#!/usr/bin/env python3
"""Tests for hat_tiling_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from hat_tiling_poster import (
    HAT_VERTICES,
    _HAT_GRID_COORDS,
    _draw_canonical_hat_legend,
    _hex_to_cart,
    generate_hat_tiling,
    generate_poster,
    render_hat_tiles,
)
from poster_utils import write_png, write_svg, _group


# ---------------------------------------------------------------------------
# Canonical Hat vertices (Smith et al., 2023, arXiv:2303.10798)
# ---------------------------------------------------------------------------

# Expected Cartesian coordinates for each of the 13 canonical vertices.
# Derived from triangular-grid coords using a=(1,0), b=(0.5, sqrt(3)/2).
_SQRT3 = math.sqrt(3)
_CANONICAL_CARTESIAN = [
    (0.0,          0.0          ),   # 1  (0, 0)
    (1.0,          0.0          ),   # 2  (1, 0)
    (2.0,          0.0          ),   # 3  (2, 0)
    (3.5,          _SQRT3 / 2   ),   # 4  (3, 1)
    (4.0,          _SQRT3       ),   # 5  (3, 2)
    (3.5,          3*_SQRT3 / 2 ),   # 6  (2, 3)
    (2.5,          3*_SQRT3 / 2 ),   # 7  (1, 3)
    (1.0,          _SQRT3       ),   # 8  (0, 2)
    (0.0,          _SQRT3       ),   # 9  (-1, 2)
    (-1.5,         _SQRT3 / 2   ),   # 10 (-2, 1)
    (-2.0,         0.0          ),   # 11 (-2, 0)
    (-1.5,        -_SQRT3 / 2   ),   # 12 (-1, -1)
    (-0.5,        -_SQRT3 / 2   ),   # 13 (0, -1)
]

_CANONICAL_GRID = [
    (0, 0), (1, 0), (2, 0), (3, 1),
    (3, 2), (2, 3), (1, 3), (0, 2),
    (-1, 2), (-2, 1), (-2, 0), (-1, -1),
    (0, -1),
]


class TestCanonicalHatVertices:
    def test_exactly_13_vertices(self):
        assert len(HAT_VERTICES) == 13

    def test_exactly_13_grid_coords(self):
        assert len(_HAT_GRID_COORDS) == 13

    def test_grid_coords_match_canonical(self):
        assert _HAT_GRID_COORDS == _CANONICAL_GRID

    def test_cartesian_coords_match_canonical(self):
        for i, ((ex, ey), (ax, ay)) in enumerate(
                zip(_CANONICAL_CARTESIAN, HAT_VERTICES)):
            assert math.isclose(ax, ex, abs_tol=1e-9), (
                f"Vertex {i+1} x: expected {ex:.4f}, got {ax:.4f}"
            )
            assert math.isclose(ay, ey, abs_tol=1e-9), (
                f"Vertex {i+1} y: expected {ey:.4f}, got {ay:.4f}"
            )

    def test_hex_to_cart_basis_vectors(self):
        # a=(1,0) should map to Cartesian (1,0)
        x, y = _hex_to_cart(1, 0)
        assert math.isclose(x, 1.0, abs_tol=1e-9)
        assert math.isclose(y, 0.0, abs_tol=1e-9)
        # b=(0,1) should map to (0.5, sqrt(3)/2)
        x, y = _hex_to_cart(0, 1)
        assert math.isclose(x, 0.5, abs_tol=1e-9)
        assert math.isclose(y, _SQRT3 / 2, abs_tol=1e-9)

    def test_vertex_5_cartesian(self):
        """Spot-check: vertex 5 at grid (3,2) → Cartesian (4, sqrt(3))."""
        x, y = HAT_VERTICES[4]
        assert math.isclose(x, 4.0, abs_tol=1e-9)
        assert math.isclose(y, _SQRT3, abs_tol=1e-9)

    def test_vertex_11_cartesian(self):
        """Spot-check: vertex 11 at grid (-2,0) → Cartesian (-2, 0)."""
        x, y = HAT_VERTICES[10]
        assert math.isclose(x, -2.0, abs_tol=1e-9)
        assert math.isclose(y, 0.0, abs_tol=1e-9)

    def test_vertex_12_cartesian(self):
        """Spot-check: vertex 12 at grid (-1,-1) → Cartesian (-1.5, -sqrt(3)/2)."""
        x, y = HAT_VERTICES[11]
        assert math.isclose(x, -1.5, abs_tol=1e-9)
        assert math.isclose(y, -_SQRT3 / 2, abs_tol=1e-9)

    def test_vertex_13_cartesian(self):
        """Spot-check: vertex 13 at grid (0,-1) → Cartesian (-0.5, -sqrt(3)/2)."""
        x, y = HAT_VERTICES[12]
        assert math.isclose(x, -0.5, abs_tol=1e-9)
        assert math.isclose(y, -_SQRT3 / 2, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Canonical Hat legend
# ---------------------------------------------------------------------------

def _make_svg_parent_helper():
    ns = "http://www.w3.org/2000/svg"
    root = ET.Element(f"{{{ns}}}svg")
    return root, ns


class TestCanonicalHatLegend:
    def test_returns_group_element(self):
        root, ns = _make_svg_parent_helper()
        g = _draw_canonical_hat_legend(root, ns, 100, 100, 60)
        assert g is not None
        assert "}" in g.tag  # namespace-qualified tag

    def test_legend_group_attached_to_parent(self):
        root, ns = _make_svg_parent_helper()
        _draw_canonical_hat_legend(root, ns, 100, 100, 60)
        assert len(list(root)) > 0

    def test_legend_contains_polygon(self):
        root, ns = _make_svg_parent_helper()
        _draw_canonical_hat_legend(root, ns, 100, 100, 60)
        svg_ns = "http://www.w3.org/2000/svg"
        polys = root.findall(f".//{{{svg_ns}}}polygon")
        assert len(polys) >= 1

    def test_legend_contains_vertex_labels(self):
        root, ns = _make_svg_parent_helper()
        _draw_canonical_hat_legend(root, ns, 100, 100, 60)
        svg_ns = "http://www.w3.org/2000/svg"
        texts = root.findall(f".//{{{svg_ns}}}text")
        text_content = " ".join(t.text or "" for t in texts)
        for i in range(1, 14):
            assert str(i) in text_content, f"Missing vertex label {i}"

    def test_legend_contains_grid_coords(self):
        root, ns = _make_svg_parent_helper()
        _draw_canonical_hat_legend(root, ns, 100, 100, 60)
        svg_ns = "http://www.w3.org/2000/svg"
        texts = root.findall(f".//{{{svg_ns}}}text")
        text_content = " ".join(t.text or "" for t in texts)
        assert "(0,0)" in text_content
        assert "(-2,0)" in text_content

    def test_legend_rendered_in_poster(self):
        svg = generate_poster(iterations=1, width_mm=200, height_mm=300,
                              verbose=False)
        ns = "http://www.w3.org/2000/svg"
        legend = svg.find(f".//{{{ns}}}g[@id='canonical-hat-legend-inset']")
        assert legend is not None

    def test_legend_theme_support(self):
        for theme in ["classic", "blueprint", "chalkboard"]:
            root, ns = _make_svg_parent_helper()
            g = _draw_canonical_hat_legend(root, ns, 100, 100, 60, theme=theme)
            assert g is not None


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
