#!/usr/bin/env python3
"""
Sierpiński Triangle Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF/PNG) of the
Sierpiński Triangle fractal. Designed for large-format printing (A2+).

Usage:
    python sierpinski_poster.py [OPTIONS]

Options:
    --depth N            Recursion depth (default: 7)
    --output FILE        Output filename (default: sierpinski_poster.svg)
    --format FMT         Output format: svg, pdf, or png (default: svg)
    --dpi N              Resolution for PNG output in dots per inch (default: 150)
    --width MM           Poster width in mm (default: 420, A2 width)
    --height MM          Poster height in mm (default: 594, A2 height)
    --designed-by TEXT   Designer credit (e.g. 'Alice and Bob')
    --designed-for TEXT  Client / purpose credit (e.g. 'the Science Museum')
"""

import argparse
import math

from poster_utils import (
    ACCENT_COLOR,
    ANNO_START_FRAC,
    ANNOTATION_STYLE,
    BASE_HEIGHT_MM,
    BASE_WIDTH_MM,
    BG_COLOR,
    CALLOUT_LINE_STYLE,
    COLUMN_CENTERS,
    CONTENT_TOP_MARGIN_FRAC,
    SERIF,
    TITLE_COLOR,
    _circle,
    _group,
    _multiline_text,
    _polygon,
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
# Geometry helpers
# ---------------------------------------------------------------------------

def equilateral_triangle_vertices(cx, cy, side_length):
    """Return three vertices of an equilateral triangle centred at (cx, cy)."""
    h = side_length * math.sqrt(3) / 2
    top = (cx, cy - 2 * h / 3)
    bottom_left = (cx - side_length / 2, cy + h / 3)
    bottom_right = (cx + side_length / 2, cy + h / 3)
    return [top, bottom_left, bottom_right]


def midpoint(p1, p2):
    """Return the midpoint between two 2-D points."""
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


# ---------------------------------------------------------------------------
# Sierpiński triangle – iterative filled-triangle collector
# ---------------------------------------------------------------------------

def sierpinski_triangles(vertices, depth):
    """Yield filled triangle vertex-lists for the Sierpiński fractal.

    Uses an iterative stack instead of call-stack recursion so that deep
    depths do not hit Python's recursion limit.
    """
    stack = [(vertices, depth)]
    while stack:
        tri, d = stack.pop()
        if d == 0:
            yield tri
        else:
            a, b, c = tri
            ab = midpoint(a, b)
            bc = midpoint(b, c)
            ac = midpoint(a, c)
            stack.append(([a, ab, ac], d - 1))
            stack.append(([ab, b, bc], d - 1))
            stack.append(([ac, bc, c], d - 1))


# ---------------------------------------------------------------------------
# Poster-specific colour
# ---------------------------------------------------------------------------

TRIANGLE_COLOR = "#1C1C1C"  # near-black ink


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_self_similarity(parent, ns, target_x, target_y,
                                col_cx, anno_y, scale=1):
    """Annotation: self-similarity callout (below the fractal)."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Self-Similarity", scale)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Every smaller triangle is an exact",
        "copy of the whole shape. Zoom in",
        "anywhere \u2014 the same pattern",
        "repeats at every scale, forever.",
    ], scale)
    return g


def _annotation_recursion(parent, ns, target_x, target_y,
                           col_cx, anno_y, scale=1):
    """Annotation: recursion callout with step diagram (below the fractal)."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Recursion", scale)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Start with one triangle. Remove the",
        "centre to get three smaller copies.",
        "Repeat on each copy \u2014 that\u2019s recursion!",
    ], scale)

    # Mini step diagram: 3 tiny triangles showing depth 0, 1, 2 — centred at col_cx
    mini_y = anno_y + 32 * scale
    for i, d in enumerate([0, 1, 2]):
        mini_cx = col_cx + (-22 + i * 22) * scale
        side = 14 * scale
        verts = equilateral_triangle_vertices(mini_cx, mini_y, side)
        for tri in sierpinski_triangles(verts, d):
            _polygon(g, ns, tri, fill=TRIANGLE_COLOR, opacity="0.85")
        _text(g, ns, mini_cx, mini_y + 13 * scale, f"depth {d}",
              **{**ANNOTATION_STYLE, "font-size": str(round(3 * scale, 2)),
                 "text-anchor": "middle"})
        if i < 2:
            _text(g, ns, mini_cx + 8 * scale, mini_y, "\u2192",
                  **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2))})

    return g


