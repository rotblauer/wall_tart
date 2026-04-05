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
    BG_COLOR,
    CALLOUT_LINE_STYLE,
    COLUMN_CENTERS,
    FOOTER_PRIMARY_COLOR,
    FOOTER_SECONDARY_COLOR,
    SERIF,
    TITLE_COLOR,
    _add_arrow_marker,
    _circle,
    _group,
    _line,
    _multiline_text,
    _polygon,
    _polyline,
    _rect,
    _svg_root,
    _text,
    add_common_poster_args,
    draw_annotation_row,
    draw_poster_border,
    draw_poster_footer,
    draw_poster_header,
    draw_row_separator,
    write_pdf,
    write_png,
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
        x = 0.4
        for _ in range(n_settle):
            x = r * x * (1.0 - x)
        for _ in range(n_plot):
            x = r * x * (1.0 - x)
            points.append((r, x))
    return points


# ---------------------------------------------------------------------------
# Poster-specific colour
# ---------------------------------------------------------------------------

DIAGRAM_COLOR = "#1C1C1C"  # near-black ink


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_period_doubling(parent, ns, target_x, target_y,
                                col_cx, anno_y, scale=1):
    """Annotation: the period-doubling cascade."""
    g = _group(parent, ns)

    arrow_y = anno_y - 8 * scale
    _line(g, ns, col_cx, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, col_cx, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    _text(g, ns, col_cx, anno_y + 2 * scale, "Period Doubling Cascade",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "As r increases, the single stable",
        "value splits into two, then four,",
        "then eight \u2014 each split arriving",
        "faster than the last. This cascade",
        "of period doublings is the road",
        "from order to chaos.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )
    return g


def _annotation_edge_of_chaos(parent, ns, target_x, target_y,
                               col_cx, anno_y, scale=1):
    """Annotation: the onset of chaos (Feigenbaum point)."""
    g = _group(parent, ns)

    arrow_y = anno_y - 8 * scale
    _line(g, ns, col_cx, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, col_cx, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    _text(g, ns, col_cx, anno_y + 2 * scale, "The Edge of Chaos",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    # Body text with r_inf value rendered via tspan for subscript
    body_style = {**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
                  "text-anchor": "middle"}
    body_y = anno_y + 9 * scale
    lh = 5 * scale

    attrib = {"x": str(col_cx), "y": str(body_y)}
    attrib.update(body_style)
    text_el = ET.SubElement(g, f"{{{ns}}}text", attrib=attrib)
    line0_tspan = ET.SubElement(
        text_el, f"{{{ns}}}tspan", attrib={"x": str(col_cx), "dy": "0"}
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
        g, ns, col_cx, body_y + lh,
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
                                  col_cx, anno_y, scale=1):
    """Annotation: the period-3 window amid chaos."""
    g = _group(parent, ns)

    arrow_y = anno_y - 8 * scale
    _line(g, ns, col_cx, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, col_cx, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    _text(g, ns, col_cx, anno_y + 2 * scale, "Windows of Order",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Deep in the chaotic regime, narrow",
        "windows of periodicity appear \u2014 the",
        "most famous at r \u2248 3.83, where a",
        "stable period-3 cycle emerges. Li &",
        "Yorke proved: \u2018period three implies",
        "chaos\u2019 \u2014 but also brief calm.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )
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

    # Build equation with subscript via tspan
    attrib = {"x": str(eq_x), "y": str(eq_y)}
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
# Poster composition
# ---------------------------------------------------------------------------

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

    w_scale = width_mm / 420
    h_scale = height_mm / 594

    _rect(svg, ns, 0, 0, width_mm, height_mm, fill=BG_COLOR)

    rule_y = draw_poster_header(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        title="The Logistic Map",
        subtitle="Order, chaos, and the road between",
        designed_by=designed_by,
        designed_for=designed_for,
    )

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
                fill=DIAGRAM_COLOR, opacity="0.25")

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
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale, opacity="0.5")

    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Arrow targets on the diagram
    pd_target = _transform(3.2, 0.8)
    ec_target = _transform(3.57, 0.5)
    wo_target = _transform(3.83, 0.5)

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_period_doubling, pd_target[0], pd_target[1]),
            (_annotation_edge_of_chaos, ec_target[0], ec_target[1]),
            (_annotation_windows_of_order, wo_target[0], wo_target[1]),
        ],
        w_scale,
    )

    # --- Second row: educational connections ---
    edu_group = _group(svg, ns, id="educational")

    row2_sep_y = anno_y + 55 * w_scale
    draw_row_separator(edu_group, ns, width_mm, row2_sep_y, w_scale, opacity="0.35")

    row2_y = row2_sep_y + 12 * w_scale

    _panel_equation(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_feigenbaum(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_population_biology(edu_group, ns, col3_cx, row2_y, w_scale)

    draw_poster_footer(
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
    )

    draw_poster_border(svg, ns, width_mm, height_mm, w_scale)

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

    write_poster(svg, args.format, args.output, dpi=args.dpi)
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
