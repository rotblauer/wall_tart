#!/usr/bin/env python3
"""
Lorenz Attractor Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of the
Lorenz Attractor — the iconic butterfly-shaped strange attractor that
launched the modern study of deterministic chaos.

Usage:
    python lorenz_poster.py [OPTIONS]

Options:
    --steps N            Integration steps (default: 200000)
    --output FILE        Output filename (default: lorenz_poster.svg)
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
    SERIF,
    _circle,
    _group,
    _line,
    _multiline_text,
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
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Lorenz system helpers
# ---------------------------------------------------------------------------

def lorenz_derivatives(state, sigma=10.0, rho=28.0, beta=8.0 / 3.0):
    """Return (dx/dt, dy/dt, dz/dt) for the Lorenz system.

    The Lorenz equations are:
        dx/dt = σ(y − x)
        dy/dt = x(ρ − z) − y
        dz/dt = xy − βz
    """
    x, y, z = state
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    return (dx, dy, dz)


def rk4_step(state, dt, sigma=10.0, rho=28.0, beta=8.0 / 3.0):
    """Advance *state* by one Runge-Kutta 4th-order step of size *dt*."""
    x, y, z = state

    k1 = lorenz_derivatives((x, y, z), sigma, rho, beta)
    k2 = lorenz_derivatives(
        (x + dt / 2 * k1[0], y + dt / 2 * k1[1], z + dt / 2 * k1[2]),
        sigma, rho, beta,
    )
    k3 = lorenz_derivatives(
        (x + dt / 2 * k2[0], y + dt / 2 * k2[1], z + dt / 2 * k2[2]),
        sigma, rho, beta,
    )
    k4 = lorenz_derivatives(
        (x + dt * k3[0], y + dt * k3[1], z + dt * k3[2]),
        sigma, rho, beta,
    )

    nx = x + (dt / 6) * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
    ny = y + (dt / 6) * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    nz = z + (dt / 6) * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
    return (nx, ny, nz)


def integrate_lorenz(initial=(1.0, 1.0, 1.0), steps=200000, dt=0.005,
                     sigma=10.0, rho=28.0, beta=8.0 / 3.0):
    """Integrate the Lorenz system and return a list of (x, y, z) tuples.

    Parameters
    ----------
    initial : tuple
        Starting point (x₀, y₀, z₀).
    steps : int
        Number of integration steps.
    dt : float
        Time-step size.
    sigma, rho, beta : float
        Lorenz system parameters (defaults: σ=10, ρ=28, β=8/3).

    Returns
    -------
    list[tuple[float, float, float]]
        Trajectory as a sequence of (x, y, z) points.
    """
    trajectory = [initial]
    state = initial
    for _ in range(steps):
        state = rk4_step(state, dt, sigma, rho, beta)
        trajectory.append(state)
    return trajectory


def project_3d_to_2d(points_3d, angle_x=-0.35, angle_z=0.85):
    """Project 3-D points onto a 2-D plane via rotation.

    Applies a rotation around the X-axis followed by a rotation around
    the Z-axis, then drops the depth coordinate to obtain (px, py).

    Parameters
    ----------
    points_3d : list[tuple[float, float, float]]
        Input 3-D points.
    angle_x : float
        Rotation angle about the X-axis (radians).
    angle_z : float
        Rotation angle about the Z-axis (radians).

    Returns
    -------
    list[tuple[float, float]]
        Projected 2-D points.
    """
    cos_x, sin_x = math.cos(angle_x), math.sin(angle_x)
    cos_z, sin_z = math.cos(angle_z), math.sin(angle_z)

    projected = []
    for x, y, z in points_3d:
        y1 = y * cos_x - z * sin_x
        z1 = y * sin_x + z * cos_x
        x2 = x * cos_z - y1 * sin_z
        y2 = x * sin_z + y1 * cos_z
        projected.append((x2, y2))
    return projected


# ---------------------------------------------------------------------------
# Poster-specific colour
# ---------------------------------------------------------------------------

ATTRACTOR_COLOR = "#1C1C1C"  # near-black ink
DIVERGED_COLOR = "#8B0000"   # red for diverged trajectory


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_butterfly_effect(parent, ns, target_x, target_y,
                                  col_cx, anno_y, scale=1, theme=None):
    """Annotation: sensitive dependence on initial conditions."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "The Butterfly Effect", scale, theme=theme)

    body_style = {**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
                  "text-anchor": "middle"}
    body_y = anno_y + 9 * scale
    lh = 5 * scale

    # First line: render "10" then the exponent "-10" via SVG tspan so that
    # the ASCII minus is used instead of U+207B (SUPERSCRIPT MINUS), which is
    # absent from many PDF-embedded fonts and renders as a missing-glyph square.
    attrib = {"x": str(col_cx), "y": str(body_y)}
    attrib.update(body_style)
    text_el = ET.SubElement(g, f"{{{ns}}}text", attrib=attrib)
    line0_tspan = ET.SubElement(
        text_el, f"{{{ns}}}tspan", attrib={"x": str(col_cx), "dy": "0"}
    )
    line0_tspan.text = "Two trajectories start just 10"
    sup = ET.SubElement(
        line0_tspan,
        f"{{{ns}}}tspan",
        attrib={
            "dy": str(round(-1.5 * scale, 2)),
            "font-size": str(round(2.5 * scale, 2)),
        },
    )
    sup.text = "-10"

    _multiline_text(
        g, ns, col_cx, body_y + lh,
        [
            "apart \u2014 an unimaginably tiny gap.",
            "Yet they diverge wildly: sensitive",
            "dependence on initial conditions",
            "makes long-term prediction impossible.",
        ],
        line_height=lh,
        **body_style,
    )
    return g


