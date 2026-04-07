#!/usr/bin/env python3
"""
Logistic Map Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of the
Logistic Map — the famous bifurcation diagram that reveals how a simple
deterministic rule can produce period doubling, chaos, and surprising
windows of order.

Usage:
    python logistic_map_poster.py [OPTIONS]

Options:
    --r-count N          Number of r-parameter samples (default: 2000)
    --output FILE        Output filename (default: logistic_map_poster.svg)
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
    _line,
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
    get_theme,
    ProgressReporter,
    run_poster_main,
    write_poster,
    write_svg,
)


# ---------------------------------------------------------------------------
# Logistic map helpers
# ---------------------------------------------------------------------------

def logistic_iterate(x0, r, n_iterations):
    """Iterate the logistic map x_{n+1} = r * x_n * (1 - x_n).

    Parameters
    ----------
    x0 : float
        Initial population value (0 < x0 < 1).
    r : float
        Growth-rate parameter.
    n_iterations : int
        Number of iterations to run.

    Returns
    -------
    list[float]
        Sequence of x values of length *n_iterations* + 1 (including x0).
    """
    xs = [x0]
    x = x0
    for _ in range(n_iterations):
        x = r * x * (1.0 - x)
        xs.append(x)
    return xs


def bifurcation_data(r_min=2.5, r_max=4.0, n_r=2000,
                     n_settle=300, n_plot=200, progress=None):
    """Compute the bifurcation diagram of the logistic map.

    For each of *n_r* evenly spaced values of *r* in [r_min, r_max],
    iterate the logistic map to steady state (discarding the first
    *n_settle* iterates) and collect the subsequent *n_plot* values.

    Parameters
    ----------
    r_min, r_max : float
        Range of the growth-rate parameter.
    n_r : int
        Number of r samples (horizontal resolution).
    n_settle : int
        Transient iterations to discard before collecting.
    n_plot : int
        Number of steady-state values to record per r.
    progress : ProgressReporter or None
        Optional progress reporter updated once per r-value.

    Returns
    -------
    list[tuple[float, float]]
        A list of (r, x) points for the bifurcation diagram.
    """
    points = []
    for i in range(n_r):
        r = r_min + (r_max - r_min) * i / max(n_r - 1, 1)
        x = 0.4
        for _ in range(n_settle):
            x = r * x * (1.0 - x)
        for _ in range(n_plot):
            x = r * x * (1.0 - x)
            points.append((r, x))
        if progress is not None:
            progress.update()
    return points


# ---------------------------------------------------------------------------
# Poster-specific colour
# ---------------------------------------------------------------------------

DIAGRAM_COLOR = "#1C1C1C"  # near-black ink


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_period_doubling(parent, ns, target_x, target_y,
                                col_cx, anno_y, scale=1, theme=None):
    """Annotation: the period-doubling cascade."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Period Doubling Cascade", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "As r increases, the single stable",
        "value splits into two, then four,",
        "then eight \u2014 each split arriving",
        "faster than the last. This cascade",
        "of period doublings is the road",
        "from order to chaos.",
    ], scale, theme=theme)
    return g


