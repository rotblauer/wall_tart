#!/usr/bin/env python3
"""Tests for cellular_automata_poster module."""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from cellular_automata_poster import (
    apply_rule,
    generate_automaton,
    generate_poster,
)
from poster_utils import write_png, write_svg


# ---------------------------------------------------------------------------
# apply_rule
# ---------------------------------------------------------------------------

class TestApplyRule:
    def test_rule_30_known_outputs(self):
        """Rule 30 = 0b00011110.  Verify all 8 neighbourhoods."""
        # Rule 30 binary: 00011110
        # index: 7(111)->0, 6(110)->0, 5(101)->0, 4(100)->1,
        #        3(011)->1, 2(010)->1, 1(001)->1, 0(000)->0
        expected = {
            (1, 1, 1): 0, (1, 1, 0): 0, (1, 0, 1): 0, (1, 0, 0): 1,
            (0, 1, 1): 1, (0, 1, 0): 1, (0, 0, 1): 1, (0, 0, 0): 0,
        }
        for (l, c, r), exp in expected.items():
            assert apply_rule(30, l, c, r) == exp, f"Rule 30 failed for ({l},{c},{r})"

    def test_rule_90_known_outputs(self):
        """Rule 90 = 0b01011010 = XOR of left and right."""
        expected = {
            (1, 1, 1): 0, (1, 1, 0): 1, (1, 0, 1): 0, (1, 0, 0): 1,
            (0, 1, 1): 1, (0, 1, 0): 0, (0, 0, 1): 1, (0, 0, 0): 0,
        }
        for (l, c, r), exp in expected.items():
            assert apply_rule(90, l, c, r) == exp, f"Rule 90 failed for ({l},{c},{r})"

    def test_rule_110_known_outputs(self):
        """Rule 110 = 0b01101110."""
        expected = {
            (1, 1, 1): 0, (1, 1, 0): 1, (1, 0, 1): 1, (1, 0, 0): 0,
            (0, 1, 1): 1, (0, 1, 0): 1, (0, 0, 1): 1, (0, 0, 0): 0,
        }
        for (l, c, r), exp in expected.items():
            assert apply_rule(110, l, c, r) == exp, f"Rule 110 failed for ({l},{c},{r})"

    def test_returns_zero_or_one(self):
        for rule in [30, 90, 110, 0, 255]:
            for l in (0, 1):
                for c in (0, 1):
                    for r in (0, 1):
                        result = apply_rule(rule, l, c, r)
                        assert result in (0, 1)

    def test_rule_0_all_dead(self):
        """Rule 0: all outputs are 0."""
        for l in (0, 1):
            for c in (0, 1):
                for r in (0, 1):
                    assert apply_rule(0, l, c, r) == 0

    def test_rule_255_all_alive(self):
        """Rule 255: all outputs are 1."""
        for l in (0, 1):
            for c in (0, 1):
                for r in (0, 1):
                    assert apply_rule(255, l, c, r) == 1


# ---------------------------------------------------------------------------
# generate_automaton
# ---------------------------------------------------------------------------

class TestGenerateAutomaton:
    def test_grid_dimensions(self):
        grid = generate_automaton(30, width=21, steps=10)
        assert len(grid) == 11  # steps + 1 (initial row + 10 steps)
        assert all(len(row) == 21 for row in grid)

    def test_initial_row_single_center_cell(self):
        grid = generate_automaton(30, width=11, steps=5)
        row0 = grid[0]
        assert row0[5] == 1
        assert sum(row0) == 1  # only center cell is 1

    def test_values_are_binary(self):
        grid = generate_automaton(90, width=21, steps=15)
        for row in grid:
            for cell in row:
                assert cell in (0, 1)

    def test_rule_90_sierpinski_pattern(self):
        """Rule 90 from a single cell produces the Sierpiński triangle pattern.
        After step 1, cells at center-1 and center+1 should be 1 (XOR behaviour)."""
        grid = generate_automaton(90, width=11, steps=1)
        center = 5
        assert grid[1][center - 1] == 1
        assert grid[1][center] == 0
        assert grid[1][center + 1] == 1

    def test_rule_30_step1(self):
        """Rule 30 from a single center cell: after 1 step, cells at
        center-1, center, center+1 should be 1,1,1."""
        grid = generate_automaton(30, width=11, steps=1)
        center = 5
        assert grid[1][center - 1] == 1
        assert grid[1][center] == 1
        assert grid[1][center + 1] == 1


# ---------------------------------------------------------------------------
# Poster generation
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_returns_svg_element(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
        assert svg.tag.endswith("svg")

    def test_contains_automata_group(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        automata = svg.find(f".//{{{ns}}}g[@id='automata']")
        assert automata is not None

    def test_contains_rule_groups(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        for rule_id in ["rule-30", "rule-90", "rule-110"]:
            group = svg.find(f".//{{{ns}}}g[@id='{rule_id}']")
            assert group is not None, f"Missing group: {rule_id}"

    def test_contains_annotations_group(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        annotations = svg.find(f".//{{{ns}}}g[@id='annotations']")
        assert annotations is not None

    def test_contains_educational_group(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        edu = svg.find(f".//{{{ns}}}g[@id='educational']")
        assert edu is not None

    def test_automata_have_rectangles(self):
        """Each rule group should contain rectangle elements for cells."""
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
        ns = "http://www.w3.org/2000/svg"
        for rule_id in ["rule-30", "rule-90", "rule-110"]:
            group = svg.find(f".//{{{ns}}}g[@id='{rule_id}']")
            rects = group.findall(f"{{{ns}}}rect")
            assert len(rects) >= 1, f"No rectangles in {rule_id}"

    def test_default_dimensions(self):
        svg = generate_poster(cell_size=2, generations=10)
        assert svg.get("width") == "420mm"
        assert svg.get("height") == "594mm"

    def test_custom_dimensions(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=300, height_mm=400)
        assert svg.get("width") == "300mm"
        assert svg.get("height") == "400mm"

    def test_annotation_text_present(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Rule 30" in xml_str
        assert "Rule 90" in xml_str
        assert "Rule 110" in xml_str

    def test_educational_text_present(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Wolfram" in xml_str or "wolfram" in xml_str

    def test_credit_designed_by(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=200, height_mm=300,
                              designed_by="Alice")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice" in xml_str

    def test_credit_designed_for(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=200, height_mm=300,
                              designed_for="the Science Museum")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed for the Science Museum" in xml_str

    def test_credit_both(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=200, height_mm=300,
                              designed_by="Alice and Bob",
                              designed_for="ACME Labs")
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by Alice and Bob for ACME Labs" in xml_str

    def test_no_credit_by_default(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Designed by" not in xml_str

    def test_title_present(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=200, height_mm=300)
        xml_str = ET.tostring(svg, encoding="unicode")
        assert "Cellular Automata" in xml_str


# ---------------------------------------------------------------------------
# SVG file output
# ---------------------------------------------------------------------------

class TestWriteSvg:
    def test_writes_valid_svg_file(self):
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
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
        svg = generate_poster(cell_size=2, generations=10, width_mm=100, height_mm=150)
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
