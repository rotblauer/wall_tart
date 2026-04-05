#!/usr/bin/env python3
"""
Harmonograph & Lissajous Curves Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of
Harmonograph and Lissajous curves — the beautiful parametric figures
produced by combining sinusoidal oscillators, intimately linked to
musical intervals and the physics of pendulum motion.

Usage:
    python harmonograph_poster.py [OPTIONS]

Options:
    --steps N            Number of simulation steps (default: 10000)
    --output FILE        Output filename (default: harmonograph_poster.svg)
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
    _multiline_text,
    _polyline,
    _rect,
    _text,
    _line,
    add_common_poster_args,
    build_poster_scaffold,
    content_area,
    draw_annotation_body,
    draw_annotation_header,
    draw_annotation_row,
    draw_row_separator,
    finalize_poster,
    get_theme,
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Harmonograph / Lissajous simulation helpers
# ---------------------------------------------------------------------------

def harmonograph(steps, dt, params):
    """Simulate a harmonograph curve from damped sinusoidal oscillators.

    The curve is defined by:
        x(t) = A1*sin(f1*t + p1)*exp(-d1*t) + A2*sin(f2*t + p2)*exp(-d2*t)
        y(t) = A3*sin(f3*t + p3)*exp(-d3*t) + A4*sin(f4*t + p4)*exp(-d4*t)

    Parameters
    ----------
    steps : int
        Number of sample points to generate.
    dt : float
        Time increment between samples.
    params : list of tuple
        Four (amplitude, frequency, phase, decay) tuples — the first two
        control x(t) and the second two control y(t).

    Returns
    -------
    list[tuple[float, float]]
        Sequence of (x, y) points tracing the curve.
    """
    (a1, f1, p1, d1), (a2, f2, p2, d2) = params[0], params[1]
    (a3, f3, p3, d3), (a4, f4, p4, d4) = params[2], params[3]

    points = []
    for i in range(steps):
        t = i * dt
        x = (a1 * math.sin(f1 * t + p1) * math.exp(-d1 * t)
             + a2 * math.sin(f2 * t + p2) * math.exp(-d2 * t))
        y = (a3 * math.sin(f3 * t + p3) * math.exp(-d3 * t)
             + a4 * math.sin(f4 * t + p4) * math.exp(-d4 * t))
        points.append((x, y))
    return points


def lissajous(steps, dt, a, b, delta):
    """Generate an undamped Lissajous curve.

    The curve is defined by:
        x(t) = sin(a*t + delta)
        y(t) = sin(b*t)

    Parameters
    ----------
    steps : int
        Number of sample points to generate.
    dt : float
        Time increment between samples.
    a, b : float
        Frequency parameters for x and y axes.
    delta : float
        Phase offset for x.

    Returns
    -------
    list[tuple[float, float]]
        Sequence of (x, y) points tracing the curve.
    """
    points = []
    for i in range(steps):
        t = i * dt
        x = math.sin(a * t + delta)
        y = math.sin(b * t)
        points.append((x, y))
    return points


# ---------------------------------------------------------------------------
# Scaling helper
# ---------------------------------------------------------------------------

def _scale_points(points, cx, cy, half_w, half_h):
    """Scale normalised (−1…+1) points to fit a bounding box.

    Parameters
    ----------
    points : list[tuple[float, float]]
        Raw curve points (expected range roughly −1 to +1 on each axis,
        but will be auto-scaled to the actual min/max).
    cx, cy : float
        Centre of the target bounding box.
    half_w, half_h : float
        Half-width and half-height of the target bounding box.

    Returns
    -------
    list[tuple[float, float]]
        Scaled points centred on (cx, cy).
    """
    if not points:
        return points
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = x_max - x_min or 1.0
    y_range = y_max - y_min or 1.0
    sx = 2.0 * half_w / x_range
    sy = 2.0 * half_h / y_range
    scale = min(sx, sy)
    x_mid = (x_min + x_max) / 2.0
    y_mid = (y_min + y_max) / 2.0
    return [
        (cx + (x - x_mid) * scale, cy + (y - y_mid) * scale)
        for x, y in points
    ]


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_damped(parent, ns, target_x, target_y,
                       col_cx, anno_y, scale=1, theme=None):
    """Annotation: damped oscillation in harmonographs."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Damped Oscillation", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "A harmonograph combines pendulums",
        "that slowly lose energy to friction.",
        "Each swing is a little smaller than",
        "the last, so the traced curve spirals",
        "inward over time — an exponential",
        "decay that gives the art its depth.",
    ], scale, theme=theme)
    return g


