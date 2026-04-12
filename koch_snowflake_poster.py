#!/usr/bin/env python3
"""
Koch Snowflake Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF/PNG) of the
Koch Snowflake fractal. Designed for large-format printing (A2+).

Usage:
    python koch_snowflake_poster.py [OPTIONS]

Options:
    --depth N            Recursion depth (default: 5)
    --output FILE        Output filename (default: koch_snowflake_poster.svg)
    --format FMT         Output format: svg, pdf, or png (default: svg)
    --dpi N              Resolution for PNG output in dots per inch (default: 150)
    --width MM           Poster width in mm (default: 420, A2 width)
    --height MM          Poster height in mm (default: 594, A2 height)
    --designed-by TEXT   Designer credit (e.g. 'Alice and Bob')
    --designed-for TEXT  Client / purpose credit (e.g. 'the Science Museum')
"""

import argparse
import math
from functools import partial

from poster_utils import (
    ACCENT_COLOR,
    ANNO_START_FRAC,
    ANNOTATION_STYLE,
    BASE_HEIGHT_MM,
    BASE_WIDTH_MM,
    BG_COLOR,
    COLUMN_CENTERS,
    CONTENT_TOP_MARGIN_FRAC,
    SERIF,
    TITLE_COLOR,
    _circle,
    _group,
    _line,
    _multiline_text,
    _polygon,
    _polyline,
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
    get_theme,
    ProgressReporter,
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def koch_curve_points(p1, p2, depth):
    """Recursively generate Koch curve points for a single edge.

    Returns a list of (x, y) points along the Koch curve from *p1* to *p2*
    at the given recursion *depth*.  The returned list starts with *p1* but
    does **not** include *p2* (so consecutive edges can be concatenated
    without duplicating shared vertices).
    """
    if depth == 0:
        return [p1]

    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1

    # Points dividing the segment into thirds
    a = (x1 + dx / 3, y1 + dy / 3)
    c = (x1 + 2 * dx / 3, y1 + 2 * dy / 3)

    # Peak of the equilateral triangle on the middle third.
    # Rotate the vector (dx/3, dy/3) by +60° around point A so the bump
    # points outward (away from the triangle interior).
    bx = a[0] + dx / 6 + dy * math.sqrt(3) / 6
    by = a[1] + dy / 6 - dx * math.sqrt(3) / 6
    b = (bx, by)

    pts = []
    pts.extend(koch_curve_points(p1, a, depth - 1))
    pts.extend(koch_curve_points(a, b, depth - 1))
    pts.extend(koch_curve_points(b, c, depth - 1))
    pts.extend(koch_curve_points(c, p2, depth - 1))
    return pts


def koch_snowflake_points(cx, cy, radius, depth):
    """Generate points of a Koch snowflake centred at (*cx*, *cy*).

    Parameters
    ----------
    cx, cy : float
        Centre of the circumscribing circle.
    radius : float
        Radius of the circumscribing circle (distance from centre to vertex).
    depth : int
        Recursion depth (0 = equilateral triangle).

    Returns
    -------
    list of (float, float)
        Ordered vertices of the Koch snowflake polygon.
    """
    # Equilateral triangle vertices (top, bottom-right, bottom-left)
    # oriented so one vertex points up.
    v0 = (cx, cy - radius)
    v1 = (cx + radius * math.sin(2 * math.pi / 3),
          cy - radius * math.cos(2 * math.pi / 3))
    v2 = (cx + radius * math.sin(4 * math.pi / 3),
          cy - radius * math.cos(4 * math.pi / 3))

    triangle = [v0, v1, v2]

    points = []
    for i in range(3):
        p1 = triangle[i]
        p2 = triangle[(i + 1) % 3]
        points.extend(koch_curve_points(p1, p2, depth))

    return points


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _draw_right_arrow(g, ns, cx, cy, length, color, scale):
    """Draw a right-pointing arrow centred at (cx, cy)."""
    head_w = length * 0.40
    head_h = length * 0.32
    shaft_x1 = cx - length / 2
    shaft_x2 = cx + length / 2 - head_w
    mid_y = cy
    sw = max(0.3, 0.3 * scale)
    _line(g, ns, shaft_x1, mid_y, shaft_x2, mid_y,
          stroke=color, **{"stroke-width": str(round(sw, 3))})
    tip_x = cx + length / 2
    _polygon(g, ns, [
        (tip_x, mid_y),
        (tip_x - head_w, mid_y - head_h / 2),
        (tip_x - head_w, mid_y + head_h / 2),
    ], fill=color)


def _annotation_infinite_perimeter(parent, ns, target_x, target_y,
                                   col_cx, anno_y, scale=1, theme=None):
    """Annotation: infinite perimeter callout."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Infinite Perimeter", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Each iteration multiplies the",
        "perimeter by 4/3. After n steps,",
        "P = 3s\u00b7(4/3)\u207f. As n grows, the",
        "perimeter grows without bound,",
        "yet the curve never crosses itself.",
    ], scale, theme=theme)
    return g


def _annotation_self_similarity(parent, ns, target_x, target_y,
                                col_cx, anno_y, scale=1, theme=None):
    """Annotation: self-similarity callout."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Self-Similarity", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Each of the three sides is a Koch",
        "curve. Zoom into any portion and",
        "the same pattern appears at every",
        "scale \u2014 a hallmark of fractal",
        "geometry.",
    ], scale, theme=theme)
    return g