def _annotation_edge_of_chaos(parent, ns, target_x, target_y,
                               col_cx, anno_y, scale=1, theme=None):
    """Annotation: the onset of chaos (Feigenbaum point)."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "The Edge of Chaos", scale, theme=theme)

    body_style = {**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
                  "text-anchor": "middle"}
    body_y = anno_y + 9 * scale
    lh = 5 * scale

    _multiline_text(
        g, ns, col_cx, body_y,
        [
            "At r \u221e \u2248 3.5699\u2026 the cascade",
            "converges. Beyond this threshold",
            "the system becomes unpredictable:",
            "no finite period remains stable.",
            "This is the exact boundary where",
            "determinism meets chaos.",
        ],
        line_height=lh,
        **body_style,
    )
    return g


def _annotation_windows_of_order(parent, ns, target_x, target_y,
                                  col_cx, anno_y, scale=1, theme=None):
    """Annotation: the period-3 window amid chaos."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Windows of Order", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Deep in the chaotic regime, narrow",
        "windows of periodicity appear \u2014 the",
        "most famous at r \u2248 3.83, where a",
        "stable period-3 cycle emerges. Li &",
        "Yorke proved: \u2018period three implies",
        "chaos\u2019 \u2014 but also brief calm.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_equation(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the logistic map equation and parameter ranges."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Equation",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The logistic map is defined by a",
        "single recurrence relation:",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Equation in italic — left-anchored at col_cx - 24*scale for visual centering
    eq_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(4.5 * scale, 2)),
        "font-style": "italic",
    }
    eq_y = anno_y + 24 * scale
    eq_x = col_cx - 24 * scale

    # Build equation using tspan dy offsets for subscripts
    # x_{n+1} = r · x_n (1 − x_n)
    base_size = round(4.5 * scale, 2)
    sub_size = round(3.4 * scale, 2)
    sub_dy = round(1.8 * scale, 2)
    attrib = {"x": str(eq_x), "y": str(eq_y)}
    attrib.update(eq_style)
    eq_el = ET.SubElement(g, f"{{{ns}}}text", attrib=attrib)
    for txt, dy, fs in [
        ("x",              None,     None),
        ("n+1",            sub_dy,   str(sub_size)),
        (" = r \u00b7 x", -sub_dy,   str(base_size)),
        ("n",              sub_dy,   str(sub_size)),
        ("(1 \u2212 x",   -sub_dy,   str(base_size)),
        ("n",              sub_dy,   str(sub_size)),
        (")",             -sub_dy,   str(base_size)),
    ]:
        ta = {}
        if dy is not None:
            ta["dy"] = str(dy)
        if fs is not None:
            ta["font-size"] = fs
        ET.SubElement(eq_el, f"{{{ns}}}tspan", attrib=ta).text = txt

    param_y = eq_y + 10 * scale
    param_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(3.8 * scale, 2)),
    }
    _multiline_text(
        g, ns, eq_x, param_y,
        [
            "0 < x < 1  (population fraction)",
            "0 < r \u2264 4  (growth rate)",
        ],
        line_height=5 * scale,
        **param_style,
    )

    return g


