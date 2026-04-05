#!/usr/bin/env python3
"""Tests for fourier_epicycles_poster module."""

import os
import math
import tempfile
import xml.etree.ElementTree as ET

import pytest

from fourier_epicycles_poster import (
    sample_target_curve,
    dft,
    reconstruct_curve,
    epicycle_arms,
    generate_poster,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# sample_target_curve
# ---------------------------------------------------------------------------

class TestSampleTargetCurve:
    def test_returns_correct_length(self):
        x, y = sample_target_curve(64)
        assert len(x) == 64 and len(y) == 64

    def test_values_are_float(self):
        x, y = sample_target_curve(16)
        for v in x + y:
            assert isinstance(v, float)


# ---------------------------------------------------------------------------
# dft
# ---------------------------------------------------------------------------

class TestDft:
    def test_returns_correct_length(self):
        x, y = sample_target_curve(32)
        result = dft(x, y)
        assert len(result) == 32

    def test_result_is_freq_amp_phase(self):
        x, y = sample_target_curve(16)
        result = dft(x, y)
        for freq, amp, phase in result:
            assert isinstance(freq, int)
            assert isinstance(amp, float)
            assert isinstance(phase, float)
            assert amp >= 0

    def test_amplitudes_are_nonnegative(self):
        x, y = sample_target_curve(32)
        result = dft(x, y)
        for _, amp, _ in result:
            assert amp >= 0


# ---------------------------------------------------------------------------
# reconstruct_curve
# ---------------------------------------------------------------------------

class TestReconstructCurve:
    def test_returns_correct_length(self):
        x, y = sample_target_curve(32)
        coeffs = dft(x, y)
        pts = reconstruct_curve(coeffs, 64)
        assert len(pts) == 64

    def test_reconstruction_close_to_original(self):
        """Full DFT reconstruction should closely match the original."""
        x, y = sample_target_curve(32)
        coeffs = dft(x, y)
        pts = reconstruct_curve(coeffs, 32)
        for i in range(32):
            assert abs(pts[i][0] - x[i]) < 0.01
            assert abs(pts[i][1] - y[i]) < 0.01


# ---------------------------------------------------------------------------
# epicycle_arms
# ---------------------------------------------------------------------------

class TestEpicycleArms:
    def test_starts_at_origin(self):
        x, y = sample_target_curve(16)
        coeffs = dft(x, y)
        sorted_c = sorted(coeffs, key=lambda c: c[1], reverse=True)[:5]
        arms = epicycle_arms(sorted_c, 0.0)
        assert arms[0] == (0.0, 0.0)

    def test_length(self):
        x, y = sample_target_curve(16)
        coeffs = dft(x, y)
        sorted_c = sorted(coeffs, key=lambda c: c[1], reverse=True)[:5]
        arms = epicycle_arms(sorted_c, 0.0)
        assert len(arms) == 6  # origin + 5 arm positions


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(num_circles=5, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_epicycles_group(self):
        svg = generate_poster(num_circles=5, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='epicycles']")
        assert grp is not None

    def test_contains_annotations_group(self):
        svg = generate_poster(num_circles=5, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert grp is not None

    def test_contains_educational_group(self):
        svg = generate_poster(num_circles=5, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        grp = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert grp is not None

    def test_default_dimensions(self):
        svg = generate_poster(num_circles=5)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(num_circles=5, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(num_circles=5, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Fourier" in xml_str

    def test_title_present(self):
        svg = generate_poster(num_circles=5, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Fourier Epicycles" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(num_circles=5, width_mm=100, height_mm=150)
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
        svg = generate_poster(num_circles=5, width_mm=100, height_mm=150)
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
