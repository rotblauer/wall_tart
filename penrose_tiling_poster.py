#!/usr/bin/env python3
"""
Penrose Tiling Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of a Penrose
Tiling — the celebrated aperiodic pattern discovered by Roger Penrose that
tiles the plane without ever repeating, exhibiting forbidden five-fold
symmetry and deep connections to the golden ratio.

Usage:
    python penrose_tiling_poster.py [OPTIONS]

Options:
    --subdivisions N     Number of subdivision steps (default: 5)
    --output FILE        Output filename (default: penrose_tiling_poster.svg)
    --format FMT         Output format: svg, pdf, or png (default: svg)
    --dpi N              Resolution for PNG output in dots per inch (default: 150)
    --width MM           Poster width in mm (default: 420, A2 width)
    --height MM          Poster height in mm (default: 594, A2 height)
    --designed-by TEXT   Designer credit (e.g. 'Alice and Bob')
    --designed-for TEXT  Client / purpose credit (e.g. 'the Science Museum')
"""

import argparse
import math
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
    _line,
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
    get_theme,
    ProgressReporter,
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Penrose tiling helpers
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2

THIN = 0    # Golden triangle — 36° apex, base angles 72°
THICK = 1   # Golden gnomon  — 108° apex, base angles 36°


def create_initial_wheel(cx, cy, radius):
    """Create a wheel of 10 golden triangles arranged around *(cx, cy)*.

    The ten thin (type 0) triangles have their 36° apex at the centre and
    their bases on a circle of the given *radius*, forming a regular decagon.

    Parameters
    ----------
    cx, cy : float
        Centre of the wheel.
    radius : float
        Distance from the centre to the outer vertices.

    Returns
    -------
    list[tuple]
        List of ``(type, A, B, C)`` triangles.
    """
    triangles = []
    for i in range(10):
        angle = 2 * math.pi * i / 10
        next_angle = 2 * math.pi * (i + 1) / 10
        b = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
        c = (cx + radius * math.cos(next_angle),
             cy + radius * math.sin(next_angle))
        # Alternate winding so adjacent triangles share a consistent
        # edge orientation, which keeps subdivisions seamless.
        if i % 2 == 0:
            triangles.append((THIN, (cx, cy), b, c))
        else:
            triangles.append((THIN, (cx, cy), c, b))
    return triangles


def subdivide_triangles(triangles):
    """Perform one level of Robinson triangle subdivision.

    Thin (type 0) triangles split into 1 thin + 1 thick = 2 sub-triangles.
    Thick (type 1) triangles split into 1 thin + 2 thick = 3 sub-triangles.

    The golden ratio φ determines the split points along triangle edges.

    Parameters
    ----------
    triangles : list[tuple]
        Each element is ``(type, A, B, C)`` with vertices as ``(x, y)``
        tuples.

    Returns
    -------
    list[tuple]
        Subdivided triangles in the same format.
    """
    result = []
    for tri_type, (ax, ay), (bx, by), (vx, vy) in triangles:
        if tri_type == THIN:
            # Golden triangle: A is the 36° apex.
            # P = A + (B − A) / φ
            p = (ax + (bx - ax) / PHI, ay + (by - ay) / PHI)
            result.append((THIN, (vx, vy), p, (bx, by)))
            result.append((THICK, p, (vx, vy), (ax, ay)))
        else:
            # Golden gnomon: A is the 108° apex.
            # Q = B + (C − B) / φ,  R = C + (B − C) / φ
            q = (bx + (vx - bx) / PHI, by + (vy - by) / PHI)
            r = (vx + (bx - vx) / PHI, vy + (by - vy) / PHI)
            result.append((THICK, r, (ax, ay), (bx, by)))
            result.append((THIN, (ax, ay), r, q))
            result.append((THICK, q, (vx, vy), (ax, ay)))
    return result


def generate_penrose_tiling(cx, cy, radius, subdivisions, progress=None):
    """Generate a Penrose tiling as a list of Robinson triangles.

    Starts with a wheel of 10 golden triangles centred at *(cx, cy)* and
    applies *subdivisions* rounds of Robinson-triangle subdivision.

    Parameters
    ----------
    cx, cy : float
        Centre of the tiling.
    radius : float
        Outer radius of the initial decagonal wheel.
    subdivisions : int
        Number of subdivision iterations to perform.
    progress : ProgressReporter or None
        Optional progress reporter updated once per subdivision level.

    Returns
    -------
    list[tuple]
        Each element is ``(type, A, B, C)`` with triangle type (0 or 1) and
        vertex coordinates as ``(x, y)`` tuples.
    """
    triangles = create_initial_wheel(cx, cy, radius)
    for level in range(subdivisions):
        triangles = subdivide_triangles(triangles)
        if progress is not None:
            progress.update(level + 1)
    return triangles


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_aperiodic(parent, ns, target_x, target_y,
                          col_cx, anno_y, scale=1, theme=None):
    """Annotation: the tiling never repeats."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Aperiodic Order", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "A Penrose tiling fills the plane",
        "completely, yet no finite patch can",
        "be shifted to overlap itself. It has",
        "long-range order without periodicity \u2014",
        "an \u2018almost crystal\u2019 that defies the",
        "classical notion of a repeating lattice.",
    ], scale, theme=theme)
    return g


def _annotation_symmetry(parent, ns, target_x, target_y,
                         col_cx, anno_y, scale=1, theme=None):
    """Annotation: five-fold rotational symmetry."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Five-Fold Symmetry", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Classical crystallography proved that",
        "periodic tilings cannot have five-fold",
        "symmetry. Penrose tilings bypass this",
        "restriction: they are not periodic, yet",
        "every local patch appears with equal",
        "frequency in all five orientations.",
    ], scale, theme=theme)
    return g


