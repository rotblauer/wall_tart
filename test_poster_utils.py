#!/usr/bin/env python3
"""Tests for poster_utils module."""

import xml.etree.ElementTree as ET

import pytest

from poster_utils import (
    assign_annotations_no_crossing,
    draw_poster_border,
    draw_poster_header,
    _svg_root,
)


# ---------------------------------------------------------------------------
# assign_annotations_no_crossing
# ---------------------------------------------------------------------------

class TestAssignAnnotationsNoCrossing:
    def test_sorted_by_target_x_ascending(self):
        annotations = [
            (lambda *a: None, 300, 100),
            (lambda *a: None, 100, 200),
            (lambda *a: None, 200, 150),
        ]
        result = assign_annotations_no_crossing(annotations)
        xs = [a[1] for a in result]
        assert xs == sorted(xs), f"Expected ascending x, got {xs}"

    def test_already_sorted_unchanged(self):
        f = lambda *a: None
        annotations = [(f, 10, 5), (f, 20, 10), (f, 30, 15)]
        result = assign_annotations_no_crossing(annotations)
        assert [a[1] for a in result] == [10, 20, 30]

    def test_reverse_order_sorted(self):
        f = lambda *a: None
        annotations = [(f, 90, 0), (f, 50, 0), (f, 10, 0)]
        result = assign_annotations_no_crossing(annotations)
        assert [a[1] for a in result] == [10, 50, 90]

    def test_preserves_associated_callables_and_y(self):
        def fn_a(): pass
        def fn_b(): pass
        def fn_c(): pass
        annotations = [(fn_c, 300, 30), (fn_a, 100, 10), (fn_b, 200, 20)]
        result = assign_annotations_no_crossing(annotations)
        assert result[0][0] is fn_a
        assert result[1][0] is fn_b
        assert result[2][0] is fn_c
        assert result[0][2] == 10
        assert result[1][2] == 20
        assert result[2][2] == 30

    def test_single_item(self):
        f = lambda *a: None
        annotations = [(f, 42, 7)]
        result = assign_annotations_no_crossing(annotations)
        assert len(result) == 1
        assert result[0][1] == 42

    def test_duplicate_x_values(self):
        f = lambda *a: None
        annotations = [(f, 50, 1), (f, 50, 2), (f, 50, 3)]
        result = assign_annotations_no_crossing(annotations)
        # Should not raise; order among ties is stable
        assert len(result) == 3


# ---------------------------------------------------------------------------
# draw_poster_header
# ---------------------------------------------------------------------------

class TestDrawPosterHeader:
    def _make_svg(self):
        svg, ns = _svg_root(420, 594)
        return svg, ns

    def test_returns_numeric_rule_y(self):
        svg, ns = self._make_svg()
        rule_y = draw_poster_header(
            svg, ns, 420, 594, 1.0, 1.0,
            title="Test Title",
            subtitle="Test Subtitle",
        )
        assert isinstance(rule_y, float)
        assert rule_y > 0

    def test_rule_y_is_correct_fraction(self):
        svg, ns = self._make_svg()
        height_mm = 594
        rule_y = draw_poster_header(
            svg, ns, 420, height_mm, 1.0, 1.0,
            title="T", subtitle="S",
        )
        assert abs(rule_y - height_mm * 0.074) < 1e-9

    def test_title_appears_in_svg(self):
        svg, ns = self._make_svg()
        draw_poster_header(svg, ns, 420, 594, 1.0, 1.0,
                           title="My Amazing Poster", subtitle="A subtitle")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "My Amazing Poster" in xml_str

    def test_subtitle_appears_in_svg(self):
        svg, ns = self._make_svg()
        draw_poster_header(svg, ns, 420, 594, 1.0, 1.0,
                           title="T", subtitle="Chaos and complexity")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Chaos and complexity" in xml_str

    def test_designed_by_appears_when_supplied(self):
        svg, ns = self._make_svg()
        draw_poster_header(svg, ns, 420, 594, 1.0, 1.0,
                           title="T", subtitle="S",
                           designed_by="Alice")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice" in xml_str

    def test_designed_for_appears_when_supplied(self):
        svg, ns = self._make_svg()
        draw_poster_header(svg, ns, 420, 594, 1.0, 1.0,
                           title="T", subtitle="S",
                           designed_for="the Science Museum")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed for the Science Museum" in xml_str

    def test_no_credits_by_default(self):
        svg, ns = self._make_svg()
        draw_poster_header(svg, ns, 420, 594, 1.0, 1.0,
                           title="T", subtitle="S")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by" not in xml_str
        assert "Designed for" not in xml_str

    def test_custom_dimensions_scale_rule_y(self):
        svg, ns = _svg_root(300, 400)
        rule_y = draw_poster_header(svg, ns, 300, 400,
                                    300 / 420, 400 / 594,
                                    title="T", subtitle="S")
        assert abs(rule_y - 400 * 0.074) < 1e-9


# ---------------------------------------------------------------------------
# draw_poster_border
# ---------------------------------------------------------------------------

class TestDrawPosterBorder:
    def test_no_exception_raised(self):
        svg, ns = _svg_root(420, 594)
        # Should not raise
        draw_poster_border(svg, ns, 420, 594, 1.0)

    def test_two_rects_added(self):
        svg, ns = _svg_root(420, 594)
        initial_count = len(list(svg))
        draw_poster_border(svg, ns, 420, 594, 1.0)
        rects = svg.findall(f"{{{ns}}}rect")
        assert len(rects) == 2

    def test_outer_border_dimensions(self):
        svg, ns = _svg_root(420, 594)
        draw_poster_border(svg, ns, 420, 594, 1.0)
        rects = svg.findall(f"{{{ns}}}rect")
        # First rect: 4mm inset → x=4, y=4, w=420-8, h=594-8
        outer = rects[0]
        assert outer.get("x") == "4"
        assert outer.get("y") == "4"
        assert outer.get("width") == str(420 - 8)
        assert outer.get("height") == str(594 - 8)

    def test_inner_border_dimensions(self):
        svg, ns = _svg_root(420, 594)
        draw_poster_border(svg, ns, 420, 594, 1.0)
        rects = svg.findall(f"{{{ns}}}rect")
        # Second rect: 7mm inset → x=7, y=7, w=420-14, h=594-14
        inner = rects[1]
        assert inner.get("x") == "7"
        assert inner.get("y") == "7"
        assert inner.get("width") == str(420 - 14)
        assert inner.get("height") == str(594 - 14)
