#!/usr/bin/env python3
"""
Double Pendulum Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of the
Double Pendulum — a simple mechanical system that exhibits deterministic
chaos, where tiny differences in starting angle lead to wildly different
trajectories.

Usage:
    python double_pendulum_poster.py [OPTIONS]

Options:
    --steps N            Integration steps (default: 10000)
    --output FILE        Output filename (default: double_pendulum_poster.svg)
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
    get_theme,
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Double pendulum helpers
# ---------------------------------------------------------------------------

def double_pendulum_derivatives(state, L1=1.0, L2=1.0, m1=1.0, m2=1.0,
                                g=9.81):
    """Return (dtheta1/dt, domega1/dt, dtheta2/dt, domega2/dt).

    Parameters
    ----------
    state : tuple
        Current state (theta1, omega1, theta2, omega2).
    L1, L2 : float
        Lengths of the first and second pendulum arms.
    m1, m2 : float
        Masses of the first and second bobs.
    g : float
        Gravitational acceleration.

    Returns
    -------
    tuple[float, float, float, float]
        Time derivatives of (theta1, omega1, theta2, omega2).
    """
    theta1, omega1, theta2, omega2 = state
    delta = theta1 - theta2
    sin_d = math.sin(delta)
    cos_d = math.cos(delta)
    denom = 2 * m1 + m2 - m2 * math.cos(2 * delta)

    dtheta1 = omega1
    dtheta2 = omega2

    domega1 = (
        -g * (2 * m1 + m2) * math.sin(theta1)
        - m2 * g * math.sin(theta1 - 2 * theta2)
        - 2 * sin_d * m2
        * (omega2 ** 2 * L2 + omega1 ** 2 * L1 * cos_d)
    ) / (L1 * denom)

    domega2 = (
        2 * sin_d
        * (omega1 ** 2 * L1 * (m1 + m2)
           + g * (m1 + m2) * math.cos(theta1)
           + omega2 ** 2 * L2 * m2 * cos_d)
    ) / (L2 * denom)

    return (dtheta1, domega1, dtheta2, domega2)


def integrate_double_pendulum(initial_state, steps=10000, dt=0.001,
                              L1=1.0, L2=1.0, m1=1.0, m2=1.0, g=9.81):
    """Integrate the double pendulum ODEs using 4th-order Runge-Kutta.

    Parameters
    ----------
    initial_state : tuple
        Starting state (theta1, omega1, theta2, omega2).
    steps : int
        Number of integration steps.
    dt : float
        Time-step size.
    L1, L2 : float
        Pendulum arm lengths.
    m1, m2 : float
        Bob masses.
    g : float
        Gravitational acceleration.

    Returns
    -------
    list[tuple[float, float, float, float]]
        Trajectory as a sequence of (theta1, omega1, theta2, omega2) states.
    """
    trajectory = [initial_state]
    state = initial_state
    for _ in range(steps):
        s = state
        k1 = double_pendulum_derivatives(s, L1, L2, m1, m2, g)
        k2 = double_pendulum_derivatives(
            tuple(s[i] + dt / 2 * k1[i] for i in range(4)),
            L1, L2, m1, m2, g,
        )
        k3 = double_pendulum_derivatives(
            tuple(s[i] + dt / 2 * k2[i] for i in range(4)),
            L1, L2, m1, m2, g,
        )
        k4 = double_pendulum_derivatives(
            tuple(s[i] + dt * k3[i] for i in range(4)),
            L1, L2, m1, m2, g,
        )
        state = tuple(
            s[i] + (dt / 6) * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
            for i in range(4)
        )
        trajectory.append(state)
    return trajectory


def pendulum_tip_positions(trajectory, L1=1.0, L2=1.0):
    """Convert a trajectory to (x2, y2) positions of the second bob tip.

    Parameters
    ----------
    trajectory : list[tuple]
        Sequence of (theta1, omega1, theta2, omega2) states.
    L1, L2 : float
        Pendulum arm lengths.

    Returns
    -------
    list[tuple[float, float]]
        Cartesian (x, y) positions of the second pendulum bob.
    """
    positions = []
    for theta1, _omega1, theta2, _omega2 in trajectory:
        x1 = L1 * math.sin(theta1)
        y1 = -L1 * math.cos(theta1)
        x2 = x1 + L2 * math.sin(theta2)
        y2 = y1 - L2 * math.cos(theta2)
        positions.append((x2, y2))
    return positions


# ---------------------------------------------------------------------------
# Poster-specific colours
# ---------------------------------------------------------------------------

TRAJECTORY_COLOR_1 = "#1C1C1C"  # near-black ink
TRAJECTORY_COLOR_2 = "#8B0000"  # accent red
TRAJECTORY_COLOR_3 = "#2E5090"  # blue


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_sensitive_dependence(parent, ns, target_x, target_y,
                                     col_cx, anno_y, scale=1, theme=None):
    """Annotation: sensitive dependence on initial conditions."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Sensitive Dependence", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Three pendulums start almost",
        "identically \u2014 angles differ by a",
        "hundred-thousandth of a radian.",
        "Within seconds the trajectories",
        "diverge completely. This is the",
        "butterfly effect in action.",
    ], scale, theme=theme)
    return g


