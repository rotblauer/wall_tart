#!/usr/bin/env python3
"""Tests for mandelbrot_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from mandelbrot_poster import (
    compute_julia_grid,
    compute_mandelbrot_grid,
    generate_poster,
    julia_escape,
    mandelbrot_escape,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# Mandelbrot escape
# ---------------------------------------------------------------------------

class TestMandelbrotEscape:
    def test_origin_never_escapes(self):
        """c = 0 is in the Mandelbrot set; escape should equal max_iter."""
        assert mandelbrot_escape(0.0, 0.0, max_iter=200) == 200

    def test_far_away_escapes_immediately(self):
        """c = 10 + 10i is far outside the set; should escape in very few iterations."""
        esc = mandelbrot_escape(10.0, 10.0, max_iter=100)
        assert esc < 5

    def test_cardioid_point_in_set(self):
        """c = -0.5 is inside the main cardioid."""
        assert mandelbrot_escape(-0.5, 0.0, max_iter=200) == 200

    def test_known_escape(self):
        """c = 1.0 + 0.0i should escape quickly."""
        esc = mandelbrot_escape(1.0, 0.0, max_iter=100)
        assert 1 <= esc < 10

    def test_return_bounded_by_max_iter(self):
        for c_r, c_i in [(0.0, 0.0), (5.0, 5.0), (-1.0, 0.0)]:
            esc = mandelbrot_escape(c_r, c_i, max_iter=50)
            assert 0 <= esc <= 50


# ---------------------------------------------------------------------------
# Julia escape
# ---------------------------------------------------------------------------

class TestJuliaEscape:
    def test_origin_with_zero_c(self):
        """z=0, c=0 should stay at zero forever."""
        assert julia_escape(0.0, 0.0, 0.0, 0.0, max_iter=100) == 100

    def test_far_away_escapes(self):
        esc = julia_escape(10.0, 10.0, 0.0, 0.0, max_iter=100)
        assert esc < 5

    def test_return_bounded_by_max_iter(self):
        for z_r, z_i in [(0.0, 0.0), (5.0, 5.0), (0.5, 0.5)]:
            esc = julia_escape(z_r, z_i, -0.7, 0.27015, max_iter=50)
            assert 0 <= esc <= 50


# ---------------------------------------------------------------------------
# Mandelbrot grid
# ---------------------------------------------------------------------------

class TestComputeMandelbrotGrid:
    def test_grid_dimensions(self):
        grid = compute_mandelbrot_grid(-2, 1, -1.5, 1.5, width=10, height=8, max_iter=20)
        assert len(grid) == 8
        assert all(len(row) == 10 for row in grid)

    def test_values_bounded(self):
        grid = compute_mandelbrot_grid(-2, 1, -1.5, 1.5, width=5, height=5, max_iter=30)
        for row in grid:
            for val in row:
                assert 0 <= val <= 30

    def test_center_in_set(self):
        """The center of the standard view (near origin) should be in the set."""
        grid = compute_mandelbrot_grid(-0.1, 0.1, -0.1, 0.1, width=3, height=3, max_iter=50)
        # Center pixel
        assert grid[1][1] == 50


# ---------------------------------------------------------------------------
# Julia grid
# ---------------------------------------------------------------------------

class TestComputeJuliaGrid:
    def test_grid_dimensions(self):
        grid = compute_julia_grid(-0.7, 0.27015, -1.5, 1.5, -1.5, 1.5,
                                  width=10, height=8, max_iter=20)
        assert len(grid) == 8
        assert all(len(row) == 10 for row in grid)

    def test_values_bounded(self):
        grid = compute_julia_grid(0.355, 0.355, -1.5, 1.5, -1.5, 1.5,
                                  width=5, height=5, max_iter=30)
        for row in grid:
            for val in row:
                assert 0 <= val <= 30


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_fractal_group(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        fractal = svg.find(f".//{{{ns}}}g[@id='fractal']")
        assert fractal is not None

    def test_contains_julia_sets_group(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        julia = svg.find(f".//{{{ns}}}g[@id='julia_sets']")
        assert julia is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert annotations is not None

    def test_contains_educational_group(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        edu = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert edu is not None

    def test_fractal_has_rectangles(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        fractal = svg.find(f".//{{{ns}}}g[@id='fractal']")
        rects = fractal.findall(f"{{{ns}}}rect")
        assert len(rects) >= 1

    def test_default_dimensions(self):
        svg = generate_poster(resolution=10, max_iter=10)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Self-Similarity" in xml_str
        assert "Escape" in xml_str
        assert "Julia" in xml_str

    def test_educational_text_present(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Equation" in xml_str or "equation" in xml_str
        assert "Complex" in xml_str or "complex" in xml_str

    def test_credit_designed_by(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300,
                              designed_by="Alice")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice" in xml_str

    def test_credit_designed_for(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300,
                              designed_for="the Science Museum")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed for the Science Museum" in xml_str

    def test_credit_both(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300,
                              designed_by="Alice and Bob",
                              designed_for="ACME Labs")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice and Bob for ACME Labs" in xml_str

    def test_no_credit_by_default(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by" not in xml_str

    def test_title_present(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Mandelbrot" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
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


class TestJuliaInlinePlacement:
    """Tests for Julia sets placed in inter-column gaps."""

    def test_four_julia_sets(self):
        """Poster should contain four Julia set insets."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        # All four Julia parameter labels should be present
        assert "\u22120.70 + 0.27i" in xml_str
        assert "0.355 + 0.355i" in xml_str
        assert "\u22120.80 + 0.16i" in xml_str
        assert "0.285 + 0.01i" in xml_str

    def test_footer_mentions_four_insets(self):
        """Footer text should reflect four Julia insets."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "4 Julia set insets" in xml_str

    def test_julia_panels_have_marker_circles(self):
        """Each Julia panel should place a marker circle on the Mandelbrot."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        julia_g = svg.find(f".//{{{ns}}}g[@id='julia_sets']")
        # Each Julia inset draws 3 circles: marker ring, centre dot, terminal dot
        circles = julia_g.findall(f".//{{{ns}}}circle")
        assert len(circles) >= 12  # 3 circles × 4 insets


