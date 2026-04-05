#!/usr/bin/env python3
"""Tests for penrose_tiling_poster module."""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from penrose_tiling_poster import (
    create_initial_wheel,
    subdivide_triangles,
    generate_penrose_tiling,
    generate_poster,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# create_initial_wheel
# ---------------------------------------------------------------------------

class TestCreateInitialWheel:
    def test_returns_ten_triangles(self):
        tris = create_initial_wheel(0, 0, 100)
        assert len(tris) == 10

    def test_all_type_thin(self):
        tris = create_initial_wheel(0, 0, 100)
        for tri_type, a, b, c in tris:
            assert tri_type == 0  # THIN

    def test_vertices_are_tuples(self):
        tris = create_initial_wheel(0, 0, 100)
        for _, a, b, c in tris:
            assert len(a) == 2 and len(b) == 2 and len(c) == 2


# ---------------------------------------------------------------------------
# subdivide_triangles
# ---------------------------------------------------------------------------

class TestSubdivideTriangles:
    def test_thin_produces_two(self):
        """A single THIN triangle should produce 2 sub-triangles."""
        tris = [(0, (0, 0), (1, 0), (0.5, 0.866))]
        result = subdivide_triangles(tris)
        assert len(result) == 2

    def test_thick_produces_three(self):
        """A single THICK triangle should produce 3 sub-triangles."""
        tris = [(1, (0, 0), (1, 0), (0.5, 0.866))]
        result = subdivide_triangles(tris)
        assert len(result) == 3

    def test_triangle_count_grows(self):
        """Subdivision increases triangle count."""
        tris = create_initial_wheel(0, 0, 100)
        count_before = len(tris)
        tris = subdivide_triangles(tris)
        assert len(tris) > count_before


# ---------------------------------------------------------------------------
# generate_penrose_tiling
# ---------------------------------------------------------------------------

class TestGeneratePenroseTiling:
    def test_returns_list_of_tuples(self):
        tris = generate_penrose_tiling(0, 0, 100, 2)
        assert isinstance(tris, list)
        assert len(tris) > 0
        tri_type, a, b, c = tris[0]
        assert tri_type in (0, 1)

    def test_more_subdivisions_more_triangles(self):
        t1 = generate_penrose_tiling(0, 0, 100, 1)
        t2 = generate_penrose_tiling(0, 0, 100, 3)
        assert len(t2) > len(t1)


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(subdivisions=2, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_tiling_group(self):
        svg = generate_poster(subdivisions=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='penrose-tiling']")
        assert grp is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(subdivisions=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert grp is not None

    def test_contains_educational_group(self):
        svg = generate_poster(subdivisions=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert grp is not None

    def test_tiling_has_polygons(self):
        svg = generate_poster(subdivisions=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='penrose-tiling']")
        polys = grp.findall(f"{{{ns}}}polygon")
        assert len(polys) >= 1

    def test_default_dimensions(self):
        svg = generate_poster(subdivisions=2)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(subdivisions=2, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(subdivisions=2, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Penrose" in xml_str

    def test_educational_text_present(self):
        svg = generate_poster(subdivisions=2, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Quasicrystal" in xml_str or "quasicrystal" in xml_str

    def test_title_present(self):
        svg = generate_poster(subdivisions=2, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Penrose Tiling" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(subdivisions=2, width_mm=100, height_mm=150)
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
        svg = generate_poster(subdivisions=2, width_mm=100, height_mm=150)
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
