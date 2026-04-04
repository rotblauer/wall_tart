#!/usr/bin/env python3
"""
Sierpiński Triangle Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of the
Sierpiński Triangle fractal. Designed for large-format printing (A2+).

Usage:
    python sierpinski_poster.py [OPTIONS]

Options:
    --depth N        Recursion depth (default: 7)
    --output FILE    Output filename (default: sierpinski_poster.svg)
    --format FMT     Output format: svg or pdf (default: svg)
    --width MM       Poster width in mm (default: 420, A2 width)
    --height MM      Poster height in mm (default: 594, A2 height)
"""

import argparse
import math
import sys
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def equilateral_triangle_vertices(cx, cy, side_length):
    """Return three vertices of an equilateral triangle centred at (cx, cy)."""
    h = side_length * math.sqrt(3) / 2
    top = (cx, cy - 2 * h / 3)
    bottom_left = (cx - side_length / 2, cy + h / 3)
    bottom_right = (cx + side_length / 2, cy + h / 3)
    return [top, bottom_left, bottom_right]


def midpoint(p1, p2):
    """Return the midpoint between two 2-D points."""
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


# ---------------------------------------------------------------------------
# Sierpiński triangle – iterative filled-triangle collector
# ---------------------------------------------------------------------------

def sierpinski_triangles(vertices, depth):
    """Yield filled triangle vertex-lists for the Sierpiński fractal.

    Uses an iterative stack instead of call-stack recursion so that deep
    depths do not hit Python's recursion limit.
    """
    stack = [(vertices, depth)]
    while stack:
        tri, d = stack.pop()
        if d == 0:
            yield tri
        else:
            a, b, c = tri
            ab = midpoint(a, b)
            bc = midpoint(b, c)
            ac = midpoint(a, c)
            stack.append(([a, ab, ac], d - 1))
            stack.append(([ab, b, bc], d - 1))
            stack.append(([ac, bc, c], d - 1))


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
            "fill": "#FFD700",
        },
    )
    return defs


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

ANNOTATION_STYLE = {
    "font-family": "Georgia, 'Times New Roman', serif",
    "fill": "#F0E6D3",
}

CALLOUT_LINE_STYLE = {
    "stroke": "#FFD700",
    "stroke-width": "0.5",
    "marker-end": "url(#arrowhead)",
}


def _annotation_self_similarity(parent, ns, target_x, target_y, width_mm):
    """Annotation: self-similarity callout."""
    box_x = width_mm * 0.62
    box_y = target_y - 30

    g = _group(parent, ns)
    _line(g, ns, box_x - 2, box_y + 4, target_x, target_y,
          **CALLOUT_LINE_STYLE)

    lines = [
        "Self-Similarity",
        "Every smaller triangle is an",
        "exact copy of the whole shape.",
        "Zoom in anywhere — you'll find",
        "the same pattern repeated forever.",
    ]
    _multiline_text(
        g, ns, box_x, box_y,
        lines, line_height=5.5,
        **{**ANNOTATION_STYLE, "font-size": "4.5"},
    )
    # Title line is bold
    return g


def _annotation_recursion(parent, ns, target_x, target_y, width_mm):
    """Annotation: recursion callout with step diagram."""
    box_x = width_mm * 0.05
    box_y = target_y + 10

    g = _group(parent, ns)
    _line(g, ns, box_x + 50, box_y - 2, target_x, target_y,
          **CALLOUT_LINE_STYLE)

    lines = [
        "Recursion",
        "Start with one triangle. Remove",
        "the centre to get three smaller",
        "copies. Repeat on each copy —",
        "forever. That's recursion!",
    ]
    _multiline_text(
        g, ns, box_x, box_y,
        lines, line_height=5.5,
        **{**ANNOTATION_STYLE, "font-size": "4.5"},
    )

    # Mini step diagram: 3 tiny triangles showing depth 0, 1, 2
    mini_y = box_y + 35
    for i, d in enumerate([0, 1, 2]):
        mini_cx = box_x + 12 + i * 22
        side = 14
        verts = equilateral_triangle_vertices(mini_cx, mini_y, side)
        for tri in sierpinski_triangles(verts, d):
            _polygon(g, ns, tri, fill="#FFD700", opacity="0.85")
        _text(g, ns, mini_cx - 4, mini_y + 13, f"depth {d}",
              **{**ANNOTATION_STYLE, "font-size": "3"})
        if i < 2:
            _text(g, ns, mini_cx + 8, mini_y, "\u2192",
                  **{**ANNOTATION_STYLE, "font-size": "5"})

    return g