class TestClipPaths:
    """Tests for SVG clipPath elements that eliminate rectangular grid artifacts."""

    def test_fractal_group_has_clip_path(self):
        """The fractal group should carry a clip-path attribute."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        fractal = svg.find(f".//{{{ns}}}g[@id='fractal']")
        assert fractal is not None
        assert fractal.get("clip-path") is not None

    def test_mandelbrot_clip_path_in_defs(self):
        """SVG defs should contain a clipPath with id 'mandelbrotClip'."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='mandelbrotClip']")
        assert clip is not None

    def test_mandelbrot_clip_contains_ellipse(self):
        """The mandelbrotClip clipPath should contain an ellipse element."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='mandelbrotClip']")
        ellipse = clip.find(f"{{{ns}}}ellipse")
        assert ellipse is not None
        # Ellipse must have valid positive radii
        assert float(ellipse.get("rx")) > 0
        assert float(ellipse.get("ry")) > 0

    def test_julia_clip_paths_in_defs(self):
        """SVG defs should contain one clipPath per Julia inset."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        # Four Julia insets → four juliaClip0..3 clipPath elements
        for idx in range(4):
            clip = svg.find(f".//{{{ns}}}clipPath[@id='juliaClip{idx}']")
            assert clip is not None, f"juliaClip{idx} not found in defs"

    def test_julia_clip_contains_ellipse(self):
        """Each Julia clipPath should contain an ellipse element."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='juliaClip0']")
        ellipse = clip.find(f"{{{ns}}}ellipse")
        assert ellipse is not None
        assert float(ellipse.get("rx")) > 0
        assert float(ellipse.get("ry")) > 0

    def test_total_clip_paths_count(self):
        """SVG should have exactly 5 clipPath elements (1 Mandelbrot + 4 Julia)."""
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        clips = svg.findall(f".//{{{ns}}}clipPath")
        assert len(clips) == 5
    """Tests for edge-fading on the Mandelbrot and Julia grids."""

    def test_julia_grids_have_faded_cells(self):
        """Julia grids rendered with fade_edges should have cells with opacity."""
        svg = generate_poster(resolution=10, max_iter=50, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        julia_g = svg.find(f".//{{{ns}}}g[@id='julia_sets']")
        rects = julia_g.findall(f".//{{{ns}}}rect")
        has_opacity = any(r.get("fill-opacity") is not None for r in rects)
        assert has_opacity

    def test_some_rects_have_fill_opacity(self):
        """Low-escape cells should have a fill-opacity attribute."""
        svg = generate_poster(resolution=15, max_iter=50, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        fractal = svg.find(f".//{{{ns}}}g[@id='fractal']")
        rects = fractal.findall(f"{{{ns}}}rect")
        has_opacity = any(r.get("fill-opacity") is not None for r in rects)
        assert has_opacity


class TestWritePng:
    pytest.importorskip("cairosvg", reason="cairosvg not installed")

    def test_writes_png_file(self):
        cairosvg = pytest.importorskip("cairosvg")  # noqa: F841
        svg = generate_poster(resolution=10, max_iter=10, width_mm=100, height_mm=150)
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