def _annotation_ratios(parent, ns, target_x, target_y,
                       col_cx, anno_y, scale=1, theme=None):
    """Annotation: musical ratios and Lissajous shapes."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Musical Ratios", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Frequency ratios like 2:3 (a perfect",
        "fifth) and 3:4 (a perfect fourth)",
        "create instantly recognisable shapes.",
        "Each musical interval has its own",
        "Lissajous signature — a visual",
        "fingerprint of harmony.",
    ], scale, theme=theme)
    return g


def _annotation_sensitive(parent, ns, target_x, target_y,
                          col_cx, anno_y, scale=1, theme=None):
    """Annotation: sensitivity to parameter changes."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Sensitive to Parameters", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Tiny frequency changes produce",
        "dramatically different patterns. A",
        "ratio of 2.00:3.00 gives a clean",
        "curve; 2.01:3.00 fills the plane",
        "with a dense, swirling figure that",
        "never quite repeats itself.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_equations(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the harmonograph equations."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Equations",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "x(t) = \u2211 A\u1d62 sin(f\u1d62t + \u03c6\u1d62) e^(\u2212d\u1d62t)",
        "y(t) follows the same form. Each",
        "term is a damped sinusoid: amplitude",
        "A, frequency f, phase \u03c6, and decay d.",
        "Two terms per axis give parametric",
        "motion in 2D. When decay is zero",
        "the result is a pure Lissajous",
        "curve that repeats perfectly.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_victorian(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the Victorian science-art tradition."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Victorian Science Art",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "In the 1840s, Hugh Blackburn and",
        "others built harmonograph machines:",
        "coupled pendulums that swung a pen",
        "over paper. The resulting drawings",
        "were prized as both scientific data",
        "and decorative art. These devices",
        "made the invisible mathematics of",
        "vibration tangible and beautiful.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_oscilloscopes(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Lissajous patterns on oscilloscopes."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Oscilloscopes & Signals",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Feed one sine wave to the X input",
        "of an oscilloscope and another to Y:",
        "a Lissajous pattern appears. Engineers",
        "once used these shapes to measure",
        "unknown frequencies by comparing",
        "them to a known reference. The same",
        "principle underlies laser shows and",
        "modern signal analysis displays.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


# ---------------------------------------------------------------------------
# Lissajous background grid parameters
# ---------------------------------------------------------------------------

LISSAJOUS_GRID = [
    # (a, b, delta, label)  — top row
    (1, 1, math.pi / 4, "1:1"),
    (1, 2, 0, "1:2"),
    (2, 3, 0, "2:3"),
    # bottom row
    (3, 4, 0, "3:4"),
    (3, 5, 0, "3:5"),
    (4, 5, 0, "4:5"),
]

# Default harmonograph parameters: produce an intricate spiralling pattern
DEFAULT_HARMONOGRAPH_PARAMS = [
    (1.0, 2.01, 0, 0.002),
    (1.0, 3.0, math.pi / 2, 0.003),
    (1.0, 3.01, 0, 0.002),
    (1.0, 2.0, math.pi / 4, 0.003),
]


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

def generate_poster(steps=10000, width_mm=BASE_WIDTH_MM,
                    height_mm=BASE_HEIGHT_MM, designed_by=None,
                    designed_for=None, theme=None):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    steps : int
        Number of sample points for the harmonograph curve (default: 10000).
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
        title="Harmonograph & Lissajous Curves",
        subtitle="The geometry of musical intervals",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    avail_w = ca["avail_w"]
    avail_h = ca["avail_h"]

    # --- Column centres ---
    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    content_group = _group(svg, ns, id="harmonograph")

    # ------------------------------------------------------------------
    # Background: 6 small Lissajous patterns in a 3×2 grid
    # ------------------------------------------------------------------
    liss_steps = 2000
    liss_dt = 2 * math.pi / 500

    cols_3 = [col1_cx, col2_cx, col3_cx]
    row_h = avail_h * 0.45
    top_row_cy = min_top + row_h * 0.5
    bot_row_cy = min_top + row_h * 1.5

    cell_half = min(avail_w / 6 * 0.4, row_h * 0.4)

    for idx, (a, b, delta, label) in enumerate(LISSAJOUS_GRID):
        col_idx = idx % 3
        row_idx = idx // 3
        cx = cols_3[col_idx]
        cy = top_row_cy if row_idx == 0 else bot_row_cy

        pts = lissajous(liss_steps, liss_dt, a, b, delta)
        scaled = _scale_points(pts, cx, cy, cell_half, cell_half)

        _polyline(content_group, ns, scaled,
                  stroke=t["content_secondary"], opacity="0.18",
                  **{"stroke-width": str(round(0.4 * w_scale, 3)),
                     "stroke-linejoin": "round"})

        _text(content_group, ns, cx, cy + cell_half + 6 * h_scale,
              label,
              **{"font-family": SERIF,
                 "font-size": str(round(4 * w_scale, 2)),
                 "fill": t["content_secondary"],
                 "opacity": "0.35",
                 "text-anchor": "middle"})

    # ------------------------------------------------------------------
    # Foreground: large elaborate harmonograph curve
    # ------------------------------------------------------------------
    dt = 0.01
    harm_pts = harmonograph(steps, dt, DEFAULT_HARMONOGRAPH_PARAMS)

    centre_cx = width_mm / 2.0
    centre_cy = min_top + avail_h / 2.0
    harm_half = min(avail_w, avail_h) * 0.42

    scaled_harm = _scale_points(harm_pts, centre_cx, centre_cy,
                                harm_half, harm_half)

    _polyline(content_group, ns, scaled_harm,
              stroke=t["content_primary"], opacity="0.85",
              **{"stroke-width": str(round(0.35 * w_scale, 3)),
                 "stroke-linejoin": "round"})

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    target_y = min_top + avail_h * 0.35

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_damped, col1_cx, target_y),
            (_annotation_ratios, col2_cx, target_y),
            (_annotation_sensitive, col3_cx, target_y),
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

    _panel_equations(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_victorian(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_oscilloscopes(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Harmonograph art: where mathematics, music, "
            "and visual beauty converge."
        ),
        secondary_line=(
            f"Generated with {steps} steps  "
            f"\u00b7  dt = {dt}  "
            f"\u00b7  4-oscillator harmonograph"
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
        description="Generate an annotated Harmonograph & Lissajous Curves poster.",
    )
    parser.add_argument(
        "--steps", type=int, default=10000,
        help="Number of simulation steps (default: 10000).",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        steps=args.steps,
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
        filename_prefix="harmonograph_poster",
        poster_label=(
            f"Harmonograph poster "
            f"(steps={args.steps})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
