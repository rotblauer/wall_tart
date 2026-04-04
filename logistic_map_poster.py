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
import sys
import xml.etree.ElementTree as ET


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
                     n_settle=300, n_plot=200):
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

    Returns
    -------
    list[tuple[float, float]]
        A list of (r, x) points for the bifurcation diagram.
    """
    points = []
    for i in range(n_r):
        r = r_min + (r_max - r_min) * i / max(n_r - 1, 1)
        x = 0.4  # deterministic starting value
        # Settle
        for _ in range(n_settle):
            x = r * x * (1.0 - x)
        # Collect
        for _ in range(n_plot):
            x = r * x * (1.0 - x)
            points.append((r, x))
    return points


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


def _annotation_period_doubling(parent, ns, target_x, target_y,
                                col_x, anno_y, scale=1):
    """Annotation: the period-doubling cascade."""
    g = _group(parent, ns)

    # Arrow from above the title up to the diagram target
    arrow_x = col_x + 25 * scale
    arrow_y = anno_y - 8 * scale
    _line(g, ns, arrow_x, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, arrow_x, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_x, anno_y + 2 * scale, "Period Doubling Cascade",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    # Body text
    lines = [
        "As r increases, the single stable",
        "value splits into two, then four,",
        "then eight \u2014 each split arriving",
        "faster than the last. This cascade",
        "of period doublings is the road",
        "from order to chaos.",
    ]
    _multiline_text(
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )
    return g


def _annotation_edge_of_chaos(parent, ns, target_x, target_y,
                               col_x, anno_y, scale=1):
    """Annotation: the onset of chaos (Feigenbaum point)."""
    g = _group(parent, ns)

    # Arrow from above the title up to the diagram target
    arrow_x = col_x + 25 * scale
    arrow_y = anno_y - 8 * scale
    _line(g, ns, arrow_x, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, arrow_x, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_x, anno_y + 2 * scale, "The Edge of Chaos",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    # Body text with r_inf value rendered via tspan for subscript
    body_style = {**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))}
    body_y = anno_y + 9 * scale
    lh = 5 * scale

    attrib = {"x": str(col_x), "y": str(body_y)}
    attrib.update(body_style)
    text_el = ET.SubElement(g, f"{{{ns}}}text", attrib=attrib)
    line0_tspan = ET.SubElement(
        text_el, f"{{{ns}}}tspan", attrib={"x": str(col_x), "dy": "0"}
    )
    line0_tspan.text = "At r"
    sub = ET.SubElement(
        line0_tspan,
        f"{{{ns}}}tspan",
        attrib={
            "dy": str(round(1.2 * scale, 2)),
            "font-size": str(round(2.5 * scale, 2)),
        },
    )
    sub.text = "\u221e"
    reset = ET.SubElement(
        line0_tspan,
        f"{{{ns}}}tspan",
        attrib={
            "dy": str(round(-1.2 * scale, 2)),
        },
    )
    reset.text = " \u2248 3.5699\u2026 the cascade"

    _multiline_text(
        g, ns, col_x, body_y + lh,
        [
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
                                  col_x, anno_y, scale=1):
    """Annotation: the period-3 window amid chaos."""
    g = _group(parent, ns)

    # Arrow from above the title up to the diagram target
    arrow_x = col_x + 25 * scale
    arrow_y = anno_y - 8 * scale
    _line(g, ns, arrow_x, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, arrow_x, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_x, anno_y + 2 * scale, "Windows of Order",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    # Body text
    lines = [
        "Deep in the chaotic regime, narrow",
        "windows of periodicity appear \u2014 the",
        "most famous at r \u2248 3.83, where a",
        "stable period-3 cycle emerges. Li &",
        "Yorke proved: \u2018period three implies",
        "chaos\u2019 \u2014 but also brief calm.",
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

def _panel_equation(parent, ns, col_x, anno_y, scale=1):
    """Panel: the logistic map equation and parameter ranges."""
    g = _group(parent, ns)

    _text(g, ns, col_x, anno_y + 2 * scale,
          "The Equation",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    lines = [
        "The logistic map is defined by a",
        "single recurrence relation:",
    ]
    _multiline_text(
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )

    # Equation in italic
    eq_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(4.5 * scale, 2)),
        "font-style": "italic",
    }
    eq_y = anno_y + 24 * scale

    # Build equation with subscript via tspan
    attrib = {"x": str(col_x + 4 * scale), "y": str(eq_y)}
    attrib.update(eq_style)
    eq_el = ET.SubElement(g, f"{{{ns}}}text", attrib=attrib)
    eq_el.text = "x"
    sub_n1 = ET.SubElement(
        eq_el, f"{{{ns}}}tspan",
        attrib={
            "dy": str(round(1.2 * scale, 2)),
            "font-size": str(round(3.0 * scale, 2)),
        },
    )
    sub_n1.text = "n+1"
    rest = ET.SubElement(
        eq_el, f"{{{ns}}}tspan",
        attrib={"dy": str(round(-1.2 * scale, 2))},
    )
    rest.text = " = r \u00b7 x"
    sub_n = ET.SubElement(
        rest, f"{{{ns}}}tspan",
        attrib={
            "dy": str(round(1.2 * scale, 2)),
            "font-size": str(round(3.0 * scale, 2)),
        },
    )
    sub_n.text = "n"
    paren = ET.SubElement(
        rest, f"{{{ns}}}tspan",
        attrib={"dy": str(round(-1.2 * scale, 2))},
    )
    paren.text = " (1 \u2212 x"
    sub_n2 = ET.SubElement(
        paren, f"{{{ns}}}tspan",
        attrib={
            "dy": str(round(1.2 * scale, 2)),
            "font-size": str(round(3.0 * scale, 2)),
        },
    )
    sub_n2.text = "n"
    close = ET.SubElement(
        paren, f"{{{ns}}}tspan",
        attrib={"dy": str(round(-1.2 * scale, 2))},
    )
    close.text = ")"

    # Parameter ranges
    param_y = eq_y + 10 * scale
    param_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(3.8 * scale, 2)),
    }
    _multiline_text(
        g, ns, col_x + 4 * scale, param_y,
        [
            "0 < x < 1  (population fraction)",
            "0 < r \u2264 4  (growth rate)",
        ],
        line_height=5 * scale,
        **param_style,
    )

    return g


def _panel_feigenbaum(parent, ns, col_x, anno_y, scale=1):
    """Panel: Feigenbaum's universal constant."""
    g = _group(parent, ns)

    _text(g, ns, col_x, anno_y + 2 * scale,
          "Feigenbaum\u2019s Constant",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

    lines = [
        "The ratio of successive bifurcation",
        "intervals converges to a universal",
        "constant discovered by Mitchell",
        "Feigenbaum in 1975:",
    ]
    _multiline_text(
        g, ns, col_x, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )

    # The constant in larger italic
    delta_y = anno_y + 34 * scale
    _text(g, ns, col_x + 4 * scale, delta_y,
          "\u03b4 = 4.669201\u2026",
          **{**ANNOTATION_STYLE,
             "font-size": str(round(5.5 * scale, 2)),
             "font-style": "italic"})

    _multiline_text(
        g, ns, col_x, delta_y + 8 * scale,
        [
            "This constant appears in every",
            "system that undergoes period",
            "doubling \u2014 it is universal.",
        ],
        line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2))},
    )

    return g


