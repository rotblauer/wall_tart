#!/usr/bin/env python3
"""Tests for koch_snowflake_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from koch_snowflake_poster import (
    koch_curve_points,
    koch_snowflake_points,
    generate_poster,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# koch_curve_points
# ---------------------------------------------------------------------------

class TestKochCurvePoints:
    def test_depth_zero_returns_start_point(self):
        pts = koch_curve_points((0, 0), (1, 0), 0)
        # Returns [start] (endpoint excluded to avoid duplication in snowflake)
        assert len(pts) >= 1

    def test_depth_one_returns_four_points(self):
        pts = koch_curve_points((0, 0), (1, 0), 1)
        # 4 points per edge segment (endpoint excluded)
        assert len(pts) == 4

    def test_depth_increases_point_count(self):
        pts1 = koch_curve_points((0, 0), (1, 0), 1)
        pts2 = koch_curve_points((0, 0), (1, 0), 2)
        assert len(pts2) > len(pts1)

    def test_points_are_tuples(self):
        pts = koch_curve_points((0, 0), (3, 0), 1)
        for p in pts:
            assert len(p) == 2

    def test_start_point_preserved(self):
        p1 = (0, 0)
        pts = koch_curve_points(p1, (3, 0), 2)
        assert abs(pts[0][0] - p1[0]) < 1e-9
        assert abs(pts[0][1] - p1[1]) < 1e-9

    def test_bump_points_outward_for_horizontal_segment(self):
        """For a left-to-right horizontal segment the Koch bump must be above
        the baseline (negative y in SVG coords), i.e. pointing outward."""
        # depth=1: points are [p1, a, peak, c]; endpoint p2 excluded
        pts = koch_curve_points((0, 0), (3, 0), 1)
        peak = pts[2]
        assert abs(peak[0] - 1.5) < 1e-9            # peak is horizontally centred
        assert peak[1] < 0                            # above baseline (outward)


# ---------------------------------------------------------------------------
# koch_snowflake_points
# ---------------------------------------------------------------------------

class TestKochSnowflakePoints:
    def test_depth_zero_returns_triangle(self):
        pts = koch_snowflake_points(0, 0, 100, 0)
        assert len(pts) == 3

    def test_depth_one_point_count(self):
        # 3 edges, each with 4^1 + 1 = 5 points, shared endpoints:
        # 3 * 4^1 = 12 points
        pts = koch_snowflake_points(0, 0, 100, 1)
        assert len(pts) == 12

    def test_more_depth_more_points(self):
        p1 = koch_snowflake_points(0, 0, 100, 1)
        p2 = koch_snowflake_points(0, 0, 100, 3)
        assert len(p2) > len(p1)

    def test_returns_list_of_tuples(self):
        pts = koch_snowflake_points(0, 0, 100, 2)
        assert isinstance(pts, list)
        for p in pts:
            assert len(p) == 2

    def test_bumps_extend_beyond_circumradius(self):
        """At depth>=1 the Koch bumps add area, so the enclosed area of the
        snowflake must exceed the area of the base triangle (depth 0).
        Verified via the shoelace formula."""
        import math as _math

        def shoelace(pts):
            n = len(pts)
            area = 0.0
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                area += x1 * y2 - x2 * y1
            return abs(area) / 2.0

        radius = 100.0
        area0 = shoelace(koch_snowflake_points(0, 0, radius, 0))
        area1 = shoelace(koch_snowflake_points(0, 0, radius, 1))
        assert area1 > area0, (
            f"Depth-1 area ({area1:.2f}) is not larger than depth-0 area "
            f"({area0:.2f}); bumps may be pointing inward (anti-snowflake)."
        )


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_fractal_group(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='fractal']")
        assert grp is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert grp is not None

    def test_contains_educational_group(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert grp is not None

    def test_fractal_has_polygon(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='fractal']")
        polys = grp.findall(f"{{{ns}}}polygon")
        assert len(polys) >= 1

    def test_default_dimensions(self):
        svg = generate_poster(depth=2)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(depth=2, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(depth=2, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Koch" in xml_str

    def test_dimension_value_present(self):
        svg = generate_poster(depth=2, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "1.26" in xml_str  # Hausdorff dimension ≈ 1.2619

    def test_title_present(self):
        svg = generate_poster(depth=2, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Koch Snowflake" in xml_str

    def test_theme_support(self):
        for theme in ["classic", "blueprint", "chalkboard"]:
            svg = generate_poster(depth=2, width_mm=100, height_mm=150,
                                  theme=theme)
            assert svg.tag.endswith("svg")


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
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
        svg = generate_poster(depth=2, width_mm=100, height_mm=150)
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