def _annotation_two_wings(parent, ns, target_x, target_y,
                           col_cx, anno_y, scale=1, theme=None):
    """Annotation: the two lobes ('wings') of the attractor."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "The Two \u2018Wings\u2019", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "The trajectory orbits two unstable",
        "fixed points, spiralling around one",
        "lobe before switching to the other.",
        "The timing of each switch is",
        "unpredictable \u2014 that\u2019s chaos.",
    ], scale, theme=theme)
    return g


def _annotation_infinite_complexity(parent, ns, target_x, target_y,
                                     col_cx, anno_y, scale=1, theme=None):
    """Annotation: the fractal nature of the strange attractor."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Infinite Complexity", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "The line never intersects itself,",
        "despite being trapped in a bounded",
        "region of space. A cross-section",
        "reveals fractal structure \u2014 infinite",
        "layers, like pages of a closed book.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_equations(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the Lorenz ODEs and their parameter values."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Equations",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Three coupled ordinary differential",
        "equations govern the motion:",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    eq_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(4.0 * scale, 2)),
        "font-style": "italic",
        "text-anchor": "middle",
    }
    eq_y = anno_y + 24 * scale
    _text(g, ns, col_cx, eq_y,
          "dx/dt = \u03c3(y \u2212 x)", **eq_style)
    _text(g, ns, col_cx, eq_y + 6 * scale,
          "dy/dt = x(\u03c1 \u2212 z) \u2212 y", **eq_style)
    _text(g, ns, col_cx, eq_y + 12 * scale,
          "dz/dt = xy \u2212 \u03b2z", **eq_style)

    param_y = eq_y + 21 * scale
    param_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(3.8 * scale, 2)),
        "text-anchor": "middle",
    }
    _text(g, ns, col_cx, param_y,
          "\u03c3 = 10,  \u03c1 = 28,  \u03b2 = 8/3", **param_style)

    return g


