#!/usr/bin/env python3
"""
Cellular Automata Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of
Elementary Cellular Automata — the one-dimensional systems studied by
Stephen Wolfram that demonstrate how extraordinarily simple rules can
produce complex, even computationally universal behaviour.

Usage:
    python cellular_automata_poster.py [OPTIONS]

Options:
    --cell-size N        Cell size in mm (default: 2)
    --generations N      Number of generations to simulate (default: 150)
    --output FILE        Output filename (default: cellular_automata_poster.svg)
    --format FMT         Output format: svg, pdf, or png (default: svg)
    --dpi N              Resolution for PNG output in dots per inch (default: 150)
    --width MM           Poster width in mm (default: 420, A2 width)
    --height MM          Poster height in mm (default: 594, A2 height)
    --designed-by TEXT   Designer credit (e.g. 'Alice and Bob')
    --designed-for TEXT  Client / purpose credit (e.g. 'the Science Museum')
"""

import argparse
import xml.etree.ElementTree as ET

from poster_utils import (
    ACCENT_COLOR,
    ANNOTATION_STYLE,
    BASE_HEIGHT_MM,
    BASE_WIDTH_MM,
    COLUMN_CENTERS,
    FOOTER_PRIMARY_COLOR,
    SERIF,
    _circle,
    _group,
    _multiline_text,
    _rect,
    _text,
    add_common_poster_args,
    build_poster_scaffold,
    content_area,
    draw_annotation_body,
    draw_annotation_header,
    draw_annotation_row,
    draw_row_separator,
    finalize_poster,
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Cellular automaton helpers
# ---------------------------------------------------------------------------

def apply_rule(rule_number, left, center, right):
    """Apply an elementary cellular automaton rule to a three-cell neighbourhood.

    The three cells form a 3-bit index (left as the most significant bit).
    The corresponding bit of *rule_number* gives the new cell value.

    Parameters
    ----------
    rule_number : int
        Rule number (0–255).
    left, center, right : int
        Current states (0 or 1) of the left, centre, and right neighbours.

    Returns
    -------
    int
        New cell value (0 or 1).
    """
    index = (left << 2) | (center << 1) | right
    return (rule_number >> index) & 1


def generate_automaton(rule_number, width, steps):
    """Generate a 2-D grid for an elementary cellular automaton.

    Starts from a single 1 in the centre of the first row and applies
    the rule for *steps* generations.

    Parameters
    ----------
    rule_number : int
        Rule number (0–255).
    width : int
        Number of cells per row.
    steps : int
        Number of generations (rows) to produce after the initial row.

    Returns
    -------
    list[list[int]]
        A grid of *steps* + 1 rows, each of length *width*, with values
        0 or 1.
    """
    row = [0] * width
    row[width // 2] = 1
    grid = [row]
    for _ in range(steps):
        prev = grid[-1]
        new_row = [0] * width
        for j in range(width):
            left = prev[j - 1] if j > 0 else 0
            center = prev[j]
            right = prev[j + 1] if j < width - 1 else 0
            new_row[j] = apply_rule(rule_number, left, center, right)
        grid.append(new_row)
    return grid


# ---------------------------------------------------------------------------
# Poster-specific colours
# ---------------------------------------------------------------------------

CELL_COLORS = {
    30: "#1C1C1C",
    90: "#8B0000",
    110: "#2E5090",
}


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_rule_30(parent, ns, target_x, target_y,
                        col_cx, anno_y, scale=1):
    """Annotation: Rule 30's chaotic, pseudo-random output."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Rule 30 \u2014 Chaos", scale)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "From a single seed, Rule 30 produces",
        "irregular, pseudo-random output that",
        "defies prediction. Wolfram chose it",
        "as the random number generator in",
        "Mathematica \u2014 proof that simple",
        "deterministic rules can mimic noise.",
    ], scale)
    return g


def _annotation_rule_90(parent, ns, target_x, target_y,
                        col_cx, anno_y, scale=1):
    """Annotation: Rule 90 and the Sierpi\u0144ski triangle."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Rule 90 \u2014 Sierpi\u0144ski", scale)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Rule 90 generates the Sierpi\u0144ski",
        "triangle \u2014 a fractal that also appears",
        "when you shade the odd entries of",
        "Pascal\u2019s triangle. This equivalence",
        "to Pascal\u2019s triangle mod 2 links",
        "automata to classical combinatorics.",
    ], scale)
    return g