def _panel_population_biology(parent, ns, col_x, anno_y, scale=1):
    """Panel: the biological origins of the logistic map."""
    g = _group(parent, ns)

    _text(g, ns, col_x, anno_y + 2 * scale,
          "Population Biology",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR})

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
DIAGRAM_COLOR = "#1C1C1C"        # near-black ink
TITLE_COLOR = "#1C1C1C"          # dark title text
ACCENT_COLOR = "#8B0000"         # deep museum red
FOOTER_PRIMARY_COLOR = "#555555"  # footer primary text
FOOTER_SECONDARY_COLOR = "#777777"  # footer secondary text


def generate_poster(r_count=2000, width_mm=420, height_mm=594,
                    designed_by=None, designed_for=None):
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
        "The Logistic Map",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(round(16 * w_scale, 2)),
            "fill": TITLE_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, subtitle_y,
        "Order, chaos, and the road between",
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

    # --- Compute bifurcation data ---
    r_min, r_max = 2.5, 4.0
    n_settle = 300
    n_plot = 200
    data = bifurcation_data(r_min, r_max, n_r=r_count,
                            n_settle=n_settle, n_plot=n_plot)

    # --- Fit the diagram into the poster space ---
    min_top = rule_y + height_mm * 0.05
    anno_start_frac = 0.70
    max_bot = height_mm * anno_start_frac

    margin = width_mm * 0.10
    avail_w = width_mm - 2 * margin
    avail_h = max_bot - min_top

    # Map data coordinates to poster coordinates
    data_r_range = r_max - r_min if r_max != r_min else 1.0
    # x values are in [0, 1] for the logistic map
    data_x_min, data_x_max = 0.0, 1.0
    data_x_range = data_x_max - data_x_min

    def _transform(r_val, x_val):
        px = margin + (r_val - r_min) / data_r_range * avail_w
        # Flip y so that x=1 is at top and x=0 is at bottom
        py = min_top + avail_h - (x_val - data_x_min) / data_x_range * avail_h
        return (px, py)

    # --- Main bifurcation diagram ---
    diagram_group = _group(svg, ns, id="diagram")

    # Draw each point as a tiny circle for the bifurcation diagram
    dot_r = round(0.15 * w_scale, 3)
    for r_val, x_val in data:
        px, py = _transform(r_val, x_val)
        _circle(diagram_group, ns, round(px, 2), round(py, 2), dot_r,
                fill=DIAGRAM_COLOR, opacity="0.25")

    # --- Axis labels ---
    axis_style = {
        "font-family": "Georgia, 'Times New Roman', serif",
        "font-size": str(round(4 * w_scale, 2)),
        "fill": FOOTER_PRIMARY_COLOR,
        "font-style": "italic",
    }
    # x-axis label (r parameter)
    _text(svg, ns, width_mm / 2, max_bot + 7 * h_scale,
          "r (growth rate)",
          **{**axis_style, "text-anchor": "middle"})
    # y-axis label (x value) — rotated
    y_label = _text(svg, ns, margin - 8 * w_scale,
                    min_top + avail_h / 2, "x (population)",
                    **{**axis_style, "text-anchor": "middle"})
    y_label.set("transform",
                f"rotate(-90, {margin - 8 * w_scale}, {min_top + avail_h / 2})")

    # --- Annotations (below the diagram in a three-column layout) ---
    anno_group = _group(svg, ns, id="annotations")

    # Subtle separator line between diagram and annotations
    anno_sep_y = max_bot + 12 * h_scale
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

    # --- Arrow targets on the diagram ---
    # Period doubling → the first split around r ≈ 3.0
    pd_target = _transform(3.2, 0.8)

    # Edge of chaos → the Feigenbaum point r ≈ 3.5699
    ec_target = _transform(3.57, 0.5)

    # Windows of order → the period-3 window around r ≈ 3.83
    wo_target = _transform(3.83, 0.5)

    _annotation_period_doubling(anno_group, ns,
                                pd_target[0], pd_target[1],
                                col1_x, anno_y, w_scale)

    _annotation_edge_of_chaos(anno_group, ns,
                              ec_target[0], ec_target[1],
                              col2_x, anno_y, w_scale)

    _annotation_windows_of_order(anno_group, ns,
                                 wo_target[0], wo_target[1],
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

    _panel_equation(edu_group, ns, col1_x, row2_y, w_scale)
    _panel_feigenbaum(edu_group, ns, col2_x, row2_y, w_scale)
    _panel_population_biology(edu_group, ns, col3_x, row2_y, w_scale)

    # --- Footer ---
    footer_y = height_mm - 18 * h_scale
    footer_font = round(4 * w_scale, 2)
    footer_font_sm = round(3.5 * w_scale, 2)

    _text(
        svg, ns, width_mm / 2, footer_y,
        "Robert May popularised this map in 1976, "
        "revealing chaos in the simplest population model.",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(footer_font),
            "fill": FOOTER_PRIMARY_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, footer_y + 6 * h_scale,
        f"Generated with {r_count:,} r-samples  "
        f"\u00b7  r \u2208 [{r_min}, {r_max}]  "
        f"\u00b7  {n_settle:,} settle + {n_plot:,} plot iterations per sample",
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


def write_png(svg_root, filepath, dpi=150):
    """Write the poster as PNG via cairosvg (must be installed).

    The pixel dimensions are derived from the SVG's declared width/height and
    the requested *dpi* so that the raster output faithfully represents the
    vector layout at the chosen resolution.
    """
    try:
        import cairosvg
    except ImportError:
        print(
            "Error: 'cairosvg' is required for PNG output.\n"
            "Install it with:  pip install cairosvg",
            file=sys.stderr,
        )
        sys.exit(1)

    # Render SVG string → PNG at the requested DPI
    svg_bytes = ET.tostring(svg_root, encoding="unicode", xml_declaration=True)
    cairosvg.svg2png(bytestring=svg_bytes.encode("utf-8"), write_to=filepath, dpi=dpi)


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
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: logistic_map_poster.<format>).",
    )
    parser.add_argument(
        "--format", type=str, choices=["svg", "pdf", "png"], default="svg",
        help="Output format (default: svg).",
    )
    parser.add_argument(
        "--dpi", type=int, default=150,
        help="Resolution for PNG output in dots per inch (default: 150).",
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
        args.output = f"logistic_map_poster.{args.format}"

    print(f"Generating Logistic Map poster (r_count={args.r_count}) \u2026")
    svg = generate_poster(
        r_count=args.r_count,
        width_mm=args.width,
        height_mm=args.height,
        designed_by=args.designed_by,
        designed_for=args.designed_for,
    )

    if args.format == "pdf":
        write_pdf(svg, args.output)
    elif args.format == "png":
        write_png(svg, args.output, dpi=args.dpi)
    else:
        write_svg(svg, args.output)

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
