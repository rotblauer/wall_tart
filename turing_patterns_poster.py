#!/usr/bin/env python3
"""
Turing Patterns Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of
Turing Patterns — the reaction-diffusion systems first described by
Alan Turing in 1952 that explain how biological patterns such as
leopard spots, zebra stripes, and coral structures emerge from
simple chemical interactions.

Usage:
    python turing_patterns_poster.py [OPTIONS]

Options:
    --grid-size N        Grid dimension (default: 60)
    --steps N            Simulation time-steps (default: 3000)
    --output FILE        Output filename (default: turing_patterns_poster.svg)
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
    ProgressReporter,
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Gray-Scott reaction-diffusion helpers
# ---------------------------------------------------------------------------

# Diffusion rates, time-step
DU = 0.16
DV = 0.08
DT = 1.0

# Parameter regimes: (label, feed_rate, kill_rate)
REGIMES = [
    ("Spots",   0.035, 0.065),
    ("Stripes", 0.055, 0.062),
    ("Mazes",   0.029, 0.057),
]


def _make_grid(n, value):
    """Create an n×n grid (list of lists) filled with *value*."""
    return [[value] * n for _ in range(n)]


def _laplacian(grid, i, j, n):
    """Five-point stencil Laplacian for a toroidal grid."""
    center = grid[i][j]
    return (
        grid[(i - 1) % n][j]
        + grid[(i + 1) % n][j]
        + grid[i][(j - 1) % n]
        + grid[i][(j + 1) % n]
        - 4.0 * center
    )


def gray_scott(n, steps, f, k, progress=None):
    """Run a Gray-Scott reaction-diffusion simulation.

    Parameters
    ----------
    n : int
        Grid side length.
    steps : int
        Number of time-steps to simulate.
    f : float
        Feed rate.
    k : float
        Kill rate.
    progress : ProgressReporter or None
        Optional progress reporter updated once per time-step.

    Returns
    -------
    list[list[float]]
        The *v* concentration grid after *steps* iterations.
    """
    u = _make_grid(n, 1.0)
    v = _make_grid(n, 0.0)

    # Seed a square region in the centre with v = 0.25, u = 0.5
    r = max(n // 10, 2)
    mid = n // 2
    for i in range(mid - r, mid + r):
        for j in range(mid - r, mid + r):
            u[i][j] = 0.50
            v[i][j] = 0.25

    for _ in range(steps):
        u_new = _make_grid(n, 0.0)
        v_new = _make_grid(n, 0.0)
        for i in range(n):
            for j in range(n):
                u_val = u[i][j]
                v_val = v[i][j]
                uvv = u_val * v_val * v_val
                lap_u = _laplacian(u, i, j, n)
                lap_v = _laplacian(v, i, j, n)
                u_new[i][j] = u_val + DT * (DU * lap_u - uvv + f * (1.0 - u_val))
                v_new[i][j] = v_val + DT * (DV * lap_v + uvv - (f + k) * v_val)
        u = u_new
        v = v_new
        if progress is not None:
            progress.update()

    return v


# ---------------------------------------------------------------------------
# Colour mapping
# ---------------------------------------------------------------------------

def _hex_to_rgb(h):
    """Convert a hex colour string to (r, g, b) tuple (0–255)."""
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r, g, b):
    """Convert (r, g, b) integers to hex colour string."""
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _lerp_color(c0, c1, t):
    """Linearly interpolate between two hex colours by factor *t* (0–1)."""
    r0, g0, b0 = _hex_to_rgb(c0)
    r1, g1, b1 = _hex_to_rgb(c1)
    r = r0 + (r1 - r0) * t
    g = g0 + (g1 - g0) * t
    b = b0 + (b1 - b0) * t
    return _rgb_to_hex(r, g, b)


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_activator_inhibitor(parent, ns, target_x, target_y,
                                    col_cx, anno_y, scale=1, theme=None):
    """Annotation: the activator-inhibitor mechanism."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Activator\u2013Inhibitor", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Two chemicals interact: one activates",
        "growth while the other inhibits it.",
        "The activator diffuses slowly, while",
        "the inhibitor spreads fast, creating",
        "local peaks surrounded by suppressed",
        "zones \u2014 the seed of every pattern.",
    ], scale, theme=theme)
    return g