def _annotation_dimension(parent, ns, target_x, target_y, width_mm):
    """Annotation: fractional (Hausdorff) dimension callout."""
    box_x = width_mm * 0.62
    box_y = target_y + 10

    g = _group(parent, ns)
    _line(g, ns, box_x - 2, box_y - 2, target_x, target_y,
          **CALLOUT_LINE_STYLE)

    dim_val = f"{math.log(3) / math.log(2):.4f}"
    lines = [
        "Fractional Dimension",
        "A line is 1-D. A square is 2-D.",
        f"This shape is {dim_val}-D!",
        "It's called the Hausdorff dimension.",
        "Not quite a line, not quite a plane —",
        "somewhere magically in between.",
    ]
    _multiline_text(
        g, ns, box_x, box_y,
        lines, line_height=5.5,
        **{**ANNOTATION_STYLE, "font-size": "4.5"},
    )
    return g


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

# Colour palette – dark museum aesthetic
BG_COLOR = "#1A1A2E"
TRIANGLE_COLOR = "#00D4FF"
TITLE_COLOR = "#F0E6D3"
ACCENT_COLOR = "#FFD700"


def generate_poster(depth=7, width_mm=420, height_mm=594):
    """Build and return the full poster as an ElementTree SVG root."""
    svg, ns = _svg_root(width_mm, height_mm)

    # Background
    _rect(svg, ns, 0, 0, width_mm, height_mm, fill=BG_COLOR)

    # Title
    _text(
        svg, ns, width_mm / 2, 30,
        "The Sierpi\u0144ski Triangle",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": "16",
            "fill": TITLE_COLOR,
            "text-anchor": "middle",
        },
    )
    # Subtitle
    _text(
        svg, ns, width_mm / 2, 40,
        "A fractal of infinite complexity from a simple rule",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": "6",
            "fill": ACCENT_COLOR,
            "text-anchor": "middle",
            "opacity": "0.8",
        },
    )

    # Arrow marker for callouts
    _add_arrow_marker(svg, ns)

    # --- Main fractal ---
    margin = width_mm * 0.12
    tri_side = width_mm - 2 * margin
    tri_cx = width_mm / 2
    tri_cy = height_mm * 0.46
    vertices = equilateral_triangle_vertices(tri_cx, tri_cy, tri_side)

    fractal_group = _group(svg, ns, id="fractal")
    for tri in sierpinski_triangles(vertices, depth):
        _polygon(fractal_group, ns, tri,
                 fill=TRIANGLE_COLOR, stroke="none", opacity="0.92")

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    # Self-similarity arrow → top sub-triangle
    ss_target_x = vertices[0][0] + tri_side * 0.18
    ss_target_y = vertices[0][1] + tri_side * 0.22
    _annotation_self_similarity(anno_group, ns, ss_target_x, ss_target_y,
                                width_mm)

    # Recursion arrow → bottom-left area
    rec_target_x = vertices[1][0] + tri_side * 0.12
    rec_target_y = vertices[1][1] - tri_side * 0.10
    _annotation_recursion(anno_group, ns, rec_target_x, rec_target_y,
                          width_mm)

    # Dimension arrow → bottom-right area
    dim_target_x = vertices[2][0] - tri_side * 0.12
    dim_target_y = vertices[2][1] - tri_side * 0.10
    _annotation_dimension(anno_group, ns, dim_target_x, dim_target_y,
                          width_mm)

    # --- Footer ---
    footer_y = height_mm - 18
    _text(
        svg, ns, width_mm / 2, footer_y,
        "Wac\u0142aw Sierpi\u0144ski first described this fractal in 1915.",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": "4",
            "fill": TITLE_COLOR,
            "text-anchor": "middle",
            "opacity": "0.6",
        },
    )
    _text(
        svg, ns, width_mm / 2, footer_y + 6,
        f"Generated at depth {depth}  \u00b7  {3**depth:,} triangles",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": "3.5",
            "fill": TITLE_COLOR,
            "text-anchor": "middle",
            "opacity": "0.5",
        },
    )

    # Decorative border
    _rect(
        svg, ns, 4, 4, width_mm - 8, height_mm - 8,
        fill="none", stroke=ACCENT_COLOR,
        **{"stroke-width": "0.3", "opacity": "0.3"},
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
        import cairosvg  # noqa: F811
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
        description="Generate an annotated Sierpiński Triangle poster.",
    )
    parser.add_argument(
        "--depth", type=int, default=7,
        help="Recursion depth (default: 7). Higher = more detail.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: sierpinski_poster.<format>).",
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
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.output is None:
        args.output = f"sierpinski_poster.{args.format}"

    print(f"Generating Sierpiński Triangle poster (depth={args.depth}) …")
    svg = generate_poster(
        depth=args.depth,
        width_mm=args.width,
        height_mm=args.height,
    )

    if args.format == "pdf":
        write_pdf(svg, args.output)
    else:
        write_svg(svg, args.output)

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
