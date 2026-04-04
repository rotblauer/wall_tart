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
    --format FMT         Output format: svg or pdf (default: svg)
    --width MM           Poster width in mm (default: 420, A2 width)
    --height MM          Poster height in mm (default: 594, A2 height)
    --designed-by TEXT   Designer credit (e.g. 'Alice and Bob')
    --designed-for TEXT  Client / purpose credit (e.g. 'the Science Museum')
"""

import argparse
import math
import sys
import xml.etree.ElementTree as ET


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
        # Rotate about X-axis
        y1 = y * cos_x - z * sin_x
        z1 = y * sin_x + z * cos_x
        # Rotate about Z-axis
        x2 = x * cos_z - y1 * sin_z
        y2 = x * sin_z + y1 * cos_z
        projected.append((x2, y2))
    return projected


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _ns():
    """Register and return the SVG/XLink XML namespaces."""
    ns = "http://www.w3.org/2000/svg"
    xlink = "http://www.w3.org/1999/xlink"
    ET.register_namespace("", ns)
    ET.register_namespace("xlink", xlink)
    return ns, xlink


def _svg_root(width_mm, height_mm):
    ns, _ = _ns()
    svg = ET.Element(
        f"{{{ns}}}svg",
        attrib={
            "version": "1.1",
            "width": f"{width_mm}mm",
            "height": f"{height_mm}mm",
            "viewBox": f"0 0 {width_mm} {height_mm}",
        },
    )
    return svg, ns


def _polygon(parent, ns, points, **extra):
    pts_str = " ".join(f"{x:.4f},{y:.4f}" for x, y in points)
    attrib = {"points": pts_str}
    attrib.update(extra)
    return ET.SubElement(parent, f"{{{ns}}}polygon", attrib=attrib)


def _polyline(parent, ns, points, **extra):
    """Add an SVG <polyline> element from a sequence of (x, y) points."""
    pts_str = " ".join(f"{x:.4f},{y:.4f}" for x, y in points)
    attrib = {"points": pts_str, "fill": "none"}
    attrib.update(extra)
    return ET.SubElement(parent, f"{{{ns}}}polyline", attrib=attrib)


def _text(parent, ns, x, y, content, **extra):
    attrib = {"x": str(x), "y": str(y)}
    attrib.update(extra)
    elem = ET.SubElement(parent, f"{{{ns}}}text", attrib=attrib)
    elem.text = content
    return elem


def _line(parent, ns, x1, y1, x2, y2, **extra):
    attrib = {
        "x1": str(x1), "y1": str(y1),
        "x2": str(x2), "y2": str(y2),
    }
    attrib.update(extra)
    return ET.SubElement(parent, f"{{{ns}}}line", attrib=attrib)


def _rect(parent, ns, x, y, w, h, **extra):
    attrib = {"x": str(x), "y": str(y), "width": str(w), "height": str(h)}
    attrib.update(extra)
    return ET.SubElement(parent, f"{{{ns}}}rect", attrib=attrib)


def _group(parent, ns, **extra):
    return ET.SubElement(parent, f"{{{ns}}}g", attrib=extra)


def _circle(parent, ns, cx, cy, r, **extra):
    attrib = {"cx": str(cx), "cy": str(cy), "r": str(r)}
    attrib.update(extra)
    return ET.SubElement(parent, f"{{{ns}}}circle", attrib=attrib)


def _multiline_text(parent, ns, x, y, lines, line_height, **extra):
    """Add a <text> element with <tspan> children for multi-line text."""
    attrib = {"x": str(x), "y": str(y)}
    attrib.update(extra)
    text_el = ET.SubElement(parent, f"{{{ns}}}text", attrib=attrib)
    for i, line in enumerate(lines):
        tspan = ET.SubElement(
            text_el,
            f"{{{ns}}}tspan",
            attrib={"x": str(x), "dy": str(line_height) if i > 0 else "0"},
        )
        tspan.text = line
    return text_el


# ---------------------------------------------------------------------------
# Arrowhead marker definition
# ---------------------------------------------------------------------------

def _add_arrow_marker(svg, ns):
    defs = ET.SubElement(svg, f"{{{ns}}}defs")
    marker = ET.SubElement(
        defs,
        f"{{{ns}}}marker",
        attrib={
            "id": "arrowhead",
            "markerWidth": "10",
            "markerHeight": "7",
            "refX": "10",
            "refY": "3.5",
            "orient": "auto",
        },
    )
    ET.SubElement(
        marker,
        f"{{{ns}}}polygon",
        attrib={
            "points": "0 0, 10 3.5, 0 7",
            "fill": "#8B0000",
        },
    )
    return defs


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

ANNOTATION_STYLE = {
    "font-family": "Georgia, 'Times New Roman', serif",
    "fill": "#1C1C1C",
}

CALLOUT_LINE_STYLE = {
    "stroke": "#8B0000",
    "stroke-width": "0.5",
    "marker-end": "url(#arrowhead)",
}


def _annotation_butterfly_effect(parent, ns, target_x, target_y,
                                 col_x, anno_y, scale=1):
    """Annotation: sensitive dependence on initial conditions."""
    g = _group(parent, ns)

    # Arrow from above the title up to the attractor target
    arrow_x = col_x + 25 * scale
    arrow_y = anno_y - 8 * scale
    _line(g, ns, arrow_x, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, arrow_x, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_x, anno_y + 2 * scale, "The Butterfly Effect",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    # Body text
    body_style = {**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))}
    body_y = anno_y + 9 * scale
    lh = 5 * scale

    # First line: render "10" then the exponent "-10" via SVG tspan so that
    # the ASCII minus is used instead of U+207B (SUPERSCRIPT MINUS), which is
    # absent from many PDF-embedded fonts and renders as a missing-glyph square.
    attrib = {"x": str(col_x), "y": str(body_y)}
    attrib.update(body_style)
    text_el = ET.SubElement(g, f"{{{ns}}}text", attrib=attrib)
    line0_tspan = ET.SubElement(
        text_el, f"{{{ns}}}tspan", attrib={"x": str(col_x), "dy": "0"}
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
        g, ns, col_x, body_y + lh,
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
                           col_x, anno_y, scale=1):
    """Annotation: the two lobes ('wings') of the attractor."""
    g = _group(parent, ns)

    # Arrow from above the title up to the attractor target
    arrow_x = col_x + 25 * scale
    arrow_y = anno_y - 8 * scale
    _line(g, ns, arrow_x, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, arrow_x, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_x, anno_y + 2 * scale, "The Two \u2018Wings\u2019",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    # Body text
    lines = [
        "The trajectory orbits two unstable",
        "fixed points, spiralling around one",
        "lobe before switching to the other.",
        "The timing of each switch is",
        "unpredictable \u2014 that\u2019s chaos.",
    ]
    _multiline_text(
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )
    return g


def _annotation_infinite_complexity(parent, ns, target_x, target_y,
                                     col_x, anno_y, scale=1):
    """Annotation: the fractal nature of the strange attractor."""
    g = _group(parent, ns)

    # Arrow from above the title up to the attractor target
    arrow_x = col_x + 25 * scale
    arrow_y = anno_y - 8 * scale
    _line(g, ns, arrow_x, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, arrow_x, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_x, anno_y + 2 * scale, "Infinite Complexity",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    # Body text
    lines = [
        "The line never intersects itself,",
        "despite being trapped in a bounded",
        "region of space. A cross-section",
        "reveals fractal structure \u2014 infinite",
        "layers, like pages of a closed book.",
    ]
    _multiline_text(
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_equations(parent, ns, col_x, anno_y, scale=1):
    """Panel: the Lorenz ODEs and their parameter values."""
    g = _group(parent, ns)

    _text(g, ns, col_x, anno_y + 2 * scale,
          "The Equations",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    lines = [
        "Three coupled ordinary differential",
        "equations govern the motion:",
    ]
    _multiline_text(
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )

    # Equations in italic
    eq_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(4.0 * scale, 2)),
        "font-style": "italic",
    }
    eq_y = anno_y + 24 * scale
    _text(g, ns, col_x + 4 * scale, eq_y,
          "dx/dt = \u03c3(y \u2212 x)", **eq_style)
    _text(g, ns, col_x + 4 * scale, eq_y + 6 * scale,
          "dy/dt = x(\u03c1 \u2212 z) \u2212 y", **eq_style)
    _text(g, ns, col_x + 4 * scale, eq_y + 12 * scale,
          "dz/dt = xy \u2212 \u03b2z", **eq_style)

    # Parameter values
    param_y = eq_y + 21 * scale
    param_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(3.8 * scale, 2)),
    }
    _text(g, ns, col_x + 4 * scale, param_y,
          "\u03c3 = 10,  \u03c1 = 28,  \u03b2 = 8/3", **param_style)

    return g


def _panel_deterministic_chaos(parent, ns, col_x, anno_y, scale=1,
                               traj_main=None, traj_diverged=None):
    """Panel: deterministic chaos explanation with mini divergence plot."""
    g = _group(parent, ns)

    _text(g, ns, col_x, anno_y + 2 * scale,
          "Deterministic Chaos",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    lines = [
        "The rules are perfectly deterministic",
        "\u2014 no randomness whatsoever. Yet the",
        "outcome is practically unpredictable",
        "after a short time horizon.",
    ]
    _multiline_text(
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )

    # Mini x-vs-time divergence plot
    plot_x = col_x + 2 * scale
    plot_y = anno_y + 34 * scale
    plot_w = 56 * scale
    plot_h = 28 * scale

    # Axes
    _line(g, ns, plot_x, plot_y, plot_x, plot_y + plot_h,
          stroke="#1C1C1C", **{"stroke-width": str(round(0.2 * scale, 3))})
    _line(g, ns, plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h,
          stroke="#1C1C1C", **{"stroke-width": str(round(0.2 * scale, 3))})

    # Axis labels
    _text(g, ns, plot_x + plot_w / 2, plot_y + plot_h + 5 * scale, "time",
          **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
             "text-anchor": "middle", "font-style": "italic"})
    _text(g, ns, plot_x - 3 * scale, plot_y + plot_h / 2, "x",
          **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
             "text-anchor": "middle", "font-style": "italic"})

    # Plot trajectory snippets if data is provided
    if traj_main and traj_diverged:
        # Use first 2000 steps for the mini plot
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

        # Subsample for SVG performance
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


def _panel_weather_model(parent, ns, col_x, anno_y, scale=1):
    """Panel: Lorenz's meteorological origins."""
    g = _group(parent, ns)

    _text(g, ns, col_x, anno_y + 2 * scale,
          "A Weather Model",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

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
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )

    return g


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

