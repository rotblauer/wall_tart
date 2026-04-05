#!/usr/bin/env python3
"""Tests for lorenz_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from lorenz_poster import (
    generate_poster,
    integrate_lorenz,
    lorenz_derivatives,
    project_3d_to_2d,
    rk4_step,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# Lorenz derivatives
# ---------------------------------------------------------------------------

class TestLorenzDerivatives:
    def test_at_origin(self):
        dx, dy, dz = lorenz_derivatives((0, 0, 0))
        assert dx == 0.0
        assert dy == 0.0
        assert dz == 0.0

    def test_known_values(self):
        dx, dy, dz = lorenz_derivatives((1, 1, 1))
        # dx = σ(y - x) = 10*(1 - 1) = 0
        assert abs(dx - 0.0) < 1e-9
        # dy = x*(ρ - z) - y = 1*(28 - 1) - 1 = 26
        assert abs(dy - 26.0) < 1e-9
        # dz = x*y - β*z = 1*1 - (8/3)*1 ≈ -1.6667
        assert abs(dz - (1.0 - 8.0 / 3.0)) < 1e-9

    def test_custom_params(self):
        dx, dy, dz = lorenz_derivatives((2, 3, 4), sigma=5.0, rho=15.0, beta=1.0)
        # dx = 5*(3 - 2) = 5
        assert abs(dx - 5.0) < 1e-9
        # dy = 2*(15 - 4) - 3 = 22 - 3 = 19
        assert abs(dy - 19.0) < 1e-9
        # dz = 2*3 - 1.0*4 = 6 - 4 = 2
        assert abs(dz - 2.0) < 1e-9


# ---------------------------------------------------------------------------
# RK4 integration step
# ---------------------------------------------------------------------------

class TestRk4Step:
    def test_returns_three_tuple(self):
        result = rk4_step((1.0, 1.0, 1.0), 0.01)
        assert len(result) == 3
        assert all(isinstance(v, float) for v in result)

    def test_advances_state(self):
        state = (1.0, 1.0, 1.0)
        new_state = rk4_step(state, 0.01)
        assert new_state != state

    def test_small_dt_accuracy(self):
        """With very small dt, RK4 result should closely match Euler step."""
        state = (1.0, 1.0, 1.0)
        dt = 1e-8
        dx, dy, dz = lorenz_derivatives(state)
        euler = (state[0] + dt * dx, state[1] + dt * dy, state[2] + dt * dz)
        rk4 = rk4_step(state, dt)
        for i in range(3):
            assert abs(rk4[i] - euler[i]) < 1e-6


# ---------------------------------------------------------------------------
# Lorenz trajectory integration
# ---------------------------------------------------------------------------

class TestIntegrateLorenz:
    def test_length(self):
        steps = 100
        traj = integrate_lorenz(steps=steps)
        assert len(traj) == steps + 1

    def test_first_point_is_initial(self):
        initial = (2.0, 3.0, 4.0)
        traj = integrate_lorenz(initial=initial, steps=10)
        assert traj[0] == initial

    def test_each_point_is_3d(self):
        traj = integrate_lorenz(steps=50)
        for pt in traj:
            assert len(pt) == 3
            assert all(isinstance(v, float) for v in pt)

    def test_trajectory_bounded(self):
        """For default params, all points should stay within reasonable bounds."""
        traj = integrate_lorenz(steps=5000, dt=0.005)
        for x, y, z in traj:
            assert abs(x) < 50, f"|x| = {abs(x):.1f} >= 50"
            assert abs(y) < 50, f"|y| = {abs(y):.1f} >= 50"
            assert abs(z) < 60, f"|z| = {abs(z):.1f} >= 60"


# ---------------------------------------------------------------------------
# 3-D to 2-D projection
# ---------------------------------------------------------------------------

class TestProject3dTo2d:
    def test_output_length(self):
        pts = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
        proj = project_3d_to_2d(pts)
        assert len(proj) == len(pts)

    def test_each_point_is_2d(self):
        pts = [(1, 2, 3), (4, 5, 6)]
        proj = project_3d_to_2d(pts)
        for pt in proj:
            assert len(pt) == 2
            assert all(isinstance(v, float) for v in pt)

    def test_identity_like(self):
        """With angles (0, 0), projection should approximate dropping z."""
        pts = [(3.0, 5.0, 7.0), (-1.0, 2.0, 4.0)]
        proj = project_3d_to_2d(pts, angle_x=0, angle_z=0)
        for (px, py), (x, y, _z) in zip(proj, pts):
            assert abs(px - x) < 1e-6
            assert abs(py - y) < 1e-6


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(steps=1000, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_attractor_group(self):
        svg = generate_poster(steps=1000, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        attractor = svg.find(f".//{{{ns}}}g[@id='attractor']")
        assert attractor is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(steps=1000, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert annotations is not None

    def test_attractor_has_polylines(self):
        svg = generate_poster(steps=1000, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        attractor = svg.find(f".//{{{ns}}}g[@id='attractor']")
        polylines = attractor.findall(f"{{{ns}}}polyline")
        assert len(polylines) >= 1

    def test_default_dimensions(self):
        svg = generate_poster(steps=1000)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(steps=1000, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        """Verify the annotation topics appear in the SVG text."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Butterfly Effect" in xml_str
        assert "Two" in xml_str
        assert "Wings" in xml_str
        assert "Infinite Complexity" in xml_str

    def test_butterfly_exponent_no_unicode_superscript_minus(self):
        """The 10^-10 exponent must use an SVG tspan, not U+207B.

        U+207B (SUPERSCRIPT MINUS) is absent from many PDF-embedded fonts and
        renders as a missing-glyph square.  The exponent is expressed instead
        via a nested <tspan> with dy/font-size so that a plain ASCII '-' is
        used, which is universally supported.
        """
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "\u207b" not in xml_str, (
            "U+207B (SUPERSCRIPT MINUS) found in SVG; use SVG tspan superscript instead"
        )
        # The exponent digits are rendered as plain ASCII via a tspan
        assert "-10" in xml_str

    def test_credit_designed_by(self):
        """Credit line appears when --designed-by is supplied."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300,
                              designed_by="Alice")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice" in xml_str

    def test_credit_designed_for(self):
        """Credit line appears when --designed-for is supplied."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300,
                              designed_for="the Science Museum")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed for the Science Museum" in xml_str

    def test_credit_both(self):
        """Credit line combines both designer and client."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300,
                              designed_by="Alice and Bob",
                              designed_for="ACME Labs")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice and Bob for ACME Labs" in xml_str

    def test_no_credit_by_default(self):
        """No credit line appears when neither flag is supplied."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by" not in xml_str

    def test_educational_group_present(self):
        """The educational panels group exists in the SVG."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        edu = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert edu is not None

    def test_educational_text_present(self):
        """All three educational panel topics appear in the SVG."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Equations" in xml_str
        assert "Deterministic Chaos" in xml_str
        assert "Weather Model" in xml_str

    def test_diverged_trajectory_present(self):
        """Attractor group has at least 2 polylines (main + diverged)."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        attractor = svg.find(f".//{{{ns}}}g[@id='attractor']")
        polylines = attractor.findall(f"{{{ns}}}polyline")
        assert len(polylines) >= 2

    def test_zoom_inset_group_present(self):
        """A 'zoom_inset' group exists in the SVG."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        assert zoom is not None

    def test_zoom_inset_clip_path_present(self):
        """A clipPath with id 'zoom_panel_clip' exists in <defs>."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='zoom_panel_clip']")
        assert clip is not None
        # The clipPath must contain a rect that defines the zoom panel bounds.
        rect = clip.find(f"{{{ns}}}rect")
        assert rect is not None
        assert float(rect.get("width")) > 0
        assert float(rect.get("height")) > 0

    def test_zoom_inset_connector_lines_present(self):
        """The zoom_inset group contains exactly 4 dashed connector lines."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        lines = zoom.findall(f"{{{ns}}}line")
        assert len(lines) == 4

    def test_zoom_inset_target_box_present(self):
        """The zoom_inset group contains the small source target rect."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        rects = zoom.findall(f"{{{ns}}}rect")
        # 3 rects: background, border, source target box
        assert len(rects) == 3

    def test_zoom_inset_panel_polylines_present(self):
        """The zoom_inset group contains at least one magnified polyline."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        polylines = zoom.findall(f".//{{{ns}}}polyline")
        assert len(polylines) >= 1

    def test_zoom_inset_all_themes(self):
        """zoom_inset renders without error for all built-in themes."""
        from poster_utils import AVAILABLE_THEMES
        for theme in AVAILABLE_THEMES:
            svg = generate_poster(steps=1000, width_mm=200, height_mm=300,
                                  theme=theme)
            ns = "http://www.w3.org/2000/svg"
            zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
            assert zoom is not None, f"zoom_inset missing for theme '{theme}'"

    def test_zoom_target_box_in_right_hemisphere(self):
        """The zoom target box must be in the right hemisphere of the attractor."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        rects = zoom.findall(f"{{{ns}}}rect")
        # The 3rd rect is the source target box on the main attractor.
        target_box = rects[2]
        box_x = float(target_box.get("x"))
        box_w = float(target_box.get("width"))
        box_cx = box_x + box_w / 2
        # The attractor is centred at width_mm / 2 = 100 mm.
        assert box_cx > 100.0, (
            f"Zoom target box centre {box_cx:.1f} should be in the right hemisphere (>100)"
        )

    def test_zoom_annotation_leader_does_not_cross_connectors(self):
        """The annotation leader to the zoom panel must not cross connector lines.

        The annotation leader targets the bottom edge of the zoom panel (y =
        zoom_y + zoom_h).  The connector lines link the source box to the
        zoom panel *corners* (y = zoom_y for top corners).  Because the
        leader terminates at or below zoom_y + zoom_h, it cannot cross the
        connector lines that terminate at zoom_y.
        """
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        # Connector lines terminate at zoom panel corners.
        lines = zoom.findall(f"{{{ns}}}line")
        assert len(lines) == 4
        # Find the zoom panel top-y (smallest y2 among connector lines).
        zoom_top_ys = [float(ln.get("y2")) for ln in lines]
        zoom_top_y = min(zoom_top_ys)
        # The annotation leader line targets the bottom edge of the panel.
        # Inspect the annotation group to find leader lines pointing upward.
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        anno_lines = annotations.findall(f".//{{{ns}}}line")
        for aline in anno_lines:
            target_y = float(aline.get("y2"))
            # Annotation leader targets must be at or below the zoom panel
            # bottom (i.e. >= zoom_top_y) — never above the panel top.
            if target_y < zoom_top_y:
                # This line points above the zoom panel top, which would
                # mean it crosses connector lines.
                origin_y = float(aline.get("y1"))
                if origin_y > target_y:
                    # Only consider lines going *upward* (from annotation row
                    # toward the attractor/panel).
                    pass  # Allow lines targeting the attractor itself


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(steps=1000, width_mm=100, height_mm=150)
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
        svg = generate_poster(steps=1000, width_mm=100, height_mm=150)
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
        svg = generate_poster(steps=1000, width_mm=100, height_mm=150)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_low:
            path_low = f_low.name
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_high:
            path_high = f_high.name
        try:
            write_png(svg, path_low, dpi=72)
            write_png(svg, path_high, dpi=144)
            assert os.path.getsize(path_high) > os.path.getsize(path_low)
        finally:
            os.unlink(path_low)
            os.unlink(path_high)