def _annotation_dimension(parent, ns, target_x, target_y,
                           col_cx, anno_y, scale=1):
    """Annotation: fractional (Hausdorff) dimension callout (below fractal)."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Fractional Dimension", scale)

    dim_val = f"{math.log(3) / math.log(2):.4f}"
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "A line is 1-D. A square is 2-D.",
        f"This fractal is {dim_val}-D!",
        "It\u2019s the Hausdorff dimension \u2014 not",
        "quite a line, not quite a plane,",
        "somewhere magically in between.",
    ], scale)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_pascal(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Pascal\u2019s triangle mod 2 \u2192 Sierpi\u0144ski pattern."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Hidden in Pascal\u2019s Triangle",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Color the odd entries of Pascal\u2019s",
        "triangle and the Sierpi\u0144ski",
        "pattern emerges \u2014 a bridge between",
        "number theory and geometry.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Pascal's triangle mod 2 — rows of small squares, centred at col_cx
    cell = 3.2 * scale
    gap = 0.4 * scale
    step = cell + gap
    base_y = anno_y + 33 * scale
    center_x = col_cx
    num_rows = 8

    for n in range(num_rows):
        row_start_x = center_x - n * step / 2
        for k in range(n + 1):
            is_odd = (n & k) == k
            rx = row_start_x + k * step
            ry = base_y + n * step
            fill = TRIANGLE_COLOR if is_odd else "none"
            opacity = "0.85" if is_odd else "0.15"
            _rect(g, ns, rx, ry, cell, cell,
                  fill=fill, stroke=TRIANGLE_COLOR,
                  **{"stroke-width": str(round(0.15 * scale, 3)),
                     "opacity": opacity})

    return g


def _panel_chaos_game(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the chaos game algorithm with dot demonstration."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale, "The Chaos Game",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Pick any starting point inside the",
        "triangle. Choose a random vertex \u2014",
        "jump halfway there. Repeat forever.",
        "The dots trace the Sierpi\u0144ski triangle!",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Small demonstration: chaos game scatter dots centred at col_cx
    tri_cx = col_cx
    tri_cy = anno_y + 48 * scale
    tri_side = 32 * scale
    demo_verts = equilateral_triangle_vertices(tri_cx, tri_cy, tri_side)

    _polygon(g, ns, demo_verts, fill="none", stroke=TRIANGLE_COLOR,
             **{"stroke-width": str(round(0.2 * scale, 3)), "opacity": "0.2"})

    labels = ["A", "B", "C"]
    offsets = [(0, -3), (-4, 4), (4, 4)]
    for v, label, (dx, dy) in zip(demo_verts, labels, offsets):
        _text(g, ns, v[0] + dx * scale, v[1] + dy * scale, label,
              **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
                 "fill": ACCENT_COLOR, "text-anchor": "middle"})

    x = (demo_verts[0][0] + demo_verts[1][0]) / 2
    y = (demo_verts[0][1] + demo_verts[1][1]) / 2
    seed = 42
    dot_r = 0.3 * scale
    for i in range(210):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        vi = seed % 3
        vx, vy = demo_verts[vi]
        x = (x + vx) / 2
        y = (y + vy) / 2
        if i >= 10:
            _circle(g, ns, x, y, dot_r,
                    fill=TRIANGLE_COLOR, opacity="0.55")

    return g


def _panel_area_paradox(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the area/perimeter paradox with formula and visual."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale, "The Area Paradox",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "At each step, \u00BC of remaining area",
        "is removed. After infinitely many",
        "steps the total area reaches zero \u2014",
        "yet the boundary length grows",
        "without limit!",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    formula_y = anno_y + 40 * scale
    _text(g, ns, col_cx, formula_y,
          "Area(n) = (\u00BE)\u207F \u2192 0",
          **{**ANNOTATION_STYLE, "font-size": str(round(4.2 * scale, 2)),
             "font-style": "italic", "text-anchor": "middle"})
    _text(g, ns, col_cx, formula_y + 7 * scale,
          "Perimeter(n) \u2192 \u221E",
          **{**ANNOTATION_STYLE, "font-size": str(round(4.2 * scale, 2)),
             "font-style": "italic", "text-anchor": "middle"})

    demo_y = anno_y + 58 * scale
    for i, (d, label) in enumerate([(0, "n=0"), (1, "n=1"), (3, "n=3")]):
        cx = col_cx + (-18 + i * 18) * scale
        side = 12 * scale
        verts = equilateral_triangle_vertices(cx, demo_y, side)
        for tri in sierpinski_triangles(verts, d):
            _polygon(g, ns, tri, fill=TRIANGLE_COLOR, opacity="0.8")
        _text(g, ns, cx, demo_y + 12 * scale, label,
              **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
                 "text-anchor": "middle"})

    return g


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

def generate_poster(depth=7, width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None):
    """Build and return the full poster as an ElementTree SVG root."""
    sc = build_poster_scaffold(
        title="The Sierpi\u0144ski Triangle",
        subtitle="A fractal of infinite complexity from a simple rule",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Main fractal ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.12)
    min_top, max_bot = ca["min_top"], ca["max_bot"]

    margin = width_mm * 0.12
    tri_side = width_mm - 2 * margin
    tri_h = tri_side * math.sqrt(3) / 2

    tri_top = min_top
    tri_bot = tri_top + tri_h
    if tri_bot > max_bot:
        tri_h = max_bot - min_top
        tri_side = tri_h * 2 / math.sqrt(3)

    tri_cx = width_mm / 2
    tri_cy = min_top + 2 * tri_h / 3

    vertices = equilateral_triangle_vertices(tri_cx, tri_cy, tri_side)

    fractal_group = _group(svg, ns, id="fractal")
    for tri in sierpinski_triangles(vertices, depth):
        _polygon(fractal_group, ns, tri,
                 fill=TRIANGLE_COLOR, stroke="none", opacity="0.92")

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    fractal_bottom = vertices[1][1]
    anno_sep_y = fractal_bottom + 10 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale, opacity="0.5")

    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    ab = midpoint(vertices[0], vertices[1])
    ac = midpoint(vertices[0], vertices[2])
    bc = midpoint(vertices[1], vertices[2])

    ss_target_x = (vertices[0][0] + ab[0] + ac[0]) / 3
    ss_target_y = (vertices[0][1] + ab[1] + ac[1]) / 3

    rec_target_x = (ab[0] + ac[0] + bc[0]) / 3
    rec_target_y = (ab[1] + ac[1] + bc[1]) / 3

    dim_target_x = (ac[0] + bc[0] + vertices[2][0]) / 3
    dim_target_y = (ac[1] + bc[1] + vertices[2][1]) / 3

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_self_similarity, ss_target_x, ss_target_y),
            (_annotation_recursion, rec_target_x, rec_target_y),
            (_annotation_dimension, dim_target_x, dim_target_y),
        ],
        w_scale,
    )

    # --- Second row: educational connections ---
    edu_group = _group(svg, ns, id="educational")

    row2_sep_y = anno_y + 55 * w_scale
    draw_row_separator(edu_group, ns, width_mm, row2_sep_y, w_scale, opacity="0.35")

    row2_y = row2_sep_y + 12 * w_scale

    _panel_pascal(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_chaos_game(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_area_paradox(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Wac\u0142aw Sierpi\u0144ski first described this fractal in 1915."
        ),
        secondary_line=(
            f"Generated at depth {depth}  \u00b7  {3**depth:,} triangles"
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
        description="Generate an annotated Sierpiński Triangle poster.",
    )
    parser.add_argument(
        "--depth", type=int, default=7,
        help="Recursion depth (default: 7). Higher = more detail.",
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
    )


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    run_poster_main(
        build_arg_parser, _generate_from_args,
        filename_prefix="sierpinski_poster",
        poster_label=f"Sierpiński Triangle poster (depth={args.depth})",
        argv=argv,
    )


if __name__ == "__main__":
    main()