def _annotation_golden_ratio(parent, ns, target_x, target_y,
                             col_cx, anno_y, scale=1, theme=None):
    """Annotation: the golden ratio φ pervades the construction."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "The Golden Ratio", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "The golden ratio \u03c6 = (1+\u221a5)/2 governs",
        "every aspect of the tiling: triangle",
        "edge ratios, subdivision positions,",
        "and the relative frequency of thick",
        "to thin tiles, which converges to \u03c6",
        "as the pattern grows without bound.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_how_it_works(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the subdivision / inflation construction method."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "How It Works",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Begin with a ring of ten triangles",
        "around a central point. Each step",
        "subdivides every triangle using the",
        "golden ratio to place new vertices.",
        "Thin triangles split into two; thick",
        "into three. After several iterations",
        "the pattern converges to the infinite",
        "Penrose tiling with perfect precision.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_quasicrystals(parent, ns, col_cx, anno_y, scale=1):
    """Panel: quasicrystals and the 2011 Nobel Prize."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Quasicrystals",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "In 1982, Dan Shechtman discovered an",
        "aluminium alloy whose diffraction",
        "showed forbidden five-fold symmetry \u2014",
        "a real material with Penrose-like order.",
        "Initially ridiculed, his work earned the",
        "2011 Nobel Prize in Chemistry and",
        "overturned the classical definition of",
        "what it means to be a crystal.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_einstein(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the Einstein problem and the 2023 Hat tile."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Einstein Problem",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Can a single shape tile the plane",
        "aperiodically? For decades this was",
        "an open question. In 2023, David",
        "Smith discovered the \u2018Hat\u2019 \u2014 a",
        "simple 13-sided polygon that tiles",
        "the plane only non-periodically.",
        "The find electrified mathematics and",
        "settled the \u2018einstein\u2019 problem at last.",
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

def generate_poster(subdivisions=5, width_mm=BASE_WIDTH_MM,
                    height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None,
                    verbose=True):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    subdivisions : int
        Number of Robinson-triangle subdivision steps (default: 5).
    width_mm, height_mm : float
        Poster dimensions in millimetres (default: A2).
    designed_by, designed_for : str or None
        Optional credit lines.
    theme : str or None
        Colour theme name.

    Returns
    -------
    xml.etree.ElementTree.Element
        The root ``<svg>`` element.
    """
    t = get_theme(theme)

    sc = build_poster_scaffold(
        title="Penrose Tiling",
        subtitle="Infinite patterns that never repeat",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    avail_w, avail_h = ca["avail_w"], ca["avail_h"]

    # --- Column centres ---
    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # --- Generate the tiling ---
    center_x = width_mm / 2
    center_y = min_top + avail_h / 2
    radius = min(avail_w, avail_h) / 2 * 0.95

    _pp = ProgressReporter(subdivisions, "Penrose: subdivisions") if verbose else None
    triangles = generate_penrose_tiling(center_x, center_y, radius,
                                        subdivisions, progress=_pp)
    if _pp:
        _pp.done()

    # --- Render triangles ---
    tiling_group = _group(svg, ns, id="penrose-tiling")

    thin_color = t["content_primary"]
    thick_color = t["content_secondary"]
    stroke_color = t.get("border_color", "#1C1C1C")

    for tri_type, a, b, c in triangles:
        fill = thin_color if tri_type == THIN else thick_color
        _polygon(tiling_group, ns, [a, b, c],
                 fill=fill, opacity="0.75",
                 stroke=stroke_color,
                 **{"stroke-width": str(round(0.15 * w_scale, 3)),
                    "stroke-opacity": "0.3"})

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    # Arrow targets: spread across the lower portion of the tiling
    target_y = center_y + radius * 0.25

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_aperiodic, col1_cx, target_y),
            (_annotation_symmetry, col2_cx, target_y),
            (_annotation_golden_ratio, col3_cx, target_y),
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

    _panel_how_it_works(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_quasicrystals(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_einstein(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Roger Penrose\u2019s aperiodic tiling, first published in 1974, "
            "bridging geometry, physics, and art."
        ),
        secondary_line=(
            f"Generated with {subdivisions} subdivision"
            f"{'s' if subdivisions != 1 else ''}  "
            f"\u00b7  {len(triangles):,} triangles  "
            f"\u00b7  \u03c6 = (1+\u221a5)/2"
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
        description="Generate an annotated Penrose Tiling poster.",
    )
    parser.add_argument(
        "--subdivisions", type=int, default=5,
        help="Number of Robinson-triangle subdivision steps (default: 5).",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        subdivisions=args.subdivisions,
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
        filename_prefix="penrose_tiling_poster",
        poster_label=(
            f"Penrose Tiling poster "
            f"(subdivisions={args.subdivisions})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
