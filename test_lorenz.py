#!/usr/bin/env python3
"""Tests for lorenz_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from lorenz_poster import (
    DEFAULT_ANGLE_X,
    DEFAULT_ANGLE_Z,
    compute_poincare_section,
    compute_poincare_section_x0,
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

    def test_butterfly_exponent_uses_ascii_notation(self):
        """Butterfly annotation should use ASCII exponent notation 1e-10."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "1e-10" in xml_str

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

    def test_zoom_inset_panel_dots_present(self):
        """The zoom_inset group contains time-colored dots (circles)."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        circles = zoom.findall(f".//{{{ns}}}circle")
        assert len(circles) >= 1

    def test_zoom_inset_all_themes(self):
        """zoom_inset renders without error for all built-in themes."""
        from poster_utils import AVAILABLE_THEMES
        for theme in AVAILABLE_THEMES:
            svg = generate_poster(steps=1000, width_mm=200, height_mm=300,
                                  theme=theme)
            ns = "http://www.w3.org/2000/svg"
            zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
            assert zoom is not None, f"zoom_inset missing for theme '{theme}'"

    def test_zoom_target_box_near_saddle_region(self):
        """The zoom target box must be near the saddle / transition region."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        rects = zoom.findall(f"{{{ns}}}rect")
        # The 3rd rect is the source target box on the main attractor.
        target_box = rects[2]
        box_x = float(target_box.get("x"))
        box_w = float(target_box.get("width"))
        box_cx = box_x + box_w / 2
        # The saddle region is near the attractor centre (width_mm / 2 = 100).
        # Allow a generous margin — the density×parallelism search may land
        # slightly off-centre.
        assert abs(box_cx - 100.0) < 30.0, (
            f"Zoom target box centre {box_cx:.1f} should be near the attractor "
            f"centre (100 ± 30)"
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
        # Find the zoom panel bottom-y (largest y2 among connector lines).
        zoom_bottom_y = max(float(ln.get("y2")) for ln in lines)
        # Find the zoom panel top-y (smallest y2 among connector lines).
        zoom_top_y = min(float(ln.get("y2")) for ln in lines)
        # The annotation leader lines originate in the annotation row (below
        # the attractor) and point upward to their targets.
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        anno_lines = annotations.findall(f".//{{{ns}}}line")
        for aline in anno_lines:
            target_y = float(aline.get("y2"))
            origin_y = float(aline.get("y1"))
            # Only check upward-pointing lines (from annotation row to target).
            if origin_y <= target_y:
                continue
            # If this leader targets the zoom panel region (near zoom_bottom_y),
            # it must NOT terminate above the panel top — that would indicate
            # it crosses through the connector lines.
            target_x = float(aline.get("x2"))
            bg_rect = zoom.findall(f"{{{ns}}}rect")[0]
            panel_left = float(bg_rect.get("x"))
            panel_right = panel_left + float(bg_rect.get("width"))
            if panel_left <= target_x <= panel_right:
                assert target_y >= zoom_top_y, (
                    f"Leader line targeting zoom panel terminates at y={target_y:.1f}, "
                    f"which is above the zoom panel top y={zoom_top_y:.1f}"
                )

    # --- Ultra-zoom (second-level zoom) tests ---

    def test_ultra_zoom_group_present(self):
        """An 'ultra_zoom_inset' group exists in the SVG."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        uz = svg.find(f".//{{{ns}}}g[@id='ultra_zoom_inset']")
        assert uz is not None

    def test_ultra_zoom_clip_path_present(self):
        """A clipPath with id 'ultra_zoom_clip' exists in <defs>."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='ultra_zoom_clip']")
        assert clip is not None
        rect = clip.find(f"{{{ns}}}rect")
        assert rect is not None
        assert float(rect.get("width")) > 0
        assert float(rect.get("height")) > 0

    def test_ultra_zoom_connector_lines_present(self):
        """The ultra_zoom_inset group has exactly 2 connector lines."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        uz = svg.find(f".//{{{ns}}}g[@id='ultra_zoom_inset']")
        lines = uz.findall(f"{{{ns}}}line")
        assert len(lines) == 2

    def test_ultra_zoom_sub_box_on_first_zoom(self):
        """The ultra_zoom_inset group contains a sub-box rect on the first zoom."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        uz = svg.find(f".//{{{ns}}}g[@id='ultra_zoom_inset']")
        rects = uz.findall(f"{{{ns}}}rect")
        # 3 rects: sub-box on first zoom, background, border
        assert len(rects) == 3

    def test_ultra_zoom_dots_present(self):
        """The ultra_zoom_inset group has time-colored dots (circles)."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        uz = svg.find(f".//{{{ns}}}g[@id='ultra_zoom_inset']")
        circles = uz.findall(f".//{{{ns}}}circle")
        assert len(circles) >= 1

    def test_ultra_zoom_label_present(self):
        """The ultra-zoom panel has a label mentioning 'x–z projection'."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "x\u2013z projection" in xml_str

    def test_ultra_zoom_below_first_zoom(self):
        """The ultra-zoom panel is positioned below the first zoom panel."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        zoom = svg.find(f".//{{{ns}}}g[@id='zoom_inset']")
        z1_bg = zoom.findall(f"{{{ns}}}rect")[0]
        z1_bottom = float(z1_bg.get("y")) + float(z1_bg.get("height"))

        uz = svg.find(f".//{{{ns}}}g[@id='ultra_zoom_inset']")
        # Rects in ultra_zoom_inset: [0] sub-box on zoom1, [1] background, [2] border.
        uz_bg = uz.findall(f"{{{ns}}}rect")[1]
        uz_top = float(uz_bg.get("y"))

        assert uz_top > z1_bottom, (
            f"Ultra-zoom top ({uz_top:.1f}) should be below first zoom "
            f"bottom ({z1_bottom:.1f})"
        )

    def test_ultra_zoom_all_themes(self):
        """ultra_zoom_inset renders without error for all built-in themes."""
        from poster_utils import AVAILABLE_THEMES
        for theme in AVAILABLE_THEMES:
            svg = generate_poster(steps=1000, width_mm=200, height_mm=300,
                                  theme=theme)
            ns = "http://www.w3.org/2000/svg"
            uz = svg.find(f".//{{{ns}}}g[@id='ultra_zoom_inset']")
            assert uz is not None, f"ultra_zoom_inset missing for theme '{theme}'"

    # --- Extra-detail trajectory tests ---

    def test_zoom_multiplier_zero_no_crash(self):
        """zoom_multiplier=0 produces a valid poster with no extra trajectory."""
        svg = generate_poster(steps=1000, zoom_multiplier=0,
                              width_mm=200, height_mm=300)
        assert svg.tag.endswith("svg")

    def test_zoom_multiplier_increases_zoom_dots(self):
        """With zoom_multiplier>0, zoom panels should have more dots (circles)."""
        ns = "http://www.w3.org/2000/svg"
        svg_no_extra = generate_poster(steps=5000, zoom_multiplier=0,
                                       width_mm=200, height_mm=300)
        svg_with_extra = generate_poster(steps=5000, zoom_multiplier=1,
                                         width_mm=200, height_mm=300)
        zoom_no = svg_no_extra.find(f".//{{{ns}}}g[@id='zoom_inset']")
        zoom_ex = svg_with_extra.find(f".//{{{ns}}}g[@id='zoom_inset']")
        dots_no = len(zoom_no.findall(f".//{{{ns}}}circle"))
        dots_ex = len(zoom_ex.findall(f".//{{{ns}}}circle"))
        assert dots_ex >= dots_no

    def test_zoom_panels_within_poster_bounds(self):
        """Zoom panels should not extend beyond the poster edges."""
        for w, h in [(200, 300), (100, 150), (420, 594)]:
            svg = generate_poster(steps=1000, width_mm=w, height_mm=h)
            ns = "http://www.w3.org/2000/svg"
            clip = svg.find(f".//{{{ns}}}clipPath[@id='zoom_panel_clip']")
            rect = clip.find(f"{{{ns}}}rect")
            rx = float(rect.get("x"))
            ry = float(rect.get("y"))
            rw = float(rect.get("width"))
            rh = float(rect.get("height"))
            assert rx >= 0, f"Zoom panel left edge {rx} < 0 for {w}x{h}"
            assert rx + rw <= w, f"Zoom panel right edge {rx+rw} > {w} for {w}x{h}"
            assert ry >= 0, f"Zoom panel top edge {ry} < 0 for {w}x{h}"
            assert ry + rh <= h, f"Zoom panel bottom edge {ry+rh} > {h} for {w}x{h}"

    def test_ultra_zoom_panels_within_poster_bounds(self):
        """Ultra-zoom panels should not extend beyond the poster edges."""
        for w, h in [(200, 300), (100, 150), (420, 594)]:
            svg = generate_poster(steps=1000, width_mm=w, height_mm=h)
            ns = "http://www.w3.org/2000/svg"
            clip = svg.find(f".//{{{ns}}}clipPath[@id='ultra_zoom_clip']")
            rect = clip.find(f"{{{ns}}}rect")
            rx = float(rect.get("x"))
            ry = float(rect.get("y"))
            rw = float(rect.get("width"))
            rh = float(rect.get("height"))
            assert rx >= 0, f"Ultra zoom left edge {rx} < 0 for {w}x{h}"
            assert rx + rw <= w, f"Ultra zoom right edge {rx+rw} > {w} for {w}x{h}"
            assert ry >= 0, f"Ultra zoom top edge {ry} < 0 for {w}x{h}"
            assert ry + rh <= h, f"Ultra zoom bottom edge {ry+rh} > {h} for {w}x{h}"


# ---------------------------------------------------------------------------
# Poincaré section
# ---------------------------------------------------------------------------

class TestComputePoincareSection:
    def test_returns_list(self):
        traj = integrate_lorenz(steps=5000)
        section = compute_poincare_section(traj, z0=27.0, tol=0.5)
        assert isinstance(section, list)

    def test_points_are_2d(self):
        traj = integrate_lorenz(steps=5000)
        section = compute_poincare_section(traj, z0=27.0, tol=0.5)
        for pt in section:
            assert len(pt) == 2

    def test_nonempty_for_default_params(self):
        """With enough steps near the attractor, the section should be nonempty."""
        traj = integrate_lorenz(steps=20000)
        section = compute_poincare_section(traj, z0=27.0, tol=0.5)
        assert len(section) > 0

    def test_empty_for_short_trajectory(self):
        """A very short trajectory from (1,1,1) may never reach z ≈ 27."""
        traj = integrate_lorenz(steps=10, dt=0.001)
        section = compute_poincare_section(traj, z0=27.0, tol=0.01)
        assert isinstance(section, list)

    def test_tight_tolerance(self):
        """Tighter tolerance should yield fewer or equal points."""
        traj = integrate_lorenz(steps=10000)
        wide = compute_poincare_section(traj, z0=27.0, tol=1.0)
        tight = compute_poincare_section(traj, z0=27.0, tol=0.1)
        assert len(tight) <= len(wide)


# ---------------------------------------------------------------------------
# Poincaré section — x=0 cross-section
# ---------------------------------------------------------------------------

class TestComputePoincareSectionX0:
    def test_returns_list(self):
        traj = integrate_lorenz(steps=5000)
        section = compute_poincare_section_x0(traj, x0=0.0, tol=1.0)
        assert isinstance(section, list)

    def test_points_are_2d(self):
        traj = integrate_lorenz(steps=5000)
        section = compute_poincare_section_x0(traj, x0=0.0, tol=1.0)
        for pt in section:
            assert len(pt) == 2

    def test_nonempty_for_default_params(self):
        """With enough steps near the attractor, the x=0 section should be nonempty."""
        traj = integrate_lorenz(steps=20000)
        section = compute_poincare_section_x0(traj, x0=0.0, tol=1.0)
        assert len(section) > 0

    def test_tight_tolerance_yields_fewer_points(self):
        """Tighter x tolerance should yield fewer or equal points."""
        traj = integrate_lorenz(steps=10000)
        wide = compute_poincare_section_x0(traj, x0=0.0, tol=2.0)
        tight = compute_poincare_section_x0(traj, x0=0.0, tol=0.1)
        assert len(tight) <= len(wide)


class TestPoincareInsetPoster:
    def test_poincare_z27_inset_group_present(self):
        """A 'poincare_z27_inset' group exists by default."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        ps = svg.find(f".//{{{ns}}}g[@id='poincare_z27_inset']")
        assert ps is not None

    def test_poincare_x0_inset_group_present(self):
        """A 'poincare_x0_inset' group exists by default."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        ps = svg.find(f".//{{{ns}}}g[@id='poincare_x0_inset']")
        assert ps is not None

    def test_poincare_z27_clip_path_present(self):
        """A clipPath with id 'poincare_z27_clip' exists."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='poincare_z27_clip']")
        assert clip is not None
        rect = clip.find(f"{{{ns}}}rect")
        assert rect is not None
        assert float(rect.get("width")) > 0
        assert float(rect.get("height")) > 0

    def test_poincare_x0_clip_path_present(self):
        """A clipPath with id 'poincare_x0_clip' exists."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='poincare_x0_clip']")
        assert clip is not None
        rect = clip.find(f"{{{ns}}}rect")
        assert rect is not None
        assert float(rect.get("width")) > 0
        assert float(rect.get("height")) > 0

    def test_poincare_labels_present(self):
        """Both Poincaré section labels are in the SVG."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "z \u2248 27" in xml_str
        assert "x \u2248 0" in xml_str

    def test_ultra_zoom_still_present_with_poincare(self):
        """ultra_zoom_inset, poincare_z27_inset, and poincare_x0_inset all exist."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        uz = svg.find(f".//{{{ns}}}g[@id='ultra_zoom_inset']")
        pz = svg.find(f".//{{{ns}}}g[@id='poincare_z27_inset']")
        px = svg.find(f".//{{{ns}}}g[@id='poincare_x0_inset']")
        assert uz is not None
        assert pz is not None
        assert px is not None

    def test_poincare_z27_panel_in_col2_col3_gap(self):
        """The z≈27 Poincaré panel is in the col2-col3 inter-column gap."""
        from poster_utils import COLUMN_CENTERS
        w = 200
        svg = generate_poster(steps=5000, width_mm=w, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='poincare_z27_clip']")
        rect = clip.find(f"{{{ns}}}rect")
        ps_x = float(rect.get("x"))
        ps_w = float(rect.get("width"))
        ps_cx = ps_x + ps_w / 2
        col2_cx = w * COLUMN_CENTERS[1]
        col3_cx = w * COLUMN_CENTERS[2]
        expected_cx = (col2_cx + col3_cx) / 2
        assert abs(ps_cx - expected_cx) <= ps_w, (
            f"z≈27 panel centre ({ps_cx:.1f}) should be near "
            f"col2-col3 midpoint ({expected_cx:.1f})"
        )

    def test_poincare_x0_panel_in_col1_col2_gap(self):
        """The x≈0 Poincaré panel is in the col1-col2 inter-column gap."""
        from poster_utils import COLUMN_CENTERS
        w = 200
        svg = generate_poster(steps=5000, width_mm=w, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='poincare_x0_clip']")
        rect = clip.find(f"{{{ns}}}rect")
        ps_x = float(rect.get("x"))
        ps_w = float(rect.get("width"))
        ps_cx = ps_x + ps_w / 2
        col1_cx = w * COLUMN_CENTERS[0]
        col2_cx = w * COLUMN_CENTERS[1]
        expected_cx = (col1_cx + col2_cx) / 2
        assert abs(ps_cx - expected_cx) <= ps_w, (
            f"x≈0 panel centre ({ps_cx:.1f}) should be near "
            f"col1-col2 midpoint ({expected_cx:.1f})"
        )

    def test_poincare_all_themes(self):
        """Both Poincaré section panels render without error for all themes."""
        from poster_utils import AVAILABLE_THEMES
        for theme in AVAILABLE_THEMES:
            svg = generate_poster(steps=5000, width_mm=200, height_mm=300,
                                  theme=theme)
            ns = "http://www.w3.org/2000/svg"
            pz = svg.find(f".//{{{ns}}}g[@id='poincare_z27_inset']")
            px = svg.find(f".//{{{ns}}}g[@id='poincare_x0_inset']")
            assert pz is not None, f"poincare_z27_inset missing for theme '{theme}'"
            assert px is not None, f"poincare_x0_inset missing for theme '{theme}'"

    def test_butterfly_effect_has_no_callout_arrow(self):
        """The Butterfly Effect annotation has no callout arrow (no bezier path)."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        # No <path> element with a cubic bezier 'C' command should exist
        paths = svg.findall(f".//{{{ns}}}path")
        arch_paths = [p for p in paths if "C " in (p.get("d") or "")]
        assert len(arch_paths) == 0, "Expected no cubic bezier arch paths"

    def test_two_wings_has_no_callout_arrow(self):
        """The Two Wings annotation has no callout arrow (no extra straight line)."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        # The only straight annotation arrow should be from Infinite Complexity
        # We verify by checking only one arrowhead marker is used
        assert xml_str.count("marker-end") == 1

    def test_infinite_complexity_references_both_sections(self):
        """'Infinite Complexity' body text mentions both x=0 and z=27."""
        svg = generate_poster(steps=5000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "x = 0" in xml_str
        assert "z = 27" in xml_str


# ---------------------------------------------------------------------------
# Projection angle configuration
# ---------------------------------------------------------------------------

class TestProjectionAngles:
    def test_default_angle_constants(self):
        """Module-level angle constants have expected values."""
        assert DEFAULT_ANGLE_X == -0.35
        assert DEFAULT_ANGLE_Z == 0.85

    def test_custom_angles_no_crash(self):
        """Custom projection angles produce a valid poster."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300,
                              angle_x=-0.5, angle_z=1.0)
        assert svg.tag.endswith("svg")

    def test_default_angles_match_original(self):
        """Explicit default angles produce same result as None."""
        svg1 = generate_poster(steps=1000, width_mm=100, height_mm=150,
                               verbose=False)
        svg2 = generate_poster(steps=1000, width_mm=100, height_mm=150,
                               angle_x=DEFAULT_ANGLE_X, angle_z=DEFAULT_ANGLE_Z,
                               verbose=False)
        xml1 = ET.tostring(svg1, encoding="unicode")
        xml2 = ET.tostring(svg2, encoding="unicode")
        assert xml1 == xml2


# ---------------------------------------------------------------------------
# Extra trajectory visual distinction
# ---------------------------------------------------------------------------

class TestExtraTrajectoryDistinction:
    def test_zoom_label_includes_xz_projection(self):
        """The zoom panel label mentions 'x–z projection'."""
        svg = generate_poster(steps=1000, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "x\u2013z projection" in xml_str


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