def _annotation_symmetry_breaking(parent, ns, target_x, target_y,
                                  col_cx, anno_y, scale=1, theme=None):
    """Annotation: spontaneous symmetry breaking."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Symmetry Breaking", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Starting from near-uniform conditions,",
        "tiny perturbations are amplified by the",
        "reaction-diffusion feedback loop. The",
        "system spontaneously organises into",
        "spots, stripes, or labyrinths \u2014 order",
        "emerging from apparent uniformity.",
    ], scale, theme=theme)
    return g


def _annotation_turings_insight(parent, ns, target_x, target_y,
                                col_cx, anno_y, scale=1, theme=None):
    """Annotation: Turing's morphogenesis insight."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Turing\u2019s Insight", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "In 1952, Alan Turing proposed that",
        "chemical substances (morphogens)",
        "reacting and diffusing through tissue",
        "could explain biological pattern",
        "formation \u2014 from a leopard\u2019s spots",
        "to the arrangement of leaf buds.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_gray_scott_model(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the Gray-Scott model equations."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Gray\u2013Scott Model",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "\u2202u/\u2202t = D_u \u2207\u00b2u \u2212 uv\u00b2 + f(1\u2212u)",
        "\u2202v/\u2202t = D_v \u2207\u00b2v + uv\u00b2 \u2212 (f+k)v",
        "",
        "Two coupled PDEs govern species u and",
        "v.  D_u and D_v set diffusion rates; f is",
        "the feed rate replenishing u; k is the",
        "kill rate removing v.  Varying f and k",
        "selects spots, stripes, or mazes.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_natures_patterns(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Turing patterns in nature."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Nature\u2019s Patterns",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Turing patterns appear throughout the",
        "living world: the rosettes on a leopard,",
        "stripes on a zebra or angelfish, the",
        "branching of coral, and the pigment",
        "whorls on seashells. Even the spacing",
        "of hair follicles and feather buds",
        "follows the same activator\u2013inhibitor",
        "logic Turing described in 1952.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_chemistry_to_ecology(parent, ns, col_cx, anno_y, scale=1):
    """Panel: from chemistry to ecology."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "From Chemistry to Ecology",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Reaction\u2013diffusion models bridge",
        "biochemistry, ecology, and mathematics.",
        "The same equations that model chemical",
        "morphogens explain vegetation bands in",
        "arid landscapes, predator\u2013prey waves,",
        "and cardiac electrical patterns. This",
        "universality makes Turing\u2019s framework",
        "one of science\u2019s most elegant ideas.",
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

def generate_poster(grid_size=60, steps=3000,
                    width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None,
                    verbose=True):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    grid_size : int
        Side length of the simulation grid (default: 60).
    steps : int
        Number of simulation time-steps (default: 3000).
    width_mm, height_mm : float
        Poster dimensions in millimetres (default: A2).
    designed_by, designed_for : str or None
        Optional credit lines.

    Returns
    -------
    xml.etree.ElementTree.Element
        The root ``<svg>`` element.
    """
    t = get_theme(theme)

    sc = build_poster_scaffold(
        title="Reaction\u2013Diffusion \u00b7 Turing Patterns",
        subtitle="How leopards get their spots",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    avail_h = ca["avail_h"]

    # --- Column centres ---
    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Panel width ~ 28% of poster width
    panel_w = width_mm * 0.28

    # Reserve space for labels below the grid
    label_gap = 14 * h_scale

    # Cell size to fit panel
    max_cell_w = panel_w / grid_size
    max_cell_h = (avail_h - label_gap) / grid_size
    cell_sz = min(max_cell_w, max_cell_h)

    grid_px = grid_size * cell_sz

    # Colour end-points: map v concentration → theme colours
    bg_color = t["bg_color"]
    ink_colors = [t["content_primary"], t["accent_color"], t["content_secondary"]]

    # --- Run simulations and draw ---
    patterns_group = _group(svg, ns, id="turing-patterns")

    col_centers = [col1_cx, col2_cx, col3_cx]

    for idx, (label, f_rate, k_rate) in enumerate(REGIMES):
        _p = ProgressReporter(steps, f"Turing: {label[:18]}") if verbose else None
        v_grid = gray_scott(grid_size, steps, f_rate, k_rate, progress=_p)
        if _p:
            _p.done()
        ink = ink_colors[idx]
        col_cx = col_centers[idx]

        # Find min/max of v for normalisation
        v_min = v_grid[0][0]
        v_max = v_grid[0][0]
        for row in v_grid:
            for val in row:
                if val < v_min:
                    v_min = val
                if val > v_max:
                    v_max = val
        v_range = v_max - v_min if v_max > v_min else 1.0

        gx = col_cx - grid_px / 2
        gy = min_top + (avail_h - label_gap - grid_px) / 2

        panel_group = _group(patterns_group, ns,
                             id=f"panel-{label.lower()}")

        for ri, row in enumerate(v_grid):
            for ci, val in enumerate(row):
                norm = (val - v_min) / v_range
                color = _lerp_color(bg_color, ink, norm)
                _rect(panel_group, ns,
                      round(gx + ci * cell_sz, 2),
                      round(gy + ri * cell_sz, 2),
                      round(cell_sz, 2),
                      round(cell_sz, 2),
                      fill=color)

        # Label below the grid
        _text(svg, ns, col_cx, gy + grid_px + 6 * h_scale,
              f"{label} (f={f_rate}, k={k_rate})",
              **{
                  "font-family": SERIF,
                  "font-size": str(round(4.2 * w_scale, 2)),
                  "fill": ACCENT_COLOR,
                  "text-anchor": "middle",
              })

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    target_y = min_top + (avail_h - label_gap - grid_px) / 2 + grid_px * 0.3

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_activator_inhibitor, col1_cx, target_y),
            (_annotation_symmetry_breaking, col2_cx, target_y),
            (_annotation_turings_insight, col3_cx, target_y),
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

    _panel_gray_scott_model(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_natures_patterns(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_chemistry_to_ecology(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Alan Turing\u2019s 1952 paper \u201cThe Chemical Basis of "
            "Morphogenesis\u201d — the origin of mathematical biology."
        ),
        secondary_line=(
            f"Generated with grid {grid_size}\u00d7{grid_size}  "
            f"\u00b7  {steps:,} steps  "
            f"\u00b7  Gray\u2013Scott model"
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
        description="Generate an annotated Turing Patterns poster.",
    )
    parser.add_argument(
        "--grid-size", type=int, default=60, dest="grid_size",
        help="Grid dimension (default: 60).",
    )
    parser.add_argument(
        "--steps", type=int, default=3000,
        help="Number of simulation time-steps (default: 3000).",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        grid_size=args.grid_size,
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
        filename_prefix="turing_patterns_poster",
        poster_label=(
            f"Turing Patterns poster "
            f"(grid_size={args.grid_size}, steps={args.steps})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