def _panel_deterministic_chaos(parent, ns, col_cx, anno_y, scale=1,
                                traj_main=None, traj_diverged=None):
    """Panel: deterministic chaos explanation with mini divergence plot."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Deterministic Chaos",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The rules are perfectly deterministic",
        "\u2014 no randomness whatsoever. Yet the",
        "outcome is practically unpredictable",
        "after a short time horizon.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Mini x-vs-time divergence plot centred at col_cx (plot is 56*scale wide)
    plot_x = col_cx - 28 * scale
    plot_y = anno_y + 34 * scale
    plot_w = 56 * scale
    plot_h = 28 * scale

    _line(g, ns, plot_x, plot_y, plot_x, plot_y + plot_h,
          stroke="#1C1C1C", **{"stroke-width": str(round(0.2 * scale, 3))})
    _line(g, ns, plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h,
          stroke="#1C1C1C", **{"stroke-width": str(round(0.2 * scale, 3))})

    _text(g, ns, plot_x + plot_w / 2, plot_y + plot_h + 5 * scale, "time",
          **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
             "text-anchor": "middle", "font-style": "italic"})
    _text(g, ns, plot_x - 3 * scale, plot_y + plot_h / 2, "x",
          **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
             "text-anchor": "middle", "font-style": "italic"})

    if traj_main and traj_diverged:
        n_plot = min(2000, len(traj_main), len(traj_diverged))
        xs_main = [p[0] for p in traj_main[:n_plot]]
        xs_div = [p[0] for p in traj_diverged[:n_plot]]

        all_xs = xs_main + xs_div
        x_min = min(all_xs)
        x_max = max(all_xs)
        x_range = x_max - x_min if x_max != x_min else 1.0

        def _map_point(i, xval):
            px = plot_x + (i / max(n_plot - 1, 1)) * plot_w
            py = plot_y + plot_h - ((xval - x_min) / x_range) * plot_h
            return (px, py)

        step = max(1, n_plot // 200)
        pts_main = [_map_point(i, xs_main[i])
                    for i in range(0, n_plot, step)]
        pts_div = [_map_point(i, xs_div[i])
                   for i in range(0, n_plot, step)]

        _polyline(g, ns, pts_main,
                  stroke=ATTRACTOR_COLOR, opacity="0.7",
                  **{"stroke-width": str(round(0.25 * scale, 3))})
        _polyline(g, ns, pts_div,
                  stroke=DIVERGED_COLOR, opacity="0.7",
                  **{"stroke-width": str(round(0.25 * scale, 3))})

    return g


def _panel_weather_model(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Lorenz's meteorological origins."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "A Weather Model",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Edward Lorenz was a meteorologist.",
        "In 1963 he simplified atmospheric",
        "convection into just three equations.",
        "The result stunned science: even a",
        "perfect model of the weather cannot",
        "predict it beyond a few days, because",
        "tiny measurement errors grow",
        "exponentially. Long-term weather",
        "forecasting is fundamentally",
        "impossible.",
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

def generate_poster(steps=200000, width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None):
    """Build and return the full poster as an ElementTree SVG root."""
    sc = build_poster_scaffold(
        title="The Lorenz Attractor",
        subtitle="Strange beauty from deterministic chaos",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Compute Lorenz trajectory ---
    initial_main = (1.0, 1.0, 1.0)
    traj_main = integrate_lorenz(initial_main, steps=steps)

    initial_div = (1.0 + 1e-10, 1.0, 1.0)
    traj_div = integrate_lorenz(initial_div, steps=steps)

    proj_main = project_3d_to_2d(traj_main)
    proj_div = project_3d_to_2d(traj_div)

    # --- Fit the attractor into the poster space ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    margin, avail_w, avail_h = ca["margin"], ca["avail_w"], ca["avail_h"]

    all_px = [p[0] for p in proj_main]
    all_py = [p[1] for p in proj_main]
    raw_min_x, raw_max_x = min(all_px), max(all_px)
    raw_min_y, raw_max_y = min(all_py), max(all_py)
    raw_w = raw_max_x - raw_min_x if raw_max_x != raw_min_x else 1.0
    raw_h = raw_max_y - raw_min_y if raw_max_y != raw_min_y else 1.0

    scale_factor = min(avail_w / raw_w, avail_h / raw_h) * 0.92
    center_x = width_mm / 2
    center_y = min_top + avail_h / 2
    raw_cx = (raw_min_x + raw_max_x) / 2
    raw_cy = (raw_min_y + raw_max_y) / 2

    def _transform(px, py):
        return (
            center_x + (px - raw_cx) * scale_factor,
            center_y + (py - raw_cy) * scale_factor,
        )

    scaled_main = [_transform(px, py) for px, py in proj_main]
    scaled_div = [_transform(px, py) for px, py in proj_div]

    # --- Main attractor visualisation ---
    attractor_group = _group(svg, ns, id="attractor")

    stroke_w = str(round(0.12 * w_scale, 3))

    n_segments = 5
    seg_len = len(scaled_main) // n_segments
    for i in range(n_segments):
        start = i * seg_len
        end = start + seg_len + 1 if i < n_segments - 1 else len(scaled_main)
        _polyline(attractor_group, ns, scaled_main[start:end],
                  stroke=ATTRACTOR_COLOR, opacity="0.4",
                  **{"stroke-width": stroke_w,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    diverge_threshold = 1.0
    diverge_start = len(scaled_main) - 1
    for idx in range(len(scaled_main)):
        dx = scaled_main[idx][0] - scaled_div[idx][0]
        dy = scaled_main[idx][1] - scaled_div[idx][1]
        if math.hypot(dx, dy) > diverge_threshold:
            diverge_start = idx
            break

    if diverge_start < len(scaled_div):
        _polyline(attractor_group, ns, scaled_div[diverge_start:],
                  stroke=DIVERGED_COLOR, opacity="0.25",
                  **{"stroke-width": stroke_w,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    vis_ys = [p[1] for p in scaled_main]
    attractor_bottom = max(vis_ys)

    anno_sep_y = attractor_bottom + 10 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale, opacity="0.5",
                       theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Arrow targets on the attractor
    if diverge_start < len(scaled_main):
        be_idx = min(diverge_start + len(scaled_main) // 20,
                     len(scaled_main) - 1)
        be_target_x = scaled_main[be_idx][0]
        be_target_y = scaled_main[be_idx][1]
    else:
        be_target_x = center_x - avail_w * 0.15
        be_target_y = center_y

    vis_xs = [p[0] for p in scaled_main]
    left_idx = vis_xs.index(min(vis_xs))
    wing_target_x = scaled_main[left_idx][0]
    wing_target_y = scaled_main[left_idx][1]

    dense_target_x = center_x
    dense_target_y = center_y + avail_h * 0.15

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_butterfly_effect, be_target_x, be_target_y),
            (_annotation_two_wings, wing_target_x, wing_target_y),
            (_annotation_infinite_complexity, dense_target_x, dense_target_y),
        ],
        w_scale,
        theme=theme,
    )

    # --- Second row: educational connections ---
    edu_group = _group(svg, ns, id="educational")

    row2_sep_y = anno_y + 55 * w_scale
    draw_row_separator(edu_group, ns, width_mm, row2_sep_y, w_scale, opacity="0.35",
                       theme=theme)

    row2_y = row2_sep_y + 12 * w_scale

    _panel_equations(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_deterministic_chaos(edu_group, ns, col2_cx, row2_y, w_scale,
                                traj_main=traj_main, traj_diverged=traj_div)
    _panel_weather_model(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Edward Lorenz discovered this attractor in 1963 "
            "while modelling atmospheric convection."
        ),
        secondary_line=(
            f"Generated with {steps:,} integration steps  "
            f"\u00b7  dt = 0.005  \u00b7  \u03c3 = 10, \u03c1 = 28, \u03b2 = 8/3"
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
        description="Generate an annotated Lorenz Attractor poster.",
    )
    parser.add_argument(
        "--steps", type=int, default=200000,
        help="Integration steps (default: 200000). Higher = more detail.",
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
        filename_prefix="lorenz_poster",
        poster_label=f"Lorenz Attractor poster (steps={args.steps})",
        argv=argv,
    )


if __name__ == "__main__":
    main()