def _annotation_phase_space(parent, ns, target_x, target_y,
                            col_cx, anno_y, scale=1, theme=None):
    """Annotation: the 4-D phase space of the double pendulum."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Four-Dimensional Phase Space", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "The state of the double pendulum",
        "lives in a 4-D space: two angles",
        "and two angular velocities. The",
        "trace you see is a projection of",
        "this high-dimensional orbit onto",
        "the physical plane.",
    ], scale, theme=theme)
    return g


def _annotation_energy_conservation(parent, ns, target_x, target_y,
                                    col_cx, anno_y, scale=1, theme=None):
    """Annotation: energy conservation amid chaotic motion."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Energy Conservation", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Total energy \u2014 kinetic plus",
        "potential \u2014 is exactly conserved.",
        "The system is Hamiltonian: no",
        "friction, no dissipation. Yet the",
        "motion is chaotic, filling a",
        "bounded region unpredictably.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_equations(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the double pendulum equations of motion."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Equations",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Two coupled second-order ODEs",
        "govern the motion of the double",
        "pendulum \u2014 far too complex for",
        "a closed-form solution:",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    eq_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(3.5 * scale, 2)),
        "font-style": "italic",
        "text-anchor": "middle",
    }
    eq_y = anno_y + 34 * scale
    _text(g, ns, col_cx, eq_y,
          "d\u03b81/dt = \u03c91", **eq_style)
    _text(g, ns, col_cx, eq_y + 5 * scale,
          "d\u03b82/dt = \u03c92", **eq_style)
    _text(g, ns, col_cx, eq_y + 12 * scale,
          "d\u03c91/dt = f(\u03b81, \u03b82, \u03c91, \u03c92)", **eq_style)
    _text(g, ns, col_cx, eq_y + 17 * scale,
          "d\u03c92/dt = g(\u03b81, \u03b82, \u03c91, \u03c92)", **eq_style)

    return g


def _panel_chaos_vs_random(parent, ns, col_cx, anno_y, scale=1):
    """Panel: distinction between chaotic and random."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Chaotic \u2260 Random",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The double pendulum obeys Newton\u2019s",
        "laws exactly \u2014 nothing is random.",
        "Given perfect initial conditions,",
        "the future is fully determined.",
        "But in practice, immeasurably tiny",
        "errors grow exponentially, making",
        "long-term prediction impossible.",
        "This is deterministic chaos.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_physical_systems(parent, ns, col_cx, anno_y, scale=1):
    """Panel: real-world examples of chaotic systems."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Chaos in the Real World",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The same mathematics governs many",
        "systems: weather patterns, the",
        "three-body problem in astronomy,",
        "turbulent fluid flow, population",
        "dynamics, and even the beating of",
        "the human heart. Wherever simple",
        "rules interact nonlinearly, chaos",
        "can emerge.",
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

