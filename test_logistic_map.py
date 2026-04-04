#!/usr/bin/env python3
"""Tests for logistic_map_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from logistic_map_poster import (
    bifurcation_data,
    generate_poster,
    logistic_iterate,
    write_png,
    write_svg,
)


# ---------------------------------------------------------------------------
# Logistic iteration
# ---------------------------------------------------------------------------

class TestLogisticIterate:
    def test_length(self):
        xs = logistic_iterate(0.5, 3.5, 100)
        assert len(xs) == 101

    def test_first_value_is_initial(self):
        xs = logistic_iterate(0.4, 3.0, 10)
        assert xs[0] == 0.4

    def test_values_bounded(self):
        """For r in (0, 4] and x0 in (0, 1), iterates stay in [0, 1]."""
        for r in [1.0, 2.5, 3.5, 3.9, 4.0]:
            xs = logistic_iterate(0.5, r, 500)
            for x in xs:
                assert 0.0 <= x <= 1.0, f"x={x} out of [0,1] for r={r}"

    def test_fixed_point_r2(self):
        """At r=2, x converges to 0.5."""
        xs = logistic_iterate(0.1, 2.0, 1000)
        assert abs(xs[-1] - 0.5) < 1e-6

    def test_known_iteration(self):
        """Verify one step: x_{n+1} = r * x_n * (1 - x_n)."""
        x0, r = 0.3, 3.7
        xs = logistic_iterate(x0, r, 1)
        expected = r * x0 * (1.0 - x0)
        assert abs(xs[1] - expected) < 1e-12


# ---------------------------------------------------------------------------
# Bifurcation data
# ---------------------------------------------------------------------------

class TestBifurcationData:
    def test_length(self):
        n_r, n_plot = 50, 20
        pts = bifurcation_data(n_r=n_r, n_plot=n_plot)
        assert len(pts) == n_r * n_plot

    def test_each_point_is_pair(self):
        pts = bifurcation_data(n_r=10, n_plot=5)
        for pt in pts:
            assert len(pt) == 2
            assert all(isinstance(v, float) for v in pt)

    def test_r_range(self):
        r_min, r_max = 2.5, 4.0
        pts = bifurcation_data(r_min=r_min, r_max=r_max, n_r=100, n_plot=10)
        rs = [p[0] for p in pts]
        assert min(rs) >= r_min - 1e-9
        assert max(rs) <= r_max + 1e-9

    def test_x_bounded(self):
        pts = bifurcation_data(n_r=100, n_plot=50)
        for r, x in pts:
            assert 0.0 <= x <= 1.0, f"x={x} out of [0,1] for r={r}"


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(r_count=50, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_diagram_group(self):
        svg = generate_poster(r_count=50, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        diagram = svg.find(f".//{{{ns}}}g[@id='diagram']")
        assert diagram is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(r_count=50, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert annotations is not None

    def test_diagram_has_circles(self):
        """The bifurcation diagram should contain circle elements (dots)."""
        svg = generate_poster(r_count=50, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        diagram = svg.find(f".//{{{ns}}}g[@id='diagram']")
        circles = diagram.findall(f"{{{ns}}}circle")
        assert len(circles) >= 1

    def test_dot_count_matches_data(self):
        """Number of dots should equal r_count * n_plot (200 default)."""
        r_count = 30
        svg = generate_poster(r_count=r_count, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        diagram = svg.find(f".//{{{ns}}}g[@id='diagram']")
        circles = diagram.findall(f"{{{ns}}}circle")
        # Default: n_plot=200, so total dots = r_count * 200
        assert len(circles) == r_count * 200

    def test_default_dimensions(self):
        svg = generate_poster(r_count=50)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(r_count=50, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        """Verify the annotation topics appear in the SVG text."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Period Doubling" in xml_str
        assert "Edge of Chaos" in xml_str
        assert "Windows of Order" in xml_str

    def test_credit_designed_by(self):
        """Credit line appears when --designed-by is supplied."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300,
                              designed_by="Alice")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice" in xml_str

    def test_credit_designed_for(self):
        """Credit line appears when --designed-for is supplied."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300,
                              designed_for="the Science Museum")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed for the Science Museum" in xml_str

    def test_credit_both(self):
        """Credit line combines both designer and client."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300,
                              designed_by="Alice and Bob",
                              designed_for="ACME Labs")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice and Bob for ACME Labs" in xml_str

    def test_no_credit_by_default(self):
        """No credit line appears when neither flag is supplied."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by" not in xml_str

    def test_educational_group_present(self):
        """The educational panels group exists in the SVG."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        edu = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert edu is not None

    def test_educational_text_present(self):
        """All three educational panel topics appear in the SVG."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Equation" in xml_str
        assert "Feigenbaum" in xml_str
        assert "Population Biology" in xml_str

    def test_feigenbaum_constant_present(self):
        """The Feigenbaum constant value appears in the SVG."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "4.669201" in xml_str

    def test_robert_may_footer(self):
        """The footer mentions Robert May."""
        svg = generate_poster(r_count=50, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Robert May" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(r_count=50, width_mm=100, height_mm=150)
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
        svg = generate_poster(r_count=50, width_mm=100, height_mm=150)
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

    def test_writes_png_file_custom_dpi(self):
        cairosvg = pytest.importorskip("cairosvg")  # noqa: F841
        svg = generate_poster(r_count=50, width_mm=100, height_mm=150)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path_low = f.name
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path_high = f.name
        try:
            write_png(svg, path_low, dpi=72)
            write_png(svg, path_high, dpi=144)
            assert os.path.getsize(path_high) > os.path.getsize(path_low)
        finally:
            os.unlink(path_low)
            os.unlink(path_high)