# Colour palette – traditional museum/print aesthetic (ink on paper)
BG_COLOR = "#FFFEF8"              # warm ivory paper
ATTRACTOR_COLOR = "#1C1C1C"       # near-black ink
TITLE_COLOR = "#1C1C1C"           # dark title text
ACCENT_COLOR = "#8B0000"          # deep museum red
FOOTER_PRIMARY_COLOR = "#555555"  # footer primary text
FOOTER_SECONDARY_COLOR = "#777777"  # footer secondary text
DIVERGED_COLOR = "#8B0000"        # red for diverged trajectory


def generate_poster(steps=200000, width_mm=420, height_mm=594,
                    designed_by=None, designed_for=None):
    """Build and return the full poster as an ElementTree SVG root."""
    svg, ns = _svg_root(width_mm, height_mm)

    # Scale factor relative to reference A2 size (420 × 594 mm) so that
    # all font sizes and spacing adapt when the poster is resized.
    w_scale = width_mm / 420
    h_scale = height_mm / 594

    # Background
    _rect(svg, ns, 0, 0, width_mm, height_mm, fill=BG_COLOR)

    # --- Header (proportional to poster height) ---
    title_y = height_mm * 0.047
    subtitle_y = height_mm * 0.064
    rule_y = height_mm * 0.074

    _text(
        svg, ns, width_mm / 2, title_y,
        "The Lorenz Attractor",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(round(16 * w_scale, 2)),
            "fill": TITLE_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, subtitle_y,
        "Strange beauty from deterministic chaos",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(round(6 * w_scale, 2)),
            "fill": ACCENT_COLOR,
            "text-anchor": "middle",
        },
    )

    # Thin red rule beneath the header (classic museum print element)
    _line(
        svg, ns,
        width_mm * 0.15, rule_y,
        width_mm * 0.85, rule_y,
        stroke=ACCENT_COLOR,
        **{"stroke-width": str(round(0.4 * w_scale, 3))},
    )

    # Header credits flanking the rule
    header_credit_y = rule_y + 5 * h_scale
    header_credit_font = str(round(3.8 * w_scale, 2))
    header_credit_style = {
        "font-family": "Georgia, 'Times New Roman', serif",
        "font-size": header_credit_font,
        "font-style": "italic",
        "fill": FOOTER_SECONDARY_COLOR,
    }
    if designed_by:
        _text(
            svg, ns,
            width_mm * 0.15, header_credit_y,
            f"Designed by {designed_by}",
            **{**header_credit_style, "text-anchor": "start"},
        )
    if designed_for:
        _text(
            svg, ns,
            width_mm * 0.85, header_credit_y,
            f"Designed for {designed_for}",
            **{**header_credit_style, "text-anchor": "end"},
        )

    # Arrow marker for callouts
    _add_arrow_marker(svg, ns)

    # --- Compute Lorenz trajectory ---
    initial_main = (1.0, 1.0, 1.0)
    traj_main = integrate_lorenz(initial_main, steps=steps)

    # Second trajectory for butterfly effect (infinitesimal offset)
    initial_div = (1.0 + 1e-10, 1.0, 1.0)
    traj_div = integrate_lorenz(initial_div, steps=steps)

    # Project both to 2-D
    proj_main = project_3d_to_2d(traj_main)
    proj_div = project_3d_to_2d(traj_div)

    # --- Fit the attractor into the poster space ---
    min_top = rule_y + height_mm * 0.05
    anno_start_frac = 0.70
    max_bot = height_mm * anno_start_frac

    margin = width_mm * 0.10
    avail_w = width_mm - 2 * margin
    avail_h = max_bot - min_top

    # Bounding box of main projected trajectory
    all_px = [p[0] for p in proj_main]
    all_py = [p[1] for p in proj_main]
    raw_min_x, raw_max_x = min(all_px), max(all_px)
    raw_min_y, raw_max_y = min(all_py), max(all_py)
    raw_w = raw_max_x - raw_min_x if raw_max_x != raw_min_x else 1.0
    raw_h = raw_max_y - raw_min_y if raw_max_y != raw_min_y else 1.0

    # Uniform scale to fit inside the available area
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

    stroke_w = str(round(0.15 * w_scale, 3))

    # Split the main trajectory into segments for better SVG handling
    n_segments = 5
    seg_len = len(scaled_main) // n_segments
    for i in range(n_segments):
        start = i * seg_len
        # Overlap by one point so segments visually connect
        end = start + seg_len + 1 if i < n_segments - 1 else len(scaled_main)
        _polyline(attractor_group, ns, scaled_main[start:end],
                  stroke=ATTRACTOR_COLOR, opacity="0.6",
                  **{"stroke-width": stroke_w,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    # Diverged trajectory — show only the portion after actual divergence
    diverge_threshold = 1.0  # in SVG mm after scaling
    diverge_start = len(scaled_main) - 1
    for idx in range(len(scaled_main)):
        dx = scaled_main[idx][0] - scaled_div[idx][0]
        dy = scaled_main[idx][1] - scaled_div[idx][1]
        if math.hypot(dx, dy) > diverge_threshold:
            diverge_start = idx
            break

    if diverge_start < len(scaled_div):
        _polyline(attractor_group, ns, scaled_div[diverge_start:],
                  stroke=DIVERGED_COLOR, opacity="0.35",
                  **{"stroke-width": stroke_w,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    # --- Annotations (below the attractor in a three-column layout) ---
    anno_group = _group(svg, ns, id="annotations")

    # Compute attractor bounding box for separator positioning
    vis_ys = [p[1] for p in scaled_main]
    attractor_bottom = max(vis_ys)

    # Subtle separator line between attractor and annotations
    anno_sep_y = attractor_bottom + 10 * h_scale
    _line(
        anno_group, ns,
        width_mm * 0.15, anno_sep_y,
        width_mm * 0.85, anno_sep_y,
        stroke=ACCENT_COLOR,
        **{"stroke-width": str(round(0.3 * w_scale, 3)), "opacity": "0.5"},
    )

    anno_y = anno_sep_y + 18 * h_scale

    # Three-column x positions
    col1_x = width_mm * 0.04
    col2_x = width_mm * 0.35
    col3_x = width_mm * 0.67

    # --- Arrow targets on the attractor ---
    # Butterfly effect → region where the two trajectories diverge
    if diverge_start < len(scaled_main):
        be_idx = min(diverge_start + len(scaled_main) // 20,
                     len(scaled_main) - 1)
        be_target_x = scaled_main[be_idx][0]
        be_target_y = scaled_main[be_idx][1]
    else:
        be_target_x = center_x - avail_w * 0.15
        be_target_y = center_y

    # Two wings → the left lobe (roughly where x is most negative)
    vis_xs = [p[0] for p in scaled_main]
    left_idx = vis_xs.index(min(vis_xs))
    wing_target_x = scaled_main[left_idx][0]
    wing_target_y = scaled_main[left_idx][1]

    # Infinite complexity → densest region near centre bottom
    dense_target_x = center_x
    dense_target_y = center_y + avail_h * 0.15

    _annotation_butterfly_effect(anno_group, ns,
                                 be_target_x, be_target_y,
                                 col1_x, anno_y, w_scale)

    _annotation_two_wings(anno_group, ns,
                          wing_target_x, wing_target_y,
                          col2_x, anno_y, w_scale)

    _annotation_infinite_complexity(anno_group, ns,
                                    dense_target_x, dense_target_y,
                                    col3_x, anno_y, w_scale)

    # --- Second row: educational connections ---
    edu_group = _group(svg, ns, id="educational")

    # Separator between annotation rows
    row2_sep_y = anno_y + 55 * w_scale
    _line(
        edu_group, ns,
        width_mm * 0.15, row2_sep_y,
        width_mm * 0.85, row2_sep_y,
        stroke=ACCENT_COLOR,
        **{"stroke-width": str(round(0.3 * w_scale, 3)), "opacity": "0.35"},
    )

    row2_y = row2_sep_y + 12 * w_scale

    _panel_equations(edu_group, ns, col1_x, row2_y, w_scale)
    _panel_deterministic_chaos(edu_group, ns, col2_x, row2_y, w_scale,
                               traj_main=traj_main, traj_diverged=traj_div)
    _panel_weather_model(edu_group, ns, col3_x, row2_y, w_scale)

    # --- Footer ---
    footer_y = height_mm - 18 * h_scale
    footer_font = round(4 * w_scale, 2)
    footer_font_sm = round(3.5 * w_scale, 2)

    _text(
        svg, ns, width_mm / 2, footer_y,
        "Edward Lorenz discovered this attractor in 1963 "
        "while modelling atmospheric convection.",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(footer_font),
            "fill": FOOTER_PRIMARY_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, footer_y + 6 * h_scale,
        f"Generated with {steps:,} integration steps  "
        f"\u00b7  dt = 0.005  \u00b7  \u03c3 = 10, \u03c1 = 28, \u03b2 = 8/3",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(footer_font_sm),
            "fill": FOOTER_SECONDARY_COLOR,
            "text-anchor": "middle",
        },
    )

    # Optional credit line: "Designed by X for Z"
    if designed_by or designed_for:
        parts = []
        if designed_by:
            parts.append(f"Designed by {designed_by}")
        if designed_for:
            parts.append(f"for {designed_for}")
        credit_text = " ".join(parts)
        _text(
            svg, ns, width_mm / 2, footer_y + 12 * h_scale,
            credit_text,
            **{
                "font-family": "Georgia, 'Times New Roman', serif",
                "font-size": str(footer_font_sm),
                "fill": FOOTER_SECONDARY_COLOR,
                "font-style": "italic",
                "text-anchor": "middle",
            },
        )

    # Decorative double border (outer rule + inner rule — classic poster look)
    border_w = round(0.8 * w_scale, 3)
    border_w_inner = round(0.2 * w_scale, 3)
    _rect(
        svg, ns, 4, 4, width_mm - 8, height_mm - 8,
        fill="none", stroke=TITLE_COLOR,
        **{"stroke-width": str(border_w)},
    )
    _rect(
        svg, ns, 7, 7, width_mm - 14, height_mm - 14,
        fill="none", stroke=TITLE_COLOR,
        **{"stroke-width": str(border_w_inner)},
    )

    return svg


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_svg(svg_root, filepath):
    """Write the SVG element tree to *filepath*."""
    tree = ET.ElementTree(svg_root)
    ET.indent(tree, space="  ")
    tree.write(filepath, encoding="unicode", xml_declaration=True)


def write_pdf(svg_root, filepath):
    """Write the poster as PDF via cairosvg (must be installed)."""
    try:
        import cairosvg
    except ImportError:
        print(
            "Error: 'cairosvg' is required for PDF output.\n"
            "Install it with:  pip install cairosvg",
            file=sys.stderr,
        )
        sys.exit(1)

    # Render SVG string → PDF
    svg_bytes = ET.tostring(svg_root, encoding="unicode", xml_declaration=True)
    cairosvg.svg2pdf(bytestring=svg_bytes.encode("utf-8"), write_to=filepath)


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
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: lorenz_poster.<format>).",
    )
    parser.add_argument(
        "--format", type=str, choices=["svg", "pdf"], default="svg",
        help="Output format (default: svg).",
    )
    parser.add_argument(
        "--width", type=float, default=420,
        help="Poster width in mm (default: 420, A2).",
    )
    parser.add_argument(
        "--height", type=float, default=594,
        help="Poster height in mm (default: 594, A2).",
    )
    parser.add_argument(
        "--designed-by", type=str, default=None, dest="designed_by",
        help="Designer credit, e.g. 'Alice and Bob'.",
    )
    parser.add_argument(
        "--designed-for", type=str, default=None, dest="designed_for",
        help="Client / purpose credit, e.g. 'the Science Museum'.",
    )
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.output is None:
        args.output = f"lorenz_poster.{args.format}"

    print(f"Generating Lorenz Attractor poster (steps={args.steps}) \u2026")
    svg = generate_poster(
        steps=args.steps,
        width_mm=args.width,
        height_mm=args.height,
        designed_by=args.designed_by,
        designed_for=args.designed_for,
    )

    if args.format == "pdf":
        write_pdf(svg, args.output)
    else:
        write_svg(svg, args.output)

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