def generate_poster(steps=10000, width_mm=BASE_WIDTH_MM,
                    height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    steps : int
        Number of RK4 integration steps per trajectory.
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
    traj_color_1 = t["content_primary"]
    traj_color_2 = t["accent_color"]
    traj_color_3 = t["content_secondary"]

    sc = build_poster_scaffold(
        title="The Double Pendulum",
        subtitle="Deterministic chaos in a simple mechanism",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Compute three trajectories with slightly different initial angles ---
    dt = 0.005
    theta1_base = math.pi / 2
    initial_states = [
        (theta1_base, 0.0, theta1_base, 0.0),
        (theta1_base + 1e-5, 0.0, theta1_base, 0.0),
        (theta1_base + 2e-5, 0.0, theta1_base, 0.0),
    ]

    trajectories = [
        integrate_double_pendulum(s, steps=steps, dt=dt)
        for s in initial_states
    ]
    tip_sets = [pendulum_tip_positions(t) for t in trajectories]

    # --- Fit the trajectories into the poster content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    margin, avail_w, avail_h = ca["margin"], ca["avail_w"], ca["avail_h"]

    all_x = [p[0] for tips in tip_sets for p in tips]
    all_y = [p[1] for tips in tip_sets for p in tips]
    raw_min_x, raw_max_x = min(all_x), max(all_x)
    raw_min_y, raw_max_y = min(all_y), max(all_y)
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

    # Subsample every 3 points to keep SVG size manageable
    subsample = 3
    scaled_sets = [
        [_transform(px, py) for px, py in tips[::subsample]]
        for tips in tip_sets
    ]

    # --- Draw trajectory traces ---
    traj_group = _group(svg, ns, id="trajectories")

    colors = [traj_color_1, traj_color_2, traj_color_3]
    opacities = ["0.4", "0.35", "0.35"]
    stroke_w = str(round(0.12 * w_scale, 3))

    for scaled, color, opacity in zip(scaled_sets, colors, opacities):
        _polyline(traj_group, ns, scaled,
                  stroke=color, opacity=opacity,
                  **{"stroke-width": stroke_w,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Arrow targets on the trajectories
    mid_idx = len(scaled_sets[0]) // 3
    quarter_idx = len(scaled_sets[0]) // 4
    third_quarter_idx = 3 * len(scaled_sets[0]) // 4

    sd_target = scaled_sets[0][mid_idx]
    ps_target = scaled_sets[1][quarter_idx] if len(scaled_sets[1]) > quarter_idx else (center_x, center_y)
    ec_target = scaled_sets[2][third_quarter_idx] if len(scaled_sets[2]) > third_quarter_idx else (center_x, center_y)

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_sensitive_dependence, sd_target[0], sd_target[1]),
            (_annotation_phase_space, ps_target[0], ps_target[1]),
            (_annotation_energy_conservation, ec_target[0], ec_target[1]),
        ],
        w_scale,
        theme=theme,
    )

    # --- Second row: educational connections ---
    edu_group = _group(svg, ns, id="educational")

    row2_sep_y = anno_y + 55 * w_scale
    draw_row_separator(edu_group, ns, width_mm, row2_sep_y, w_scale,
                       opacity="0.35", theme=theme)

    row2_y = row2_sep_y + 12 * w_scale

    _panel_equations(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_chaos_vs_random(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_physical_systems(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "The double pendulum: one of the simplest systems "
            "to exhibit deterministic chaos."
        ),
        secondary_line=(
            f"Generated with {steps:,} integration steps  "
            f"\u00b7  dt = {dt}  "
            f"\u00b7  \u03b81\u2080 \u2248 \u03c0/2  "
            f"\u00b7  \u0394\u03b8 = 10\u207b\u2075"
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
        description="Generate an annotated Double Pendulum chaos poster.",
    )
    parser.add_argument(
        "--steps", type=int, default=10000,
        help="Integration steps (default: 10000). Higher = more detail.",
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
        filename_prefix="double_pendulum_poster",
        poster_label=f"Double Pendulum poster (steps={args.steps})",
        argv=argv,
    )


if __name__ == "__main__":
    main()
