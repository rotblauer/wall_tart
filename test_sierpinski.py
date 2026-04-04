#!/usr/bin/env python3
"""Tests for sierpinski_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from sierpinski_poster import (
    equilateral_triangle_vertices,
    generate_poster,
    midpoint,
    sierpinski_triangles,
    write_svg,
)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

class TestMidpoint:
    def test_basic(self):
        assert midpoint((0, 0), (2, 2)) == (1.0, 1.0)

    def test_negative(self):
        assert midpoint((-4, -4), (4, 4)) == (0.0, 0.0)

    def test_same_point(self):
        assert midpoint((5, 5), (5, 5)) == (5.0, 5.0)


class TestEquilateralTriangleVertices:
    def test_vertex_count(self):
        verts = equilateral_triangle_vertices(0, 0, 100)
        assert len(verts) == 3

    def test_side_length(self):
        side = 100
        verts = equilateral_triangle_vertices(0, 0, side)
        for i in range(3):
            a = verts[i]
            b = verts[(i + 1) % 3]
            dist = math.hypot(a[0] - b[0], a[1] - b[1])
            assert abs(dist - side) < 1e-9, f"Side {i} length {dist} != {side}"

    def test_centroid_close_to_center(self):
        cx, cy = 100, 200
        verts = equilateral_triangle_vertices(cx, cy, 50)
        avg_x = sum(v[0] for v in verts) / 3
        avg_y = sum(v[1] for v in verts) / 3
        assert abs(avg_x - cx) < 1e-9
        assert abs(avg_y - cy) < 1e-9


# ---------------------------------------------------------------------------
# Sierpiński triangle generation
# ---------------------------------------------------------------------------

class TestSierpinskiTriangles:
    def test_depth_zero_yields_one(self):
        verts = equilateral_triangle_vertices(0, 0, 100)
        tris = list(sierpinski_triangles(verts, 0))
        assert len(tris) == 1

    def test_depth_one_yields_three(self):
        verts = equilateral_triangle_vertices(0, 0, 100)
        tris = list(sierpinski_triangles(verts, 1))
        assert len(tris) == 3

    def test_depth_n_yields_3_to_the_n(self):
        verts = equilateral_triangle_vertices(0, 0, 100)
        for n in range(6):
            tris = list(sierpinski_triangles(verts, n))
            assert len(tris) == 3**n, f"depth {n}: expected {3**n}, got {len(tris)}"

    def test_each_triangle_has_three_vertices(self):
        verts = equilateral_triangle_vertices(0, 0, 100)
        for tri in sierpinski_triangles(verts, 3):
            assert len(tri) == 3

    def test_deep_depth_does_not_raise(self):
        """Ensure the iterative approach handles deep recursion."""
        verts = equilateral_triangle_vertices(0, 0, 100)
        count = 0
        for _ in sierpinski_triangles(verts, 12):
            count += 1
        assert count == 3**12


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(depth=1, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_fractal_group(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        fractal = svg.find(f".//{{{ns}}}g[@id='fractal']")
        assert fractal is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert annotations is not None

    def test_polygon_count_matches_depth(self):
        depth = 3
        svg = generate_poster(depth=depth, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        fractal = svg.find(f".//{{{ns}}}g[@id='fractal']")
        polygons = fractal.findall(f"{{{ns}}}polygon")
        assert len(polygons) == 3**depth

    def test_default_dimensions(self):
        svg = generate_poster(depth=1)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(depth=1, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        """Verify the three annotation topics appear in the SVG text."""
        svg = generate_poster(depth=2, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Self-Similarity" in xml_str
        assert "Recursion" in xml_str
        assert "Fractional Dimension" in xml_str
        assert "Hausdorff" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(depth=1, width_mm=100, height_mm=150)
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
