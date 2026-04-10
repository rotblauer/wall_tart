#!/usr/bin/env python3
"""Tests for double_pendulum_poster module."""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from double_pendulum_poster import (
    compute_lyapunov_separation,
    compute_phase_space_portrait,
    compute_poincare_section_dp,
    double_pendulum_derivatives,
    generate_poster,
    integrate_double_pendulum,
    pendulum_tip_positions,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# Double pendulum derivatives
# ---------------------------------------------------------------------------

class TestDoublePendulumDerivatives:
    def test_returns_four_values(self):
        state = (math.pi / 4, 0.0, math.pi / 4, 0.0)
        result = double_pendulum_derivatives(state)
        assert len(result) == 4

    def test_all_zero_velocities_at_rest(self):
        """At theta1=theta2=0 (hanging down), angular velocities should be zero."""
        state = (0.0, 0.0, 0.0, 0.0)
        dtheta1, domega1, dtheta2, domega2 = double_pendulum_derivatives(state)
        assert dtheta1 == 0.0
        assert dtheta2 == 0.0
        # At equilibrium, the angular accelerations should be near zero
        assert abs(domega1) < 1e-10
        assert abs(domega2) < 1e-10

    def test_returns_float_values(self):
        state = (1.0, 0.5, -0.5, 0.1)
        result = double_pendulum_derivatives(state)
        assert all(isinstance(v, float) for v in result)

    def test_dtheta_equals_omega(self):
        """dtheta1/dt should be omega1, dtheta2/dt should be omega2."""
        omega1, omega2 = 1.5, -0.3
        state = (0.5, omega1, -0.2, omega2)
        result = double_pendulum_derivatives(state)
        assert result[0] == omega1
        assert result[2] == omega2


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegrateDoublePendulum:
    def test_trajectory_length(self):
        traj = integrate_double_pendulum((1.0, 0.0, 1.0, 0.0), steps=100)
        assert len(traj) == 101  # initial + 100 steps

    def test_first_state_is_initial(self):
        initial = (math.pi / 4, 0.0, math.pi / 6, 0.0)
        traj = integrate_double_pendulum(initial, steps=10)
        assert traj[0] == initial

    def test_each_state_has_four_components(self):
        traj = integrate_double_pendulum((1.0, 0.0, 1.0, 0.0), steps=50)
        for state in traj:
            assert len(state) == 4

    def test_values_are_finite(self):
        traj = integrate_double_pendulum((1.0, 0.0, 0.5, 0.0), steps=500, dt=0.001)
        for state in traj:
            assert all(math.isfinite(v) for v in state), f"Non-finite state: {state}"

    def test_short_integration_stays_close(self):
        """For a very short integration, state should not change much."""
        initial = (0.1, 0.0, 0.1, 0.0)
        traj = integrate_double_pendulum(initial, steps=10, dt=0.0001)
        for comp_idx in range(4):
            assert abs(traj[-1][comp_idx] - initial[comp_idx]) < 0.1


# ---------------------------------------------------------------------------
# Tip positions
# ---------------------------------------------------------------------------

class TestPendulumTipPositions:
    def test_returns_xy_pairs(self):
        traj = [(0.0, 0.0, 0.0, 0.0)] * 5
        tips = pendulum_tip_positions(traj)
        assert len(tips) == 5
        for pt in tips:
            assert len(pt) == 2

    def test_hanging_straight_down(self):
        """When both angles are 0, the tip should be at (0, -(L1+L2))."""
        traj = [(0.0, 0.0, 0.0, 0.0)]
        tips = pendulum_tip_positions(traj, L1=1.0, L2=1.0)
        x, y = tips[0]
        assert abs(x) < 1e-10
        assert abs(y - (-2.0)) < 1e-10

    def test_horizontal_position(self):
        """theta1 = pi/2, theta2 = pi/2: both arms pointing right."""
        traj = [(math.pi / 2, 0.0, math.pi / 2, 0.0)]
        tips = pendulum_tip_positions(traj, L1=1.0, L2=1.0)
        x, y = tips[0]
        assert abs(x - 2.0) < 1e-10
        assert abs(y) < 1e-10


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(steps=100, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_trajectories_group(self):
        svg = generate_poster(steps=100, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        traj = svg.find(f".//{{{ns}}}g[@id='trajectories']")
        assert traj is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(steps=100, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert annotations is not None

    def test_contains_educational_group(self):
        svg = generate_poster(steps=100, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        edu = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert edu is not None

    def test_trajectories_has_polylines(self):
        svg = generate_poster(steps=200, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        traj = svg.find(f".//{{{ns}}}g[@id='trajectories']")
        polylines = traj.findall(f".//{{{ns}}}polyline")
        # Should have 3 trajectories
        assert len(polylines) >= 3

    def test_default_dimensions(self):
        svg = generate_poster(steps=100)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(steps=100, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(steps=100, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Sensitive" in xml_str or "sensitive" in xml_str or "Dependence" in xml_str
        assert "Phase" in xml_str or "phase" in xml_str
        assert "Energy" in xml_str or "energy" in xml_str

    def test_educational_text_present(self):
        svg = generate_poster(steps=100, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Chaos" in xml_str or "chaos" in xml_str

    def test_credit_designed_by(self):
        svg = generate_poster(steps=100, width_mm=200, height_mm=300,
                              designed_by="Alice")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice" in xml_str

    def test_credit_designed_for(self):
        svg = generate_poster(steps=100, width_mm=200, height_mm=300,
                              designed_for="the Science Museum")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed for the Science Museum" in xml_str

    def test_credit_both(self):
        svg = generate_poster(steps=100, width_mm=200, height_mm=300,
                              designed_by="Alice and Bob",
                              designed_for="ACME Labs")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice and Bob for ACME Labs" in xml_str

    def test_no_credit_by_default(self):
        svg = generate_poster(steps=100, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by" not in xml_str

    def test_title_present(self):
        svg = generate_poster(steps=100, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Double Pendulum" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(steps=100, width_mm=100, height_mm=150)
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
        svg = generate_poster(steps=100, width_mm=100, height_mm=150)
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


# ---------------------------------------------------------------------------
# Lyapunov separation
# ---------------------------------------------------------------------------

class TestComputeLyapunovSeparation:
    def test_same_trajectory_gives_zero(self):
        traj = integrate_double_pendulum((1.0, 0.0, 1.0, 0.0), steps=50)
        sep = compute_lyapunov_separation(traj, traj)
        assert all(s == 0.0 for s in sep)

    def test_length_equals_shorter_trajectory(self):
        traj_a = integrate_double_pendulum((1.0, 0.0, 1.0, 0.0), steps=100)
        traj_b = integrate_double_pendulum((1.0 + 1e-5, 0.0, 1.0, 0.0), steps=100)
        sep = compute_lyapunov_separation(traj_a, traj_b)
        assert len(sep) == 101

    def test_initial_separation_matches_state_difference(self):
        delta = 1e-5
        traj_a = integrate_double_pendulum((1.0, 0.0, 1.0, 0.0), steps=10)
        traj_b = integrate_double_pendulum((1.0 + delta, 0.0, 1.0, 0.0), steps=10)
        sep = compute_lyapunov_separation(traj_a, traj_b)
        assert abs(sep[0] - delta) < 1e-12

    def test_all_values_non_negative(self):
        traj_a = integrate_double_pendulum((1.0, 0.0, 0.5, 0.0), steps=100)
        traj_b = integrate_double_pendulum((1.0 + 1e-5, 0.0, 0.5, 0.0), steps=100)
        sep = compute_lyapunov_separation(traj_a, traj_b)
        assert all(s >= 0.0 for s in sep)

    def test_separation_grows_over_time(self):
        """Chaotic trajectories starting nearby should diverge over many steps."""
        traj_a = integrate_double_pendulum((math.pi / 2, 0.0, math.pi / 2, 0.0),
                                           steps=2000, dt=0.005)
        traj_b = integrate_double_pendulum((math.pi / 2 + 1e-5, 0.0, math.pi / 2, 0.0),
                                           steps=2000, dt=0.005)
        sep = compute_lyapunov_separation(traj_a, traj_b)
        assert sep[-1] > sep[0]


# ---------------------------------------------------------------------------
# Phase-space portrait
# ---------------------------------------------------------------------------

class TestComputePhaseSpacePortrait:
    def test_returns_pairs(self):
        traj = integrate_double_pendulum((1.0, 0.0, 1.0, 0.0), steps=50)
        pts = compute_phase_space_portrait(traj)
        assert len(pts) == len(traj)
        for pt in pts:
            assert len(pt) == 2

    def test_first_point_matches_initial_state(self):
        initial = (math.pi / 4, 0.5, math.pi / 6, -0.3)
        traj = integrate_double_pendulum(initial, steps=10)
        pts = compute_phase_space_portrait(traj)
        assert pts[0][0] == initial[0]   # theta1
        assert pts[0][1] == initial[1]   # omega1

    def test_values_are_floats(self):
        traj = integrate_double_pendulum((1.0, 0.0, 1.0, 0.0), steps=20)
        pts = compute_phase_space_portrait(traj)
        for theta, omega in pts:
            assert isinstance(theta, float)
            assert isinstance(omega, float)


# ---------------------------------------------------------------------------
# Poincaré section
# ---------------------------------------------------------------------------

class TestComputePoincareSectionDp:
    def test_returns_pairs(self):
        traj = integrate_double_pendulum((math.pi / 2, 0.0, math.pi / 2, 0.0),
                                         steps=1000, dt=0.005)
        pts = compute_poincare_section_dp(traj)
        for pt in pts:
            assert len(pt) == 2

    def test_no_crossings_for_trivial_trajectory(self):
        """A trajectory that stays at omega1=0 has no downward crossings."""
        # Use a very short integration near equilibrium — omega1 never crosses 0
        traj = [(0.0, 0.0, 0.0, 0.0)] * 10
        pts = compute_poincare_section_dp(traj)
        assert pts == []

    def test_detects_downward_crossing(self):
        """Explicit omega1 sign change from positive to non-positive is caught."""
        traj = [
            (1.0, 0.5, 1.0, 0.0),   # omega1 > 0
            (1.0, 0.0, 1.0, 0.0),   # omega1 crosses to 0 → crossing recorded
            (1.0, -0.5, 1.0, 0.0),  # omega1 < 0  → NOT a downward crossing start
            (1.0, 0.3, 1.0, 0.0),   # omega1 > 0 again
            (1.0, -0.1, 1.0, 0.0),  # omega1 → negative → second crossing
        ]
        pts = compute_poincare_section_dp(traj)
        # Crossings at indices 1 and 4
        assert len(pts) == 2
        assert pts[0] == (1.0, 1.0)   # (theta1, theta2) at index 1
        assert pts[1] == (1.0, 1.0)   # (theta1, theta2) at index 4

    def test_upward_crossings_ignored(self):
        """Only downward (positive→non-positive) zero crossings are included."""
        traj = [
            (0.5, -0.5, 0.5, 0.0),  # omega1 < 0
            (0.5, 0.5, 0.5, 0.0),   # upward crossing — should NOT appear
        ]
        pts = compute_poincare_section_dp(traj)
        assert pts == []


# ---------------------------------------------------------------------------
# Inset groups in generated SVG
# ---------------------------------------------------------------------------

class TestInsetGroupsInPoster:
    def test_phase_space_inset_group_present(self):
        svg = generate_poster(steps=200, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='phase_space_inset']")
        assert grp is not None

    def test_poincare_dp_inset_group_present(self):
        svg = generate_poster(steps=200, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='poincare_dp_inset']")
        assert grp is not None

    def test_phase_space_clip_path_present(self):
        svg = generate_poster(steps=200, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='phase_space_clip']")
        assert clip is not None

    def test_poincare_dp_clip_path_present(self):
        svg = generate_poster(steps=200, width_mm=200, height_mm=300)
        ns = "http://www.w3.org/2000/svg"
        clip = svg.find(f".//{{{ns}}}clipPath[@id='poincare_dp_clip']")
        assert clip is not None

    def test_lyapunov_label_text_present(self):
        svg = generate_poster(steps=200, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "exponential divergence" in xml_str

    def test_phase_portrait_label_present(self):
        svg = generate_poster(steps=200, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Phase portrait" in xml_str

    def test_poincare_label_present(self):
        svg = generate_poster(steps=200, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Poincar" in xml_str