def _annotation_rule_110(parent, ns, target_x, target_y,
                         col_cx, anno_y, scale=1):
    """Annotation: Rule 110's Turing-completeness."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Rule 110 \u2014 Universal", scale)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "In 2004, Matthew Cook proved that",
        "Rule 110 is Turing-complete: it can",
        "simulate any computation. A one-",
        "dimensional row of cells with the",
        "simplest possible update rule is, in",
        "principle, a universal computer.",
    ], scale)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_how_it_works(parent, ns, col_cx, anno_y, scale=1):
    """Panel: how elementary cellular automata rules are encoded."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "How It Works",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Each cell looks at itself and its two",
        "neighbours \u2014 eight possible patterns",
        "of three cells. A rule assigns a new",
        "value (0 or 1) to each pattern. These",
        "eight bits form the rule number: an",
        "8-bit integer from 0 to 255. That",
        "single number fully determines the",
        "automaton\u2019s behaviour for all time.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_wolfram_classes(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Wolfram's four classes of automata behaviour."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Wolfram\u2019s Four Classes",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Wolfram classified all 256 rules into",
        "four classes: I. uniform (all cells",
        "settle to one state), II. periodic",
        "(stable repeating structures), III.",
        "chaotic (pseudo-random, like Rule 30),",
        "and IV. complex (localised structures",
        "that interact \u2014 like Rule 110). Class",
        "IV sits at the edge of chaos.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_computation(parent, ns, col_cx, anno_y, scale=1):
    """Panel: universal computation and 'A New Kind of Science'."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "A New Kind of Science",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "In 2002, Stephen Wolfram argued that",
        "simple programs \u2014 not equations \u2014 are",
        "the key to modelling nature. Cellular",
        "automata appear in crystal growth,",
        "pigmentation patterns, and traffic",
        "flow. Rule 110\u2019s universality shows",
        "that even the simplest rules can, in",
        "principle, perform any computation.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

def generate_poster(cell_size=2, generations=150,
                    width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    cell_size : int
        Size of each cell square in SVG user units (default: 2).
    generations : int
        Number of generations (rows) to simulate (default: 150).
    width_mm, height_mm : float
        Poster dimensions in millimetres (default: A2).
    designed_by, designed_for : str or None
        Optional credit lines.

    Returns
    -------
    xml.etree.ElementTree.Element
        The root ``<svg>`` element.
    """
    sc = build_poster_scaffold(
        title="Elementary Cellular Automata",
        subtitle="Simple rules, complex worlds",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    avail_h = ca["avail_h"]

    # Grid dimensions: width = 2 * generations + 1 to allow full spread
    grid_width = 2 * generations + 1

    # --- Column centres ---
    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Panel width ~ 28% of poster width
    panel_w = width_mm * 0.28

    rules = [30, 90, 110]
    col_centers = [col1_cx, col2_cx, col3_cx]

    # --- Draw the three automata ---
    automata_group = _group(svg, ns, id="automata")

    # Reserve space for labels below the grid
    label_gap = 8 * h_scale

    # Scale cells to fit within the available height and panel width
    max_cell_h = (avail_h - label_gap) / (generations + 1)
    max_cell_w = panel_w / grid_width
    fit_cell = min(max_cell_h, max_cell_w, cell_size)

    grid_px_w = grid_width * fit_cell
    grid_px_h = (generations + 1) * fit_cell

    for rule_num, col_cx in zip(rules, col_centers):
        grid = generate_automaton(rule_num, grid_width, generations)
        color = CELL_COLORS.get(rule_num, "#1C1C1C")

        # Top-left corner of this automaton's grid
        gx = col_cx - grid_px_w / 2
        gy = min_top + (avail_h - label_gap - grid_px_h) / 2

        rule_group = _group(automata_group, ns, id=f"rule-{rule_num}")

        for row_idx, row in enumerate(grid):
            for col_idx, cell in enumerate(row):
                if cell:
                    _rect(rule_group, ns,
                          round(gx + col_idx * fit_cell, 2),
                          round(gy + row_idx * fit_cell, 2),
                          round(fit_cell, 2),
                          round(fit_cell, 2),
                          fill=color)

        # Label below the grid
        _text(svg, ns, col_cx, gy + grid_px_h + 6 * h_scale,
              f"Rule {rule_num}",
              **{
                  "font-family": SERIF,
                  "font-size": str(round(5 * w_scale, 2)),
                  "fill": ACCENT_COLOR,
                  "text-anchor": "middle",
              })

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale, opacity="0.5")

    anno_y = anno_sep_y + 18 * h_scale

    # Arrow targets: centre-top of each automaton panel
    target_y = min_top + (avail_h - label_gap - grid_px_h) / 2 + grid_px_h * 0.3

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_rule_30, col1_cx, target_y),
            (_annotation_rule_90, col2_cx, target_y),
            (_annotation_rule_110, col3_cx, target_y),
        ],
        w_scale,
    )

    # --- Second row: educational panels ---
    edu_group = _group(svg, ns, id="educational")

    row2_sep_y = anno_y + 55 * w_scale
    draw_row_separator(edu_group, ns, width_mm, row2_sep_y, w_scale, opacity="0.35")

    row2_y = row2_sep_y + 12 * w_scale

    _panel_how_it_works(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_wolfram_classes(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_computation(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Stephen Wolfram\u2019s elementary cellular automata, "
            "explored in A New Kind of Science (2002)."
        ),
        secondary_line=(
            f"Generated with cell size {cell_size}  "
            f"\u00b7  {generations} generations  "
            f"\u00b7  Rules 30, 90, 110"
        ),
        designed_by=designed_by,
        designed_for=designed_for,
    )

    return svg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser():
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate an annotated Elementary Cellular Automata poster.",
    )
    parser.add_argument(
        "--cell-size", type=int, default=2, dest="cell_size",
        help="Cell size in mm (default: 2).",
    )
    parser.add_argument(
        "--generations", type=int, default=150,
        help="Number of generations to simulate (default: 150).",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        cell_size=args.cell_size,
        generations=args.generations,
        width_mm=args.width,
        height_mm=args.height,
        designed_by=args.designed_by,
        designed_for=args.designed_for,
    )


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    run_poster_main(
        build_arg_parser, _generate_from_args,
        filename_prefix="cellular_automata_poster",
        poster_label=(
            f"Cellular Automata poster "
            f"(cell_size={args.cell_size}, generations={args.generations})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