def _panel_feigenbaum(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Feigenbaum's universal constant."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Feigenbaum\u2019s Constant",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The ratio of successive bifurcation",
        "intervals converges to a universal",
        "constant discovered by Mitchell",
        "Feigenbaum in 1975:",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    delta_y = anno_y + 34 * scale
    _text(g, ns, col_cx, delta_y,
          "\u03b4 = 4.669201\u2026",
          **{**ANNOTATION_STYLE,
             "font-size": str(round(5.5 * scale, 2)),
             "font-style": "italic",
             "text-anchor": "middle"})

    _multiline_text(
        g, ns, col_cx, delta_y + 8 * scale,
        [
            "This constant appears in every",
            "system that undergoes period",
            "doubling \u2014 it is universal.",
        ],
        line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_population_biology(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the biological origins of the logistic map."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Population Biology",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "In 1976 the biologist Robert May",
        "showed that this simple model of",
        "population growth \u2014 where next",
        "year\u2019s population depends on this",
        "year\u2019s \u2014 can produce wildly erratic",
        "behaviour. A perfectly deterministic",
        "rule generates dynamics that look",
        "random, challenging the assumption",
        "that complex behaviour requires",
        "complex causes.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


# ---------------------------------------------------------------------------
# Zoom inset panel for logistic map
# ---------------------------------------------------------------------------

def _draw_inline_zoom(svg, ns, panel_cx, panel_cy, panel_w, panel_h,
                      src_r_min, src_r_max, src_x_min, src_x_max,
                      main_transform_fn, diagram_color, label,
                      clip_id, w_scale, h_scale,
                      line_stop_y=None,
                      progress=None, theme=None):
    """Draw an inline zoom panel in the inter-column gap beside annotation text.

    The panel is centred at (*panel_cx*, *panel_cy*).  A small bounding
    box is drawn on the main diagram at the source region, and a single
    delicate dashed line descends from the bottom-centre of that box.  If
    *line_stop_y* is supplied the line terminates there (e.g. at the
    annotation separator) so that it never overlaps the annotation text
    below.  A small filled circle marks the terminus of the line.

    Parameters
    ----------
    svg : Element
        Root SVG element.
    panel_cx, panel_cy : float
        Centre of the zoom panel (poster coordinates).
    panel_w, panel_h : float
        Width and height of the zoom panel.
    src_r_min, src_r_max : float
        Source r-parameter range to zoom into.
    src_x_min, src_x_max : float
        Source x-value range to zoom into.
    main_transform_fn : callable
        The ``_transform(r, x) -> (px, py)`` closure from
        ``generate_poster`` that maps data coordinates to poster
        coordinates on the main diagram.
    diagram_color : str
        Colour for the bifurcation dots.
    label : str
        Text label drawn at the bottom of the zoom panel.
    clip_id : str
        Unique id for the SVG ``<clipPath>`` element.
    w_scale, h_scale : float
        Poster scaling factors.
    line_stop_y : float or None
        If given, the dashed leader line ends at this y-coordinate instead
        of continuing all the way to the zoom panel top.  Pass
        ``anno_sep_y`` to keep the line entirely within the diagram area.
    progress : ProgressReporter or None
        Optional progress reporter.
    theme : str or None
        Poster theme name.

    Returns
    -------
    Element
        The zoom group element.
    """
    t = get_theme(theme)
    border_color = t["border_color"]
    bg_color = t["bg_color"]

    # Panel top-left from centre
    panel_x = panel_cx - panel_w / 2
    panel_y = panel_cy - panel_h / 2

    # --- Map source bounds to main diagram coordinates ---
    src_tl_x, src_tl_y = main_transform_fn(src_r_min, src_x_max)   # top-left
    src_br_x, src_br_y = main_transform_fn(src_r_max, src_x_min)   # bottom-right
    src_w = src_br_x - src_tl_x
    src_h = src_br_y - src_tl_y
    src_cx = src_tl_x + src_w / 2

    # --- Add clipPath to <defs> ---
    defs_el = svg.find(f"{{{ns}}}defs")
    if defs_el is None:
        defs_el = ET.SubElement(svg, f"{{{ns}}}defs")
    clip_path_el = ET.SubElement(defs_el, f"{{{ns}}}clipPath",
                                  attrib={"id": clip_id})
    ET.SubElement(clip_path_el, f"{{{ns}}}rect", attrib={
        "x": str(round(panel_x, 4)),
        "y": str(round(panel_y, 4)),
        "width": str(round(panel_w, 4)),
        "height": str(round(panel_h, 4)),
    })

    # --- Group for all zoom elements ---
    zoom_group = _group(svg, ns, id=clip_id.replace("_clip", ""))

    # --- Source bounding box on the main diagram ---
    _rect(zoom_group, ns, src_tl_x, src_tl_y, src_w, src_h,
          fill=border_color,
          **{"fill-opacity": "0.07",
             "stroke": border_color,
             "stroke-width": str(round(0.35 * w_scale, 3))})

    # --- Dashed leader line: bottom-centre of source box → stop point ---
    # When line_stop_y is provided the line terminates there (at the
    # annotation separator) so it never runs through the annotation text.
    line_end_y = line_stop_y if line_stop_y is not None else panel_y
    line_end_x = panel_cx
    _line(zoom_group, ns,
          src_cx, src_br_y,
          line_end_x, line_end_y,
          **{"stroke": border_color,
             "stroke-width": str(round(0.25 * w_scale, 3)),
             "stroke-dasharray": "1.5,1.5",
             "opacity": "0.5"})
    # Small filled circle at the terminus so the viewer can follow the chain
    # from the diagram down to the zoom panel sitting just below.
    _circle(zoom_group, ns,
            round(line_end_x, 2), round(line_end_y, 2),
            round(0.8 * w_scale, 3),
            fill=border_color, opacity="0.45")

    # --- Panel background ---
    _rect(zoom_group, ns, panel_x, panel_y, panel_w, panel_h,
          fill=bg_color, stroke="none", opacity="0.92")

    # --- Compute high-res bifurcation data for the zoom region ---
    zoom_data = bifurcation_data(
        r_min=src_r_min, r_max=src_r_max,
        n_r=600, n_settle=400, n_plot=150,
        progress=progress,
    )

    # --- Draw zoom data inside the clipped panel ---
    zoom_lines_g = _group(zoom_group, ns, **{"clip-path": f"url(#{clip_id})"})

    zoom_r_range = src_r_max - src_r_min if src_r_max != src_r_min else 1.0
    zoom_x_range = src_x_max - src_x_min if src_x_max != src_x_min else 1.0

    dot_r = round(0.15 * w_scale, 3)
    for r_val, x_val in zoom_data:
        px = panel_x + (r_val - src_r_min) / zoom_r_range * panel_w
        py = panel_y + panel_h - (x_val - src_x_min) / zoom_x_range * panel_h
        _circle(zoom_lines_g, ns, round(px, 2), round(py, 2), dot_r,
                fill=diagram_color, opacity="0.20")

    # --- Panel border ---
    _rect(zoom_group, ns, panel_x, panel_y, panel_w, panel_h,
          fill="none", stroke=border_color,
          **{"stroke-width": str(round(0.5 * w_scale, 3))})

    # --- Label below zoom panel (outside the border, never inside the plot) ---
    _text(zoom_group, ns, panel_cx,
          panel_y + panel_h + 3.5 * h_scale,
          label,
          **{**ANNOTATION_STYLE,
             "fill": border_color,
             "font-size": str(round(2.8 * w_scale, 2)),
             "text-anchor": "middle",
             "opacity": "0.65"})

    return zoom_group


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

def generate_poster(r_count=2000, width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None, verbose=True):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    r_count : int
        Number of r-parameter samples for horizontal resolution.
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
    diagram_color = t["content_primary"]

    sc = build_poster_scaffold(
        title="The Logistic Map",
        subtitle="Order, chaos, and the road between",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Compute bifurcation data ---
    r_min, r_max = 2.5, 4.0
    n_settle = 300
    n_plot = 200
    _p = ProgressReporter(r_count, "Logistic: bifurcation") if verbose else None
    data = bifurcation_data(r_min, r_max, n_r=r_count,
                            n_settle=n_settle, n_plot=n_plot, progress=_p)
    if _p:
        _p.done()

    # --- Fit the diagram into the poster space ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    margin, avail_w, avail_h = ca["margin"], ca["avail_w"], ca["avail_h"]

    data_r_range = r_max - r_min if r_max != r_min else 1.0
    data_x_min, data_x_max = 0.0, 1.0
    data_x_range = data_x_max - data_x_min

    def _transform(r_val, x_val):
        px = margin + (r_val - r_min) / data_r_range * avail_w
        py = min_top + avail_h - (x_val - data_x_min) / data_x_range * avail_h
        return (px, py)

    # --- Main bifurcation diagram ---
    diagram_group = _group(svg, ns, id="diagram")

    dot_r = round(0.15 * w_scale, 3)
    for r_val, x_val in data:
        px, py = _transform(r_val, x_val)
        _circle(diagram_group, ns, round(px, 2), round(py, 2), dot_r,
                fill=diagram_color, opacity="0.25")

    # --- Axis labels ---
    axis_style = {
        "font-family": SERIF,
        "font-size": str(round(4 * w_scale, 2)),
        "fill": FOOTER_PRIMARY_COLOR,
        "font-style": "italic",
    }
    _text(svg, ns, width_mm / 2, max_bot + 7 * h_scale,
          "r (growth rate)",
          **{**axis_style, "text-anchor": "middle"})
    y_label = _text(svg, ns, margin - 8 * w_scale,
                    min_top + avail_h / 2, "x (population)",
                    **{**axis_style, "text-anchor": "middle"})
    y_label.set("transform",
                f"rotate(-90, {margin - 8 * w_scale}, {min_top + avail_h / 2})")

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale, opacity="0.5",
                       theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # --- Inline zoom panels: placed in the inter-column gaps beside annotation text ---
    # Each panel sits in the horizontal space between adjacent columns so the
    # annotation text is not displaced vertically and fits on the poster.
    #
    # Sizing is computed dynamically from the available inter-column gap so the
    # layout works at any poster dimension, not just A2.
    col_gap = col2_cx - col1_cx   # = col3_cx - col2_cx for the symmetric 3-col grid
    # Use ~47% of the gap width — leaves ~26% (~7 mm at A2) clearance on each side
    panel_w = col_gap * 0.47
    # Height: ~58% of width gives a natural 5:3 landscape ratio
    panel_h = panel_w * 0.58
    # Centre the panel just above the annotation-text midline so the caption
    # that hangs below the border still clears the row-2 separator.
    panel_cy = anno_y + panel_h / 2 + 1 * h_scale

    # Edge of Chaos: centred in the gap between col1 and col2 (~136mm at A2)
    panel_cx_ec = (col1_cx + col2_cx) / 2
    # Period-3 Window: centred in the gap between col2 and col3 (~284mm at A2)
    panel_cx_wo = (col2_cx + col3_cx) / 2

    # Zoom 1: Edge of Chaos (left of col2 text)
    _pz1 = ProgressReporter(600, "Logistic: zoom 1") if verbose else None
    _draw_inline_zoom(
        svg, ns,
        panel_cx=panel_cx_ec, panel_cy=panel_cy,
        panel_w=panel_w, panel_h=panel_h,
        src_r_min=3.54, src_r_max=3.59,
        src_x_min=0.8, src_x_max=0.9,
        main_transform_fn=_transform,
        diagram_color=diagram_color,
        label="Onset of Chaos",
        clip_id="zoom1_clip",
        w_scale=w_scale, h_scale=h_scale,
        line_stop_y=anno_sep_y,
        progress=_pz1, theme=theme,
    )
    if _pz1:
        _pz1.done()

    # Zoom 2: Period-3 Window (left of col3 text)
    _pz2 = ProgressReporter(600, "Logistic: zoom 2") if verbose else None
    _draw_inline_zoom(
        svg, ns,
        panel_cx=panel_cx_wo, panel_cy=panel_cy,
        panel_w=panel_w, panel_h=panel_h,
        src_r_min=3.828, src_r_max=3.856,
        src_x_min=0.4, src_x_max=0.55,
        main_transform_fn=_transform,
        diagram_color=diagram_color,
        label="Period-3 Window",
        clip_id="zoom2_clip",
        w_scale=w_scale, h_scale=h_scale,
        line_stop_y=anno_sep_y,
        progress=_pz2, theme=theme,
    )
    if _pz2:
        _pz2.done()

    # All annotation arrows point upward to their r-value on the main diagram.
    # The zoom panels are already visually connected to the diagram via the
    # source-region highlight box, so no extra cross-text arrow is needed.
    pd_target = _transform(3.2, 0.8)
    ec_target = _transform(3.5699, 0.5)   # Feigenbaum point (onset of chaos)
    wo_target = _transform(3.83, 0.5)     # Period-3 window

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_period_doubling, pd_target[0], pd_target[1]),
            (_annotation_edge_of_chaos, ec_target[0], ec_target[1]),
            (_annotation_windows_of_order, wo_target[0], wo_target[1]),
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

    _panel_equation(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_feigenbaum(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_population_biology(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Robert May popularised this map in 1976, "
            "revealing chaos in the simplest population model."
        ),
        secondary_line=(
            f"Generated with {r_count:,} r-samples  "
            f"\u00b7  r \u2208 [{r_min}, {r_max}]  "
            f"\u00b7  {n_settle:,} settle + {n_plot:,} plot iterations per sample"
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
        description="Generate an annotated Logistic Map bifurcation poster.",
    )
    parser.add_argument(
        "--r-count", type=int, default=2000, dest="r_count",
        help="Number of r-parameter samples (default: 2000). Higher = finer.",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        r_count=args.r_count,
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
        filename_prefix="logistic_map_poster",
        poster_label=f"Logistic Map poster (r_count={args.r_count})",
        argv=argv,
    )


if __name__ == "__main__":
    main()
