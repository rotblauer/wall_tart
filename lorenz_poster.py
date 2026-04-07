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
    get_theme,
    ProgressReporter,
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
                     sigma=10.0, rho=28.0, beta=8.0 / 3.0, progress=None):
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
    progress : ProgressReporter or None
        Optional progress reporter updated once per step.

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
        if progress is not None:
            progress.update()
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
# Default projection angles (radians)
#
# These angles control the 3-D → 2-D rotation used when drawing the
# attractor.  Adjusting them changes the viewing perspective:
#   angle_x  — rotation about the X-axis (tilts the butterfly up/down)
#   angle_z  — rotation about the Z-axis (rotates the butterfly left/right)
# ---------------------------------------------------------------------------

DEFAULT_ANGLE_X = -0.35
DEFAULT_ANGLE_Z = 0.85


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

    _multiline_text(
        g, ns, col_cx, body_y,
        [
            "Two trajectories start just 1e-10",
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
    """Annotation: the fractal nature of the strange attractor.

    The callout line points to the zoom inset panel (target_x/target_y are
    set to the panel's centre so the arrow terminates there).
    The Poincaré section panel (in the adjacent inter-column gap) is
    referenced in the body text.
    """
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Infinite Complexity", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "The line never intersects itself,",
        "despite being trapped in a bounded",
        "region of space. A Poincar\u00e9 section",
        "\u2014 all crossings through z = 27 \u2014",
        "exposes fractal layers: infinite",
        "sheets, like pages of a closed book.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Zoom inset panel
# ---------------------------------------------------------------------------

def _find_best_zoom_center(scaled_main, origin_x, origin_y, w_scale):
    """Find the best zoom centre near the saddle / origin region.

    Searches a neighbourhood around *origin_x*, *origin_y* (the poster-space
    projection of the 3-D origin) using a combined density × parallelism
    metric.  The result is the point that best reveals the fractal sheet
    structure — many trajectory passes flowing in nearly the same direction
    at slightly different offsets, creating visible layers.
    """
    search_radius = 25.0 * w_scale
    bin_size = 4.0 * w_scale

    bins_count: dict[tuple[int, int], int] = {}
    bins_sin2: dict[tuple[int, int], float] = {}
    bins_cos2: dict[tuple[int, int], float] = {}

    prev = None
    for px, py in scaled_main:
        if (abs(px - origin_x) > search_radius
                or abs(py - origin_y) > search_radius):
            prev = (px, py)
            continue

        bx = int((px - origin_x) / bin_size)
        by = int((py - origin_y) / bin_size)
        key = (bx, by)
        bins_count[key] = bins_count.get(key, 0) + 1

        if prev is not None:
            dx = px - prev[0]
            dy = py - prev[1]
            if abs(dx) > 1e-10 or abs(dy) > 1e-10:
                angle = math.atan2(dy, dx)
                bins_sin2[key] = bins_sin2.get(key, 0) + math.sin(2 * angle)
                bins_cos2[key] = bins_cos2.get(key, 0) + math.cos(2 * angle)
        prev = (px, py)

    if not bins_count:
        return origin_x, origin_y

    best_score = -1.0
    best_key = None
    for key, count in bins_count.items():
        if count < 20:
            continue
        s2 = bins_sin2.get(key, 0.0)
        c2 = bins_cos2.get(key, 0.0)
        parallelism = math.hypot(s2, c2) / count   # mean resultant length ∈ [0, 1]
        score = math.log(count + 1) * parallelism
        if score > best_score:
            best_score = score
            best_key = key

    if best_key is None:
        return origin_x, origin_y

    return (origin_x + (best_key[0] + 0.5) * bin_size,
            origin_y + (best_key[1] + 0.5) * bin_size)


def _draw_zoom_inset(svg, ns, scaled_main, w_scale, h_scale,
                     center_x, center_y, avail_w, avail_h, min_top,
                     width_mm, attractor_color, origin_poster=None,
                     theme=None, scaled_extra=None):
    """Draw a zoom-inset panel highlighting the saddle / transition region.

    The saddle region near the 3-D origin (0, 0, 0) is where the two lobes
    of the Lorenz attractor meet and trajectories switch between wings.
    At sufficient magnification the trajectory sheets separate into visible
    fractal layers — locally parallel, closely spaced, and never
    self-intersecting.

    A density × parallelism search around the projected origin finds the
    exact sub-region with the richest visible lamination.

    Adds:
      - a small target bounding box on the main attractor,
      - faint dashed connector lines from the target box corners to the zoom
        panel corners,
      - a background-filled zoom panel in the upper-right free area,
      - high-magnification attractor lines clipped to the panel boundary, and
      - a subtle border and label on the zoom panel.

    Returns
    -------
    dict
        Zoom-info dict used by :func:`_draw_ultra_zoom_inset` and by the
        caller to place the 'Infinite Complexity' annotation.  Keys:
        ``anno_target``, ``src_cx``, ``src_cy``, ``src_hw``, ``src_hh``,
        ``zoom_x``, ``zoom_y``, ``zoom_w``, ``zoom_h``, ``zoom_cx``,
        ``zoom_cy``, ``magnify``.
    """
    t = get_theme(theme)
    border_color = t["border_color"]
    bg_color = t["bg_color"]

    # --- Source (target) box near the saddle / transition region ---
    src_hw = 6.0 * w_scale               # half-width  → 12 mm total
    src_hh = 6.0 * w_scale               # half-height → 12 mm total

    if origin_poster is not None:
        origin_x, origin_y = origin_poster
    else:
        # Fallback: attractor centre (less ideal, but safe)
        origin_x, origin_y = center_x, center_y

    src_cx, src_cy = _find_best_zoom_center(
        scaled_main, origin_x, origin_y, w_scale,
    )

    src_x1, src_y1 = src_cx - src_hw, src_cy - src_hh
    src_x2, src_y2 = src_cx + src_hw, src_cy + src_hh

    # --- Zoom panel in the upper-right free area ---
    right_margin = (width_mm - avail_w) / 2  # horizontal margin (left = right)
    max_bot = min_top + avail_h

    zoom_w = min(70.0 * w_scale, avail_w * 0.4)
    zoom_h = min(70.0 * w_scale, avail_h * 0.4)
    zoom_x = width_mm - right_margin - zoom_w  # flush with right margin
    zoom_y = min_top + 4.0 * h_scale           # just below the header-rule gap

    # Clamp so the panel stays within poster bounds.
    if zoom_x + zoom_w > width_mm - right_margin:
        zoom_x = width_mm - right_margin - zoom_w
    if zoom_y + zoom_h > max_bot:
        zoom_h = max_bot - zoom_y

    zoom_cx = zoom_x + zoom_w / 2
    zoom_cy = zoom_y + zoom_h / 2

    magnify = zoom_w / (2 * src_hw)     # ≈ 4.8 ×

    # Round to one decimal for display in the label.
    magnify_label = f"{magnify:.1f}\u00d7 magnified"

    # --- Add clipPath for the zoom panel to <defs> ---
    defs_el = svg.find(f"{{{ns}}}defs")
    if defs_el is None:
        defs_el = ET.SubElement(svg, f"{{{ns}}}defs")
    clip_id = "zoom_panel_clip"
    clip_path_el = ET.SubElement(defs_el, f"{{{ns}}}clipPath",
                                  attrib={"id": clip_id})
    ET.SubElement(clip_path_el, f"{{{ns}}}rect", attrib={
        "x": str(round(zoom_x, 4)),
        "y": str(round(zoom_y, 4)),
        "width": str(round(zoom_w, 4)),
        "height": str(round(zoom_h, 4)),
    })

    # --- Group that holds all zoom-inset elements ---
    zoom_group = _group(svg, ns, id="zoom_inset")

    # --- Connector lines: source-box corners → zoom-panel corners ---
    conn_style = {
        "stroke": border_color,
        "stroke-width": str(round(0.25 * w_scale, 3)),
        "stroke-dasharray": "1.5,1.5",
        "opacity": "0.35",
    }
    src_corners = [
        (src_x1, src_y1), (src_x2, src_y1),
        (src_x2, src_y2), (src_x1, src_y2),
    ]
    zoom_corners = [
        (zoom_x, zoom_y), (zoom_x + zoom_w, zoom_y),
        (zoom_x + zoom_w, zoom_y + zoom_h), (zoom_x, zoom_y + zoom_h),
    ]
    for (sx, sy), (zx, zy) in zip(src_corners, zoom_corners):
        _line(zoom_group, ns, sx, sy, zx, zy, **conn_style)

    # --- Zoom panel background (covers underlying attractor lines) ---
    _rect(zoom_group, ns, zoom_x, zoom_y, zoom_w, zoom_h,
          fill=bg_color, stroke="none", opacity="0.92")

    # --- Zoomed attractor lines (clipped to the panel) ---
    # Sample region: extend to 2× the source-box half-dimensions so that
    # trajectory segments entering/exiting the box are included and smoothly
    # clipped by the clipPath (total sampled area = 4× source-box area).
    sample_hw = src_hw * 2.0
    sample_hh = src_hh * 2.0
    zoom_lines_g = _group(zoom_group, ns, **{"clip-path": f"url(#{clip_id})"})

    # Ultra-thin stroke to reveal individual fractal sheets at this zoom level.
    thin_sw = str(round(0.05 * w_scale, 3))

    def _to_zoom(px, py):
        return (zoom_cx + (px - src_cx) * magnify,
                zoom_cy + (py - src_cy) * magnify)

    segment = []
    for px, py in scaled_main:
        if abs(px - src_cx) <= sample_hw and abs(py - src_cy) <= sample_hh:
            segment.append(_to_zoom(px, py))
        else:
            if len(segment) >= 2:
                _polyline(zoom_lines_g, ns, segment,
                          stroke=attractor_color, opacity="0.75",
                          **{"stroke-width": thin_sw,
                             "stroke-linejoin": "round",
                             "stroke-linecap": "round"})
            segment = []
    if len(segment) >= 2:
        _polyline(zoom_lines_g, ns, segment,
                  stroke=attractor_color, opacity="0.75",
                  **{"stroke-width": thin_sw,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    # --- Extra-detail trajectory (only in zoom) ---
    # Drawn at reduced opacity so it is subtly distinguishable from the
    # main trajectory while still contributing fractal detail.
    if scaled_extra:
        extra_sw = str(round(0.04 * w_scale, 3))
        segment = []
        for px, py in scaled_extra:
            if abs(px - src_cx) <= sample_hw and abs(py - src_cy) <= sample_hh:
                segment.append(_to_zoom(px, py))
            else:
                if len(segment) >= 2:
                    _polyline(zoom_lines_g, ns, segment,
                              stroke=attractor_color, opacity="0.45",
                              **{"stroke-width": extra_sw,
                                 "stroke-linejoin": "round",
                                 "stroke-linecap": "round"})
                segment = []
        if len(segment) >= 2:
            _polyline(zoom_lines_g, ns, segment,
                      stroke=attractor_color, opacity="0.45",
                      **{"stroke-width": extra_sw,
                         "stroke-linejoin": "round",
                         "stroke-linecap": "round"})

    # --- Zoom panel border ---
    _rect(zoom_group, ns, zoom_x, zoom_y, zoom_w, zoom_h,
          fill="none", stroke=border_color,
          **{"stroke-width": str(round(0.5 * w_scale, 3))})

    # --- Subtle label in bottom of zoom panel ---
    _text(zoom_group, ns, zoom_cx, zoom_y + zoom_h - 3.5 * h_scale,
          f"{magnify_label}  \u2014  saddle region",
          **{**ANNOTATION_STYLE,
             "fill": border_color,
             "font-size": str(round(2.8 * w_scale, 2)),
             "text-anchor": "middle",
             "opacity": "0.55"})

    # --- Source (target) box on the main attractor ---
    _rect(zoom_group, ns, src_x1, src_y1, 2 * src_hw, 2 * src_hh,
          fill=border_color,
          **{"fill-opacity": "0.07",
             "stroke": border_color,
             "stroke-width": str(round(0.35 * w_scale, 3))})

    # Return zoom info for the 'Infinite Complexity' annotation and for
    # the ultra-zoom panel.
    return {
        "anno_target": (zoom_cx, zoom_y + zoom_h),
        "src_cx": src_cx,
        "src_cy": src_cy,
        "src_hw": src_hw,
        "src_hh": src_hh,
        "zoom_x": zoom_x,
        "zoom_y": zoom_y,
        "zoom_w": zoom_w,
        "zoom_h": zoom_h,
        "zoom_cx": zoom_cx,
        "zoom_cy": zoom_cy,
        "magnify": magnify,
        "max_bot": max_bot,
        "right_margin": right_margin,
    }


def _draw_ultra_zoom_inset(svg, ns, scaled_main, w_scale, h_scale,
                           zoom_info, width_mm, attractor_color,
                           theme=None, scaled_extra=None):
    """Draw a second-level ultra-zoom panel for deeper fractal structure.

    Zooms further into the *same* outer-turnaround-edge region targeted by
    the first zoom, revealing even finer fractal lamination.  The panel is
    placed directly below the first zoom panel.

    A small sub-box is drawn on the first zoom panel to indicate the area
    magnified by this second-level zoom, and faint dashed connector lines
    link the sub-box to the ultra-zoom panel corners.
    """
    t = get_theme(theme)
    border_color = t["border_color"]
    bg_color = t["bg_color"]

    # --- Unpack first-zoom info ---
    src_cx = zoom_info["src_cx"]
    src_cy = zoom_info["src_cy"]
    z1_zoom_cx = zoom_info["zoom_cx"]
    z1_zoom_cy = zoom_info["zoom_cy"]
    z1_zoom_x = zoom_info["zoom_x"]
    z1_zoom_y = zoom_info["zoom_y"]
    z1_zoom_w = zoom_info["zoom_w"]
    z1_zoom_h = zoom_info["zoom_h"]
    z1_magnify = zoom_info["magnify"]

    # --- Ultra-zoom source box (same centre, tighter window) ---
    uz_src_hw = 2.0 * w_scale           # half-width  → 4 mm total
    uz_src_hh = 2.0 * w_scale           # half-height → 4 mm total

    # --- Ultra-zoom panel: placed below the first zoom panel ---
    uz_w = min(46.0 * w_scale, z1_zoom_w * 0.85)
    uz_h = min(46.0 * w_scale, z1_zoom_h * 0.85)
    uz_x = z1_zoom_x + z1_zoom_w - uz_w  # right-aligned with first zoom
    uz_y = z1_zoom_y + z1_zoom_h + 6.0 * w_scale  # gap below first zoom

    # Clamp so the panel stays within poster bounds.
    max_bot = zoom_info.get("max_bot", uz_y + uz_h + 20)
    right_margin = zoom_info.get("right_margin", width_mm * 0.10)
    if uz_x + uz_w > width_mm - right_margin:
        uz_x = width_mm - right_margin - uz_w
    if uz_x < z1_zoom_x:
        uz_x = z1_zoom_x
    if uz_y + uz_h > max_bot:
        uz_h = max(10.0 * w_scale, max_bot - uz_y)

    uz_cx = uz_x + uz_w / 2
    uz_cy = uz_y + uz_h / 2

    uz_magnify = uz_w / (2 * uz_src_hw)  # 36 / 4 = 9 ×
    uz_magnify_label = f"{uz_magnify:.0f}\u00d7 into outer layer"

    # --- clipPath for ultra-zoom panel ---
    defs_el = svg.find(f"{{{ns}}}defs")
    if defs_el is None:
        defs_el = ET.SubElement(svg, f"{{{ns}}}defs")
    uz_clip_id = "ultra_zoom_clip"
    uz_clip_el = ET.SubElement(defs_el, f"{{{ns}}}clipPath",
                               attrib={"id": uz_clip_id})
    ET.SubElement(uz_clip_el, f"{{{ns}}}rect", attrib={
        "x": str(round(uz_x, 4)),
        "y": str(round(uz_y, 4)),
        "width": str(round(uz_w, 4)),
        "height": str(round(uz_h, 4)),
    })

    # --- Group for all ultra-zoom elements ---
    uz_group = _group(svg, ns, id="ultra_zoom_inset")

    # --- Sub-box on the first zoom panel (showing ultra-zoom region) ---
    sub_on_z1_hw = uz_src_hw * z1_magnify
    sub_on_z1_hh = uz_src_hh * z1_magnify
    sub_on_z1_x = z1_zoom_cx - sub_on_z1_hw
    sub_on_z1_y = z1_zoom_cy - sub_on_z1_hh
    _rect(uz_group, ns, sub_on_z1_x, sub_on_z1_y,
          2 * sub_on_z1_hw, 2 * sub_on_z1_hh,
          fill=border_color,
          **{"fill-opacity": "0.07",
             "stroke": border_color,
             "stroke-width": str(round(0.3 * w_scale, 3))})

    # --- Connector lines: sub-box on first zoom → ultra-zoom panel ---
    conn_style = {
        "stroke": border_color,
        "stroke-width": str(round(0.25 * w_scale, 3)),
        "stroke-dasharray": "1.5,1.5",
        "opacity": "0.35",
    }
    sub_corners = [
        (sub_on_z1_x, sub_on_z1_y + 2 * sub_on_z1_hh),              # bottom-left
        (sub_on_z1_x + 2 * sub_on_z1_hw, sub_on_z1_y + 2 * sub_on_z1_hh),  # bottom-right
    ]
    uz_top_corners = [
        (uz_x, uz_y),              # top-left
        (uz_x + uz_w, uz_y),       # top-right
    ]
    for (sx, sy), (zx, zy) in zip(sub_corners, uz_top_corners):
        _line(uz_group, ns, sx, sy, zx, zy, **conn_style)

    # --- Ultra-zoom panel background ---
    _rect(uz_group, ns, uz_x, uz_y, uz_w, uz_h,
          fill=bg_color, stroke="none", opacity="0.92")

    # --- Zoomed attractor lines (clipped to panel) ---
    sample_hw = uz_src_hw * 2.0
    sample_hh = uz_src_hh * 2.0
    uz_lines_g = _group(uz_group, ns, **{"clip-path": f"url(#{uz_clip_id})"})

    ultra_thin_sw = str(round(0.03 * w_scale, 3))

    def _to_uz(px, py):
        return (uz_cx + (px - src_cx) * uz_magnify,
                uz_cy + (py - src_cy) * uz_magnify)

    segment = []
    for px, py in scaled_main:
        if abs(px - src_cx) <= sample_hw and abs(py - src_cy) <= sample_hh:
            segment.append(_to_uz(px, py))
        else:
            if len(segment) >= 2:
                _polyline(uz_lines_g, ns, segment,
                          stroke=attractor_color, opacity="0.75",
                          **{"stroke-width": ultra_thin_sw,
                             "stroke-linejoin": "round",
                             "stroke-linecap": "round"})
            segment = []
    if len(segment) >= 2:
        _polyline(uz_lines_g, ns, segment,
                  stroke=attractor_color, opacity="0.75",
                  **{"stroke-width": ultra_thin_sw,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    # --- Extra-detail trajectory (only in ultra-zoom) ---
    # Drawn at reduced opacity so it is subtly distinguishable from the
    # main trajectory while still contributing fractal detail.
    if scaled_extra:
        extra_sw = str(round(0.02 * w_scale, 3))
        segment = []
        for px, py in scaled_extra:
            if abs(px - src_cx) <= sample_hw and abs(py - src_cy) <= sample_hh:
                segment.append(_to_uz(px, py))
            else:
                if len(segment) >= 2:
                    _polyline(uz_lines_g, ns, segment,
                              stroke=attractor_color, opacity="0.45",
                              **{"stroke-width": extra_sw,
                                 "stroke-linejoin": "round",
                                 "stroke-linecap": "round"})
                segment = []
        if len(segment) >= 2:
            _polyline(uz_lines_g, ns, segment,
                      stroke=attractor_color, opacity="0.45",
                      **{"stroke-width": extra_sw,
                         "stroke-linejoin": "round",
                         "stroke-linecap": "round"})

    # --- Ultra-zoom panel border ---
    _rect(uz_group, ns, uz_x, uz_y, uz_w, uz_h,
          fill="none", stroke=border_color,
          **{"stroke-width": str(round(0.5 * w_scale, 3))})

    # --- Label at bottom of ultra-zoom panel ---
    _text(uz_group, ns, uz_cx, uz_y + uz_h - 3.0 * h_scale,
          uz_magnify_label,
          **{**ANNOTATION_STYLE,
             "fill": border_color,
             "font-size": str(round(2.4 * w_scale, 2)),
             "text-anchor": "middle",
             "opacity": "0.55"})


# ---------------------------------------------------------------------------
# Poincaré section helpers
# ---------------------------------------------------------------------------

def compute_poincare_section(trajectory, z0=27.0, tol=0.5):
    """Collect (x, y) points where the trajectory crosses z ≈ z0.

    The Poincaré section is a standard tool for visualising fractal
    structure in the Lorenz attractor.  By slicing through a fixed
    z-plane the continuous 3-D flow is reduced to a 2-D point cloud
    whose structure reveals the attractor's fractal layers.

    Parameters
    ----------
    trajectory : list[tuple[float, float, float]]
        3-D trajectory from :func:`integrate_lorenz`.
    z0 : float
        The z-value at which to take the cross-section (default 27,
        near the top of the attractor where the lobes meet).
    tol : float
        Half-width of the z-band: points with ``|z - z0| < tol``
        are included.

    Returns
    -------
    list[tuple[float, float]]
        The (x, y) coordinates of each crossing point.
    """
    section = []
    for x, y, z in trajectory:
        if abs(z - z0) < tol:
            section.append((x, y))
    return section


def _draw_poincare_inset(svg, ns, poincare_pts, w_scale, h_scale,
                         anno_y, anno_sep_y, col2_cx, col3_cx,
                         attractor_color, theme=None):
    """Draw a Poincaré section inset panel in the annotation-row inter-column gap.

    The panel is centred in the horizontal gap between the col2 and col3
    annotation columns (same pattern as the logistic-map inline zoom panels),
    at the same vertical level as the annotation text.  A short dashed leader
    line rises from the panel top to the annotation separator.

    Parameters
    ----------
    anno_y : float
        Y-coordinate of the top of the annotation text row (poster mm).
    anno_sep_y : float
        Y-coordinate of the annotation separator line (panel leader line
        terminus).
    col2_cx, col3_cx : float
        Centre x-coordinates of the second and third annotation columns (mm).
    attractor_color : str
        Fill colour for the scatter dots.
    theme : str or None
        Poster theme name.
    """
    t = get_theme(theme)
    border_color = t["border_color"]
    bg_color = t["bg_color"]

    # --- Panel geometry: inter-column gap between col2 and col3 ---
    col_gap = col3_cx - col2_cx
    ps_w = col_gap * 0.40
    ps_h = min(ps_w, 44.0 * w_scale)   # square or capped at 44 mm
    ps_cx = (col2_cx + col3_cx) / 2
    ps_cy = anno_y + 1.0 * h_scale + ps_h / 2
    ps_x = ps_cx - ps_w / 2
    ps_y = ps_cy - ps_h / 2

    # --- clipPath ---
    defs_el = svg.find(f"{{{ns}}}defs")
    if defs_el is None:
        defs_el = ET.SubElement(svg, f"{{{ns}}}defs")
    clip_id = "poincare_clip"
    clip_el = ET.SubElement(defs_el, f"{{{ns}}}clipPath",
                            attrib={"id": clip_id})
    ET.SubElement(clip_el, f"{{{ns}}}rect", attrib={
        "x": str(round(ps_x, 4)),
        "y": str(round(ps_y, 4)),
        "width": str(round(ps_w, 4)),
        "height": str(round(ps_h, 4)),
    })

    # --- Group ---
    ps_group = _group(svg, ns, id="poincare_inset")

    # --- Leader line: panel top-centre → annotation separator ---
    _line(ps_group, ns,
          ps_cx, ps_y,
          ps_cx, anno_sep_y,
          **{"stroke": border_color,
             "stroke-width": str(round(0.25 * w_scale, 3)),
             "stroke-dasharray": "1.5,1.5",
             "opacity": "0.5"})
    # Small filled circle at the terminus (same as logistic map)
    _circle(ps_group, ns,
            round(ps_cx, 2), round(anno_sep_y, 2),
            round(0.8 * w_scale, 3),
            fill=border_color, opacity="0.45")

    # --- Background ---
    _rect(ps_group, ns, ps_x, ps_y, ps_w, ps_h,
          fill=bg_color, stroke="none", opacity="0.92")

    # --- Plot Poincaré points ---
    if poincare_pts:
        px_vals = [p[0] for p in poincare_pts]
        py_vals = [p[1] for p in poincare_pts]
        x_min, x_max = min(px_vals), max(px_vals)
        y_min, y_max = min(py_vals), max(py_vals)
        x_range = x_max - x_min if x_max != x_min else 1.0
        y_range = y_max - y_min if y_max != y_min else 1.0

        pad = 0.05
        plot_w = ps_w * (1 - 2 * pad)
        plot_h = ps_h * (1 - 2 * pad)
        plot_x0 = ps_x + ps_w * pad
        plot_y0 = ps_y + ps_h * pad

        scatter_g = _group(ps_group, ns, **{"clip-path": f"url(#{clip_id})"})
        dot_r = str(round(0.25 * w_scale, 3))
        for px, py in poincare_pts:
            sx = plot_x0 + ((px - x_min) / x_range) * plot_w
            sy = plot_y0 + ((py - y_min) / y_range) * plot_h
            _circle(scatter_g, ns, sx, sy, dot_r,
                    fill=attractor_color, opacity="0.55")

    # --- Border ---
    _rect(ps_group, ns, ps_x, ps_y, ps_w, ps_h,
          fill="none", stroke=border_color,
          **{"stroke-width": str(round(0.5 * w_scale, 3))})

    # --- Label below panel border (same style as logistic-map zoom labels) ---
    _text(ps_group, ns, ps_cx, ps_y + ps_h + 3.5 * h_scale,
          "Poincar\u00e9 section (z \u2248 27)",
          **{**ANNOTATION_STYLE,
             "fill": border_color,
             "font-size": str(round(2.8 * w_scale, 2)),
             "text-anchor": "middle",
             "opacity": "0.65"})


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
                                traj_main=None, traj_diverged=None,
                                attractor_color=None, diverged_color=None):
    """Panel: deterministic chaos explanation with mini divergence plot."""
    if attractor_color is None:
        attractor_color = ATTRACTOR_COLOR
    if diverged_color is None:
        diverged_color = DIVERGED_COLOR
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
          stroke=attractor_color, **{"stroke-width": str(round(0.2 * scale, 3))})
    _line(g, ns, plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h,
          stroke=attractor_color, **{"stroke-width": str(round(0.2 * scale, 3))})

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
                  stroke=attractor_color, opacity="0.7",
                  **{"stroke-width": str(round(0.25 * scale, 3))})
        _polyline(g, ns, pts_div,
                  stroke=diverged_color, opacity="0.7",
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

def generate_poster(steps=200000, zoom_multiplier=2, width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None, verbose=True,
                    angle_x=None, angle_z=None):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    steps : int
        Number of RK4 integration steps for the main trajectory.
    zoom_multiplier : int
        Extra integration multiplier for zoom panels (0 to disable).
    width_mm, height_mm : float
        Poster dimensions in millimetres.
    designed_by, designed_for : str or None
        Optional credit lines for the poster footer.
    theme : str or None
        Colour-theme name (see :data:`poster_utils.AVAILABLE_THEMES`).
    verbose : bool
        If True, print progress bars to stderr during integration.
    angle_x : float or None
        Rotation angle about the X-axis for the 3-D → 2-D projection
        (radians).  Defaults to :data:`DEFAULT_ANGLE_X` (-0.35).
    angle_z : float or None
        Rotation angle about the Z-axis for the 3-D → 2-D projection
        (radians).  Defaults to :data:`DEFAULT_ANGLE_Z` (0.85).
    """
    if angle_x is None:
        angle_x = DEFAULT_ANGLE_X
    if angle_z is None:
        angle_z = DEFAULT_ANGLE_Z

    t = get_theme(theme)
    attractor_color = t["content_primary"]
    diverged_color = t["accent_color"]

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
    _p1 = ProgressReporter(steps, "Lorenz: main traj") if verbose else None
    traj_main = integrate_lorenz(initial_main, steps=steps, progress=_p1)
    if _p1:
        _p1.done()

    initial_div = (1.0 + 1e-10, 1.0, 1.0)
    _p2 = ProgressReporter(steps, "Lorenz: chaos diverge") if verbose else None
    traj_div = integrate_lorenz(initial_div, steps=steps, progress=_p2)
    if _p2:
        _p2.done()

    # --- Compute extra trajectory for high-res zoom panels ---
    extra_steps = steps * zoom_multiplier
    if extra_steps > 0:
        last_pt = traj_main[-1]
        _p3 = ProgressReporter(extra_steps, "Lorenz: zoom detail") if verbose else None
        traj_extra = integrate_lorenz(last_pt, steps=extra_steps, progress=_p3)
        if _p3:
            _p3.done()
    else:
        traj_extra = []

    proj_main = project_3d_to_2d(traj_main, angle_x=angle_x, angle_z=angle_z)
    proj_div = project_3d_to_2d(traj_div, angle_x=angle_x, angle_z=angle_z)

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

    if traj_extra:
        proj_extra = project_3d_to_2d(traj_extra, angle_x=angle_x, angle_z=angle_z)
        scaled_extra = [_transform(px, py) for px, py in proj_extra]
    else:
        scaled_extra = []

    # --- Main attractor visualisation ---
    attractor_group = _group(svg, ns, id="attractor")

    stroke_w = str(round(0.12 * w_scale, 3))

    n_segments = 5
    seg_len = len(scaled_main) // n_segments
    for i in range(n_segments):
        start = i * seg_len
        end = start + seg_len + 1 if i < n_segments - 1 else len(scaled_main)
        _polyline(attractor_group, ns, scaled_main[start:end],
                  stroke=attractor_color, opacity="0.4",
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
                  stroke=diverged_color, opacity="0.25",
                  **{"stroke-width": stroke_w,
                     "stroke-linejoin": "round",
                     "stroke-linecap": "round"})

    # --- Zoom inset panel (drawn before annotations so it sits in the right layer) ---
    # The 3-D origin (0,0,0) projects to the saddle region where the two
    # lobes meet — the ideal region for revealing fractal sheet structure.
    origin_poster = _transform(0, 0)
    zoom_info = _draw_zoom_inset(
        svg, ns, scaled_main, w_scale, h_scale,
        center_x, center_y, avail_w, avail_h, min_top,
        width_mm, attractor_color, origin_poster=origin_poster, theme=theme,
        scaled_extra=scaled_extra,
    )
    zoom_target_x, zoom_target_y = zoom_info["anno_target"]

    # --- Ultra-zoom panel (second-level zoom for deeper fractal structure) ---
    _draw_ultra_zoom_inset(
        svg, ns, scaled_main, w_scale, h_scale,
        zoom_info, width_mm, attractor_color, theme=theme,
        scaled_extra=scaled_extra,
    )

    # --- Pre-compute annotation layout positions ---
    # These are needed both to position the Poincaré panel (inline in the
    # annotation row) and to draw the annotation text below it.
    vis_ys = [p[1] for p in scaled_main]
    attractor_bottom = max(vis_ys)

    anno_sep_y = attractor_bottom + 10 * h_scale
    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # --- Poincaré section panel (inline, in annotation-row inter-column gap) ---
    # The panel sits in the horizontal gap between col2 and col3 text columns
    # at the same y-level as the annotation text — mirroring the inline-zoom
    # placement used by the logistic-map poster.
    combined_traj = traj_main + traj_extra
    poincare_pts = compute_poincare_section(combined_traj, z0=27.0, tol=0.5)
    _draw_poincare_inset(
        svg, ns, poincare_pts, w_scale, h_scale,
        anno_y, anno_sep_y, col2_cx, col3_cx,
        attractor_color, theme=theme,
    )

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale, opacity="0.5",
                       theme=theme)

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

    # 'Infinite Complexity' now points to the zoom inset panel centre
    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_butterfly_effect, be_target_x, be_target_y),
            (_annotation_two_wings, wing_target_x, wing_target_y),
            (_annotation_infinite_complexity, zoom_target_x, zoom_target_y),
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
                                traj_main=traj_main, traj_diverged=traj_div,
                                attractor_color=attractor_color,
                                diverged_color=diverged_color)
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
    parser.add_argument(
        "--zoom-multiplier", type=int, default=2, dest="zoom_multiplier",
        help="Extra integration multiplier for zoom panels (default: 2).",
    )
    parser.add_argument(
        "--angle-x", type=float, default=None, dest="angle_x",
        help=(
            "Rotation angle about the X-axis in radians "
            f"(default: {DEFAULT_ANGLE_X})."
        ),
    )
    parser.add_argument(
        "--angle-z", type=float, default=None, dest="angle_z",
        help=(
            "Rotation angle about the Z-axis in radians "
            f"(default: {DEFAULT_ANGLE_Z})."
        ),
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        steps=args.steps,
        zoom_multiplier=args.zoom_multiplier,
        width_mm=args.width,
        height_mm=args.height,
        designed_by=args.designed_by,
        designed_for=args.designed_for,
        theme=args.theme,
        angle_x=args.angle_x,
        angle_z=args.angle_z,
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