def _annotation_dimension(parent, ns, target_x, target_y,
                          col_cx, anno_y, scale=1, theme=None):
    """Annotation: fractional (Hausdorff) dimension callout."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Fractional Dimension", scale, theme=theme,
                               show_line=False)

    dim_val = f"{math.log(4) / math.log(3):.4f}"
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "A line is 1-D. A surface is 2-D.",
        f"The Koch snowflake is {dim_val}-D!",
        "Its Hausdorff dimension is",
        "log(4)/log(3) \u2014 more than a line",
        "but less than a filled plane.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_construction(parent, ns, col_cx, anno_y, scale=1,
                        snowflake_color=None):
    """Panel: step-by-step construction with mini Koch curve segments."""
    if snowflake_color is None:
        snowflake_color = "#1C1C1C"
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale, "The Construction",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Begin with a straight segment.",
        "Divide it into thirds; replace the",
        "middle third with two sides of an",
        "equilateral triangle. Repeat on",
        "every new segment \u2014 forever.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Mini visual: single Koch curve segment at depths 0, 1, 2
    mini_y = anno_y + 40 * scale
    seg_len = 20 * scale
    for i, d in enumerate([0, 1, 2]):
        mini_cx = col_cx + (-24 + i * 24) * scale
        p1 = (mini_cx - seg_len / 2, mini_y)
        p2 = (mini_cx + seg_len / 2, mini_y)
        pts = koch_curve_points(p1, p2, d) + [p2]
        sw = max(0.3, 0.4 * scale)
        _polyline(g, ns, pts, fill="none", stroke=snowflake_color,
                  **{"stroke-width": str(round(sw, 3)),
                     "stroke-linejoin": "round",
                     "opacity": "0.85"})
        _text(g, ns, mini_cx, mini_y + 8 * scale, f"depth {d}",
              **{**ANNOTATION_STYLE, "font-size": str(round(3 * scale, 2)),
                 "text-anchor": "middle"})
        if i < 2:
            arrow_color = ANNOTATION_STYLE.get("fill", "#1C1C1C")
            _draw_right_arrow(g, ns, mini_cx + 12 * scale,
                              mini_y - 2 * scale,
                              8 * scale, arrow_color, scale)

    return g


def _panel_area_paradox(parent, ns, col_cx, anno_y, scale=1,
                        snowflake_color=None):
    """Panel: area convergence paradox with formula."""
    if snowflake_color is None:
        snowflake_color = "#1C1C1C"
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale, "Area Paradox",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Despite its infinite perimeter, the",
        "Koch snowflake encloses a finite",
        "area. It converges to exactly 8/5",
        "of the original triangle\u2019s area:",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    formula_y = anno_y + 33 * scale
    _text(g, ns, col_cx, formula_y,
          "A = (2s\u00b2\u221a3) / 5",
          **{**ANNOTATION_STYLE, "font-size": str(round(4.2 * scale, 2)),
             "font-style": "italic", "text-anchor": "middle"})
    # Render "Perimeter(n) = 3s·(4/3)ⁿ → ∞" using an SVG-path arrow so the
    # rendered PNG does not depend on the font having the U+2192 glyph.
    peri_y = formula_y + 7 * scale
    arrow_len = 6 * scale
    arrow_cx = col_cx
    arrow_cy = peri_y - 1.5 * scale
    text_gap = 1 * scale
    formula_style = {**ANNOTATION_STYLE,
                     "font-size": str(round(4.2 * scale, 2)),
                     "font-style": "italic"}
    _text(g, ns, arrow_cx - arrow_len / 2 - text_gap, peri_y,
          "Perimeter(n) = 3s\u00b7(4/3)\u207f",
          **{**formula_style, "text-anchor": "end"})
    arrow_color = ANNOTATION_STYLE.get("fill", "#1C1C1C")
    _draw_right_arrow(g, ns, arrow_cx, arrow_cy, arrow_len, arrow_color, scale)
    _text(g, ns, arrow_cx + arrow_len / 2 + text_gap, peri_y,
          "\u221e",
          **{**formula_style, "text-anchor": "start"})

    # Mini snowflakes at increasing depth
    demo_y = anno_y + 55 * scale
    for i, (d, label) in enumerate([(0, "n=0"), (1, "n=1"), (2, "n=2")]):
        cx = col_cx + (-18 + i * 18) * scale
        r = 6 * scale
        pts = koch_snowflake_points(cx, demo_y, r, d)
        _polygon(g, ns, pts, fill=snowflake_color, opacity="0.8")
        _text(g, ns, cx, demo_y + 11 * scale, label,
              **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
                 "text-anchor": "middle"})

    return g


def _panel_variations(parent, ns, col_cx, anno_y, scale=1,
                      snowflake_color=None):
    """Panel: snowflake variations — anti-snowflake, Koch curve, higher-order."""
    if snowflake_color is None:
        snowflake_color = "#1C1C1C"
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale, "Snowflake Variations",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The anti-snowflake points its",
        "bumps inward, creating a shape",
        "that tiles with the original. A",
        "single Koch curve forms one side.",
        "Higher-order variants use squares",
        "or other polygons as generators.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Mini demos: regular snowflake, anti-snowflake outline, single Koch curve
    demo_y = anno_y + 50 * scale

    # Regular snowflake (small)
    cx1 = col_cx - 20 * scale
    r_demo = 6 * scale
    pts_reg = koch_snowflake_points(cx1, demo_y, r_demo, 2)
    _polygon(g, ns, pts_reg, fill=snowflake_color, opacity="0.7")
    _text(g, ns, cx1, demo_y + 11 * scale, "snowflake",
          **{**ANNOTATION_STYLE, "font-size": str(round(2.6 * scale, 2)),
             "text-anchor": "middle"})

    # Anti-snowflake (bumps inward) — draw as outline
    cx2 = col_cx
    pts_anti = _anti_snowflake_points(cx2, demo_y, r_demo, 2)
    _polygon(g, ns, pts_anti, fill="none", stroke=snowflake_color,
             **{"stroke-width": str(round(0.3 * scale, 3)),
                "opacity": "0.7"})
    _text(g, ns, cx2, demo_y + 11 * scale, "anti-snowflake",
          **{**ANNOTATION_STYLE, "font-size": str(round(2.6 * scale, 2)),
             "text-anchor": "middle"})

    # Single Koch curve
    cx3 = col_cx + 20 * scale
    seg_len = 12 * scale
    p1 = (cx3 - seg_len / 2, demo_y)
    p2 = (cx3 + seg_len / 2, demo_y)
    pts_curve = koch_curve_points(p1, p2, 3) + [p2]
    _polyline(g, ns, pts_curve, fill="none", stroke=snowflake_color,
              **{"stroke-width": str(round(0.3 * scale, 3)),
                 "stroke-linejoin": "round",
                 "opacity": "0.7"})
    _text(g, ns, cx3, demo_y + 11 * scale, "Koch curve",
          **{**ANNOTATION_STYLE, "font-size": str(round(2.6 * scale, 2)),
             "text-anchor": "middle"})

    return g


def _anti_snowflake_points(cx, cy, radius, depth):
    """Generate an anti-snowflake (bumps point inward)."""
    v0 = (cx, cy - radius)
    v1 = (cx + radius * math.sin(2 * math.pi / 3),
          cy - radius * math.cos(2 * math.pi / 3))
    v2 = (cx + radius * math.sin(4 * math.pi / 3),
          cy - radius * math.cos(4 * math.pi / 3))

    # Reverse winding so bumps point inward
    triangle = [v0, v2, v1]

    points = []
    for i in range(3):
        p1 = triangle[i]
        p2 = triangle[(i + 1) % 3]
        points.extend(koch_curve_points(p1, p2, depth))

    return points


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

def generate_poster(depth=5, width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None,
                    verbose=True):
    """Build and return the full poster as an ElementTree SVG root."""
    t = get_theme(theme)
    snowflake_color = t["content_primary"]

    sc = build_poster_scaffold(
        title="The Koch Snowflake",
        subtitle="Infinite perimeter, finite area",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Main fractal ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.03)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    margin = ca["margin"]

    avail_h = max_bot - min_top
    avail_w = width_mm - 2 * margin

    # Fit the snowflake in the content area
    radius = min(avail_w, avail_h) / 2 * 0.92
    snowflake_cx = width_mm / 2
    snowflake_cy = min_top + avail_h / 2

    fractal_group = _group(svg, ns, id="fractal")

    num_sides = 3 * (4 ** depth)
    _ps = (ProgressReporter(num_sides, "Koch: points")
           if verbose else None)

    points = koch_snowflake_points(snowflake_cx, snowflake_cy,
                                   radius, depth)
    if _ps:
        _ps.update(num_sides)
        _ps.done()

    _polygon(fractal_group, ns, points,
             fill=snowflake_color, stroke=snowflake_color,
             opacity="0.92",
             **{"stroke-width": str(round(0.15 * w_scale, 3)),
                "stroke-linejoin": "round"})

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    # Compute snowflake bounding box for separator placement
    ys = [p[1] for p in points]
    fractal_bottom = max(ys)
    anno_sep_y = fractal_bottom + 10 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Target points on the snowflake for annotation callouts
    perim_target_x = snowflake_cx - radius * 0.5
    perim_target_y = snowflake_cy - radius * 0.3

    ss_target_x = snowflake_cx + radius * 0.5
    ss_target_y = snowflake_cy - radius * 0.3

    dim_target_x = snowflake_cx
    dim_target_y = snowflake_cy + radius * 0.5

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_infinite_perimeter,
             perim_target_x, perim_target_y),
            (_annotation_self_similarity,
             ss_target_x, ss_target_y),
            (_annotation_dimension,
             dim_target_x, dim_target_y),
        ],
        w_scale,
        theme=theme,
    )

    # --- Second row: educational panels ---
    edu_group = _group(svg, ns, id="educational")

    row2_sep_y = anno_y + 55 * w_scale
    draw_row_separator(edu_group, ns, width_mm, row2_sep_y, w_scale,
                       opacity="0.35", theme=theme)

    row2_y = row2_sep_y + 12 * w_scale

    _panel_construction(edu_group, ns, col1_cx, row2_y, w_scale,
                        snowflake_color=snowflake_color)
    _panel_area_paradox(edu_group, ns, col2_cx, row2_y, w_scale,
                        snowflake_color=snowflake_color)
    _panel_variations(edu_group, ns, col3_cx, row2_y, w_scale,
                      snowflake_color=snowflake_color)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Helge von Koch first described this curve in 1904."
        ),
        secondary_line=(
            f"Generated at depth {depth}  \u00b7  "
            f"{num_sides:,} sides"
        ),
        designed_by=designed_by,
        designed_for=designed_for,
        theme=theme,
    )

    return svg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser():
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate an annotated Koch Snowflake poster.",
    )
    parser.add_argument(
        "--depth", type=int, default=5,
        help="Recursion depth (default: 5). Higher = more detail.",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        depth=args.depth,
        width_mm=args.width,
        height_mm=args.height,
        designed_by=args.designed_by,
        designed_for=args.designed_for,
        theme=args.theme,
    )


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    run_poster_main(
        build_arg_parser, _generate_from_args,
        filename_prefix="koch_snowflake_poster",
        poster_label=f"Koch Snowflake poster (depth={args.depth})",
        argv=argv,
    )


if __name__ == "__main__":
    main()
