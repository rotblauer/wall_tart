#!/usr/bin/env python3
"""Tests for poster_utils module."""

import xml.etree.ElementTree as ET

import pytest

from poster_utils import (
    ANNO_START_FRAC,
    AVAILABLE_THEMES,
    BASE_HEIGHT_MM,
    BASE_WIDTH_MM,
    CONTENT_TOP_MARGIN_FRAC,
    DEFAULT_THEME,
    THEMES,
    assign_annotations_no_crossing,
    build_poster_scaffold,
    content_area,
    draw_annotation_body,
    draw_annotation_header,
    draw_poster_border,
    draw_poster_header,
    finalize_poster,
    get_theme,
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


# ---------------------------------------------------------------------------
# build_poster_scaffold
# ---------------------------------------------------------------------------

class TestBuildPosterScaffold:
    def test_returns_dict_with_expected_keys(self):
        sc = build_poster_scaffold("Title", "Subtitle")
        for key in ("svg", "ns", "w_scale", "h_scale", "rule_y",
                     "width_mm", "height_mm", "designed_by", "designed_for"):
            assert key in sc, f"Missing key: {key}"

    def test_svg_root_element(self):
        sc = build_poster_scaffold("T", "S")
        assert sc["svg"].tag.endswith("svg")

    def test_default_dimensions(self):
        sc = build_poster_scaffold("T", "S")
        assert sc["svg"].get("width") == f"{BASE_WIDTH_MM}mm"
        assert sc["svg"].get("height") == f"{BASE_HEIGHT_MM}mm"
        assert sc["w_scale"] == 1.0
        assert sc["h_scale"] == 1.0

    def test_custom_dimensions(self):
        sc = build_poster_scaffold("T", "S", width_mm=300, height_mm=400)
        assert sc["svg"].get("width") == "300mm"
        assert sc["svg"].get("height") == "400mm"
        assert abs(sc["w_scale"] - 300 / BASE_WIDTH_MM) < 1e-9
        assert abs(sc["h_scale"] - 400 / BASE_HEIGHT_MM) < 1e-9

    def test_title_and_subtitle_in_svg(self):
        sc = build_poster_scaffold("My Title", "My Subtitle")
        xml_str = ET.tostring(sc["svg"], encoding="unicode")
        assert "My Title" in xml_str
        assert "My Subtitle" in xml_str

    def test_rule_y_is_numeric(self):
        sc = build_poster_scaffold("T", "S")
        assert isinstance(sc["rule_y"], float)
        assert sc["rule_y"] > 0

    def test_arrow_marker_present(self):
        sc = build_poster_scaffold("T", "S")
        ns = sc["ns"]
        defs = sc["svg"].find(f"{{{ns}}}defs")
        assert defs is not None
        marker = defs.find(f"{{{ns}}}marker[@id='arrowhead']")
        assert marker is not None

    def test_credit_lines_stored(self):
        sc = build_poster_scaffold("T", "S",
                                   designed_by="Alice",
                                   designed_for="Museum")
        assert sc["designed_by"] == "Alice"
        assert sc["designed_for"] == "Museum"


# ---------------------------------------------------------------------------
# content_area
# ---------------------------------------------------------------------------

class TestContentArea:
    def test_returns_dict_with_expected_keys(self):
        ca = content_area(rule_y=44.0, width_mm=420, height_mm=594)
        for key in ("min_top", "max_bot", "margin", "avail_w", "avail_h"):
            assert key in ca, f"Missing key: {key}"

    def test_default_margin(self):
        ca = content_area(rule_y=44.0, width_mm=420, height_mm=594)
        assert abs(ca["margin"] - 420 * 0.10) < 1e-9

    def test_custom_margin_frac(self):
        ca = content_area(rule_y=44.0, width_mm=420, height_mm=594,
                          margin_frac=0.12)
        assert abs(ca["margin"] - 420 * 0.12) < 1e-9

    def test_avail_w_consistent(self):
        ca = content_area(rule_y=44.0, width_mm=420, height_mm=594)
        assert abs(ca["avail_w"] - (420 - 2 * ca["margin"])) < 1e-9

    def test_min_top_uses_constant(self):
        rule_y = 44.0
        ca = content_area(rule_y=rule_y, width_mm=420, height_mm=594)
        expected = rule_y + 594 * CONTENT_TOP_MARGIN_FRAC
        assert abs(ca["min_top"] - expected) < 1e-9

    def test_max_bot_uses_constant(self):
        ca = content_area(rule_y=44.0, width_mm=420, height_mm=594)
        expected = 594 * ANNO_START_FRAC
        assert abs(ca["max_bot"] - expected) < 1e-9


# ---------------------------------------------------------------------------
# finalize_poster
# ---------------------------------------------------------------------------

class TestFinalizePoster:
    def test_adds_footer_and_border(self):
        svg, ns = _svg_root(420, 594)
        finalize_poster(svg, ns, 420, 594, 1.0, 1.0,
                        primary_line="Primary footer",
                        secondary_line="Secondary footer")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Primary footer" in xml_str
        assert "Secondary footer" in xml_str
        # Border rects should be present
        rects = svg.findall(f"{{{ns}}}rect")
        assert len(rects) >= 2


# ---------------------------------------------------------------------------
# draw_annotation_header
# ---------------------------------------------------------------------------

class TestDrawAnnotationHeader:
    def test_returns_group_element(self):
        svg, ns = _svg_root(420, 594)
        g = draw_annotation_header(svg, ns, 210, 400, 100, 200,
                                   "Test Title", scale=1)
        assert g.tag.endswith("g")

    def test_contains_title_text(self):
        svg, ns = _svg_root(420, 594)
        g = draw_annotation_header(svg, ns, 210, 400, 100, 200,
                                   "My Annotation", scale=1)
        xml_str = ET.tostring(g, encoding="unicode")
        assert "My Annotation" in xml_str

    def test_contains_circle_and_line(self):
        svg, ns = _svg_root(420, 594)
        g = draw_annotation_header(svg, ns, 210, 400, 100, 200,
                                   "Title", scale=1)
        assert g.find(f"{{{ns}}}circle") is not None
        assert g.find(f"{{{ns}}}line") is not None


# ---------------------------------------------------------------------------
# draw_annotation_body
# ---------------------------------------------------------------------------

class TestDrawAnnotationBody:
    def test_adds_text_element(self):
        svg, ns = _svg_root(420, 594)
        g = ET.SubElement(svg, f"{{{ns}}}g")
        draw_annotation_body(g, ns, 210, 400, ["Line 1", "Line 2"], scale=1)
        texts = g.findall(f"{{{ns}}}text")
        assert len(texts) >= 1
        xml_str = ET.tostring(g, encoding="unicode")
        assert "Line 1" in xml_str
        assert "Line 2" in xml_str


# ---------------------------------------------------------------------------
# Theme system
# ---------------------------------------------------------------------------

class TestThemeSystem:
    def test_available_themes_not_empty(self):
        assert len(AVAILABLE_THEMES) >= 3

    def test_classic_is_default(self):
        assert DEFAULT_THEME == "classic"

    def test_get_theme_returns_dict(self):
        t = get_theme("classic")
        assert isinstance(t, dict)
        for key in ("bg_color", "accent_color", "title_color",
                     "footer_primary", "footer_secondary",
                     "text_color", "border_color",
                     "content_primary", "content_secondary"):
            assert key in t

    def test_get_theme_none_returns_default(self):
        assert get_theme(None) == get_theme(DEFAULT_THEME)

    def test_get_theme_unknown_returns_default(self):
        assert get_theme("nonexistent") == get_theme(DEFAULT_THEME)

    def test_blueprint_theme_has_blue_bg(self):
        t = get_theme("blueprint")
        # Blueprint should have a dark blue background
        assert t["bg_color"].startswith("#0")

    def test_chalkboard_theme_has_dark_bg(self):
        t = get_theme("chalkboard")
        assert t["bg_color"].startswith("#2")

    def test_all_themes_have_same_keys(self):
        keys = set(THEMES["classic"].keys())
        for name, theme in THEMES.items():
            assert set(theme.keys()) == keys, f"Theme '{name}' has different keys"


# ---------------------------------------------------------------------------
# Font embedding
# ---------------------------------------------------------------------------

class TestFontEmbedding:
    def test_scaffold_embeds_font_style(self):
        sc = build_poster_scaffold("T", "S")
        ns = sc["ns"]
        style = sc["svg"].find(f"{{{ns}}}style")
        assert style is not None
        assert "Playfair" in style.text
        assert "Inter" in style.text

    def test_scaffold_with_theme_embeds_fonts(self):
        sc = build_poster_scaffold("T", "S", theme="blueprint")
        ns = sc["ns"]
        style = sc["svg"].find(f"{{{ns}}}style")
        assert style is not None


# ---------------------------------------------------------------------------
# Callout markers
# ---------------------------------------------------------------------------

class TestCalloutMarker:
    def test_marker_uses_circle_not_polygon(self):
        sc = build_poster_scaffold("T", "S")
        ns = sc["ns"]
        defs = sc["svg"].find(f"{{{ns}}}defs")
        marker = defs.find(f"{{{ns}}}marker[@id='arrowhead']")
        assert marker is not None
        # Should contain a circle, not a polygon
        assert marker.find(f"{{{ns}}}circle") is not None
        assert marker.find(f"{{{ns}}}polygon") is None

    def test_marker_uses_theme_accent_color(self):
        t_bp = get_theme("blueprint")
        sc = build_poster_scaffold("T", "S", theme="blueprint")
        ns = sc["ns"]
        defs = sc["svg"].find(f"{{{ns}}}defs")
        marker = defs.find(f"{{{ns}}}marker[@id='arrowhead']")
        circle = marker.find(f"{{{ns}}}circle")
        assert circle.get("fill") == t_bp["accent_color"]


# ---------------------------------------------------------------------------
# Theme integration in scaffold
# ---------------------------------------------------------------------------

class TestScaffoldTheme:
    def test_scaffold_returns_theme_key(self):
        sc = build_poster_scaffold("T", "S", theme="blueprint")
        assert sc["theme"] == "blueprint"

    def test_scaffold_default_theme(self):
        sc = build_poster_scaffold("T", "S")
        # Scaffold stores None; get_theme(None) resolves to DEFAULT_THEME
        assert sc["theme"] is None

    def test_scaffold_blueprint_uses_blue_bg(self):
        t = get_theme("blueprint")
        sc = build_poster_scaffold("T", "S", theme="blueprint")
        ns = sc["ns"]
        rects = sc["svg"].findall(f"{{{ns}}}rect")
        bg_rect = rects[0]
        assert bg_rect.get("fill") == t["bg_color"]

    def test_scaffold_chalkboard_uses_dark_bg(self):
        t = get_theme("chalkboard")
        sc = build_poster_scaffold("T", "S", theme="chalkboard")
        ns = sc["ns"]
        rects = sc["svg"].findall(f"{{{ns}}}rect")
        bg_rect = rects[0]
        assert bg_rect.get("fill") == t["bg_color"]

    def test_annotation_header_uses_theme_colors(self):
        t = get_theme("blueprint")
        svg, ns = _svg_root(420, 594)
        g = draw_annotation_header(svg, ns, 210, 400, 100, 200,
                                   "Test", scale=1, theme="blueprint")
        xml_str = ET.tostring(g, encoding="unicode")
        assert t["accent_color"] in xml_str
