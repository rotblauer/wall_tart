#!/usr/bin/env python3
"""
Shared utilities for the wall_tart poster generators.

Provides SVG helpers, style constants, output helpers, layout helpers,
no-crossing annotation utilities, and a common CLI argument builder that
are identical across the Sierpiński, Lorenz, and Logistic Map posters.
"""

import sys
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------

BG_COLOR = "#FFFEF8"                # warm ivory paper
ACCENT_COLOR = "#8B0000"            # deep museum red
TITLE_COLOR = "#1C1C1C"             # dark title text
FOOTER_PRIMARY_COLOR = "#555555"    # footer primary text
FOOTER_SECONDARY_COLOR = "#777777"  # footer secondary text

SERIF = "Georgia, 'Times New Roman', serif"

ANNOTATION_STYLE = {
    "font-family": SERIF,
    "fill": "#1C1C1C",
}

CALLOUT_LINE_STYLE = {
    "stroke": "#8B0000",
    "stroke-width": "0.5",
    "marker-end": "url(#arrowhead)",
}

# Column centres as fractions of poster width (left, centre, right)
COLUMN_CENTERS = (0.15, 0.50, 0.85)


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
# Layout helpers
# ---------------------------------------------------------------------------

def draw_poster_header(svg, ns, width_mm, height_mm, w_scale, h_scale,
                       title, subtitle, designed_by=None, designed_for=None):
    """Draw title, subtitle, rule, and optional inline credits.

    Returns rule_y so the caller can place content below the rule.
    """
    title_y = height_mm * 0.047
    subtitle_y = height_mm * 0.064
    rule_y = height_mm * 0.074

    _text(
        svg, ns, width_mm / 2, title_y, title,
        **{
            "font-family": SERIF,
            "font-size": str(round(16 * w_scale, 2)),
            "fill": TITLE_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, subtitle_y, subtitle,
        **{
            "font-family": SERIF,
            "font-size": str(round(6 * w_scale, 2)),
            "fill": ACCENT_COLOR,
            "text-anchor": "middle",
        },
    )

    # Thin red rule beneath the header
    _line(
        svg, ns,
        width_mm * 0.15, rule_y,
        width_mm * 0.85, rule_y,
        stroke=ACCENT_COLOR,
        **{"stroke-width": str(round(0.4 * w_scale, 3))},
    )

    # Header credits flanking the rule
    header_credit_y = rule_y + 5 * h_scale
    header_credit_style = {
        "font-family": SERIF,
        "font-size": str(round(3.8 * w_scale, 2)),
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

    return rule_y


def draw_poster_footer(svg, ns, width_mm, height_mm, w_scale, h_scale,
                       primary_line, secondary_line,
                       designed_by=None, designed_for=None):
    """Draw footer text lines and optional credit.

    Returns footer_y (the y coordinate of the primary footer line).
    """
    footer_y = height_mm - 18 * h_scale
    footer_font = round(4 * w_scale, 2)
    footer_font_sm = round(3.5 * w_scale, 2)

    _text(
        svg, ns, width_mm / 2, footer_y, primary_line,
        **{
            "font-family": SERIF,
            "font-size": str(footer_font),
            "fill": FOOTER_PRIMARY_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, footer_y + 6 * h_scale, secondary_line,
        **{
            "font-family": SERIF,
            "font-size": str(footer_font_sm),
            "fill": FOOTER_SECONDARY_COLOR,
            "text-anchor": "middle",
        },
    )

    if designed_by or designed_for:
        parts = []
        if designed_by:
            parts.append(f"Designed by {designed_by}")
        if designed_for:
            parts.append(f"for {designed_for}")
        credit_text = " ".join(parts)
        _text(
            svg, ns, width_mm / 2, footer_y + 12 * h_scale, credit_text,
            **{
                "font-family": SERIF,
                "font-size": str(footer_font_sm),
                "fill": FOOTER_SECONDARY_COLOR,
                "font-style": "italic",
                "text-anchor": "middle",
            },
        )

    return footer_y


def draw_poster_border(svg, ns, width_mm, height_mm, w_scale):
    """Draw the decorative double border (outer + inner rect)."""
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


def draw_row_separator(parent, ns, width_mm, y, w_scale, opacity="0.5"):
    """Draw a full-width separator line at y."""
    _line(
        parent, ns,
        width_mm * 0.15, y,
        width_mm * 0.85, y,
        stroke=ACCENT_COLOR,
        **{"stroke-width": str(round(0.3 * w_scale, 3)), "opacity": opacity},
    )


# ---------------------------------------------------------------------------
# No-crossing annotation utilities
# ---------------------------------------------------------------------------

def assign_annotations_no_crossing(annotations):
    """Sort annotation descriptors so their arrows never cross.

    annotations: sequence of (callable, target_x, target_y) — one per column.

    Arrow lines go from (col_cx, arrow_origin_y) up to (target_x, target_y).
    When the left-to-right ordering of column centres matches the left-to-right
    ordering of target x-coordinates, the lines cannot intersect.

    Returns the annotations list sorted by target_x ascending.  Pass the i-th
    result to the i-th column (left → right).
    """
    return sorted(annotations, key=lambda a: a[1])


def draw_annotation_row(parent, ns, anno_y, col_centers, annotations, scale):
    """Draw annotation callouts in order, ensuring no arrows cross.

    col_centers: sorted list of 3 column-centre x values
    annotations: list of 3 (callable, target_x, target_y) tuples
    Each callable has signature: func(parent, ns, target_x, target_y, col_cx, anno_y, scale)
    """
    for (func, tx, ty), col_cx in zip(
        assign_annotations_no_crossing(annotations), col_centers
    ):
        func(parent, ns, tx, ty, col_cx, anno_y, scale)


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

    svg_bytes = ET.tostring(svg_root, encoding="unicode", xml_declaration=True)
    cairosvg.svg2png(bytestring=svg_bytes.encode("utf-8"), write_to=filepath, dpi=dpi)


def write_poster(svg_root, fmt, filepath, dpi=150):
    """Convenience dispatcher: call the right write_* based on fmt."""
    if fmt == "pdf":
        write_pdf(svg_root, filepath)
    elif fmt == "png":
        write_png(svg_root, filepath, dpi=dpi)
    else:
        write_svg(svg_root, filepath)


# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------

def add_common_poster_args(parser):
    """Add --output, --format, --dpi, --width, --height, --designed-by, --designed-for."""
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path.",
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
