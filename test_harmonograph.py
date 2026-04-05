#!/usr/bin/env python3
"""Tests for harmonograph_poster module."""

import os
import math
import tempfile
import xml.etree.ElementTree as ET

import pytest

from harmonograph_poster import (
    harmonograph,
    lissajous,
    generate_poster,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# harmonograph
# ---------------------------------------------------------------------------

class TestHarmonograph:
    def test_returns_correct_length(self):
        params = [(1, 2, 0, 0.01), (1, 3, 0, 0.01),
                  (1, 2, 0, 0.01), (1, 3, 0, 0.01)]
        pts = harmonograph(100, 0.01, params)
        assert len(pts) == 100

    def test_starts_near_origin_with_zero_phase(self):
        params = [(1, 1, 0, 0), (0, 1, 0, 0),
                  (1, 1, 0, 0), (0, 1, 0, 0)]
        pts = harmonograph(10, 0.001, params)
        assert abs(pts[0][0]) < 0.01
        assert abs(pts[0][1]) < 0.01

    def test_decay_reduces_amplitude(self):
        params = [(1, 1, 0, 0.1), (0, 1, 0, 0),
                  (1, 1, math.pi/2, 0.1), (0, 1, 0, 0)]
        pts = harmonograph(1000, 0.01, params)
        first_r = math.sqrt(pts[0][0]**2 + pts[0][1]**2)
        last_r = math.sqrt(pts[-1][0]**2 + pts[-1][1]**2)
        assert last_r < first_r


# ---------------------------------------------------------------------------
# lissajous
# ---------------------------------------------------------------------------

class TestLissajous:
    def test_returns_correct_length(self):
        pts = lissajous(200, 0.01, 1, 2, 0)
        assert len(pts) == 200

    def test_bounded_output(self):
        pts = lissajous(500, 0.01, 3, 4, 0)
        for x, y in pts:
            assert -1.01 <= x <= 1.01
            assert -1.01 <= y <= 1.01

    def test_one_to_one_with_delta(self):
        """1:1 ratio with delta=pi/2 should produce a circle-like shape."""
        pts = lissajous(1000, 0.01, 1, 1, math.pi/2)
        # All points should be roughly on a unit circle
        for x, y in pts[:628]:  # one full period
            r = math.sqrt(x**2 + y**2)
            assert 0.9 < r < 1.1


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(steps=500, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_harmonograph_group(self):
        svg = generate_poster(steps=500, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='harmonograph']")
        assert grp is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(steps=500, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert grp is not None

    def test_contains_educational_group(self):
        svg = generate_poster(steps=500, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert grp is not None

    def test_default_dimensions(self):
        svg = generate_poster(steps=500)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(steps=500, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(steps=500, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Harmonograph" in xml_str

    def test_lissajous_labels_present(self):
        svg = generate_poster(steps=500, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "1:1" in xml_str or "2:3" in xml_str

    def test_title_present(self):
        svg = generate_poster(steps=500, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Lissajous" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(steps=500, width_mm=100, height_mm=150)
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
        svg = generate_poster(steps=500, width_mm=100, height_mm=150)
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
