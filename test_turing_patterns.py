#!/usr/bin/env python3
"""Tests for turing_patterns_poster module."""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from turing_patterns_poster import (
    gray_scott,
    generate_poster,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# gray_scott
# ---------------------------------------------------------------------------

class TestGrayScott:
    def test_grid_dimensions(self):
        v = gray_scott(10, 5, 0.035, 0.065)
        assert len(v) == 10
        assert all(len(row) == 10 for row in v)

    def test_values_are_float(self):
        v = gray_scott(10, 5, 0.035, 0.065)
        for row in v:
            for val in row:
                assert isinstance(val, float)

    def test_nonzero_output(self):
        """After enough steps, v should contain non-zero values."""
        v = gray_scott(10, 100, 0.035, 0.065)
        all_vals = [val for row in v for val in row]
        assert max(all_vals) > 0

    def test_different_parameters_differ(self):
        """Different f/k should give different results."""
        v1 = gray_scott(10, 50, 0.035, 0.065)
        v2 = gray_scott(10, 50, 0.055, 0.062)
        flat1 = [val for row in v1 for val in row]
        flat2 = [val for row in v2 for val in row]
        assert flat1 != flat2


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_patterns_group(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='turing-patterns']")
        assert grp is not None

    def test_contains_panel_groups(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        for name in ["panel-spots", "panel-stripes", "panel-mazes"]:
            grp = svg.find(f".//{{{ns}}}g[@id='{name}']")
            assert grp is not None, f"Missing group: {name}"

    def test_contains_annotations_group(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert grp is not None

    def test_contains_educational_group(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert grp is not None

    def test_panels_have_rectangles(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        for name in ["panel-spots", "panel-stripes", "panel-mazes"]:
            grp = svg.find(f".//{{{ns}}}g[@id='{name}']")
            rects = grp.findall(f"{{{ns}}}rect")
            assert len(rects) >= 1, f"No rectangles in {name}"

    def test_default_dimensions(self):
        svg = generate_poster(grid_size=8, steps=10)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Turing" in xml_str

    def test_educational_text_present(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Gray" in xml_str

    def test_credit_designed_by(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=200, height_mm=300,
                              designed_by="Alice")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice" in xml_str

    def test_credit_designed_for(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=200, height_mm=300,
                              designed_for="the Science Museum")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed for the Science Museum" in xml_str

    def test_title_present(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Turing Patterns" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
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
    pytest.importorskip("cairosvg", reason="cairosvg not installed")

    def test_writes_png_file(self):
        cairosvg = pytest.importorskip("cairosvg")  # noqa: F841
        svg = generate_poster(grid_size=8, steps=10, width_mm=100, height_mm=150)
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
