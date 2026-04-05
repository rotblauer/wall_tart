#!/usr/bin/env python3
"""
Sierpiński Triangle Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF/PNG) of the
Sierpiński Triangle fractal. Designed for large-format printing (A2+).

Usage:
    python sierpinski_poster.py [OPTIONS]

Options:
    --depth N            Recursion depth (default: 7)
    --output FILE        Output filename (default: sierpinski_poster.svg)
    --format FMT         Output format: svg, pdf, or png (default: svg)
    --dpi N              Resolution for PNG output in dots per inch (default: 150)
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


def _annotation_self_similarity(parent, ns, target_x, target_y,
                                col_cx, anno_y, scale=1):
    """Annotation: self-similarity callout (below the fractal)."""
    g = _group(parent, ns)

    # Arrow from above the title up to the fractal target
    arrow_y = anno_y - 8 * scale
    _line(g, ns, col_cx, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, col_cx, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_cx, anno_y + 2 * scale, "Self-Similarity",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    # Body text
    lines = [
        "Every smaller triangle is an exact",
        "copy of the whole shape. Zoom in",
        "anywhere \u2014 the same pattern",
        "repeats at every scale, forever.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )
    return g


def _annotation_recursion(parent, ns, target_x, target_y,
                           col_cx, anno_y, scale=1):
    """Annotation: recursion callout with step diagram (below the fractal)."""
    g = _group(parent, ns)

    # Arrow from above the title up to the fractal target
    arrow_y = anno_y - 8 * scale
    _line(g, ns, col_cx, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, col_cx, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    # Title
    _text(g, ns, col_cx, anno_y + 2 * scale, "Recursion",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    # Body text
    lines = [
        "Start with one triangle. Remove the",
        "centre to get three smaller copies.",
        "Repeat on each copy \u2014 that\u2019s recursion!",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Mini step diagram: 3 tiny triangles showing depth 0, 1, 2 — centred at col_cx
    mini_y = anno_y + 32 * scale
    for i, d in enumerate([0, 1, 2]):
        mini_cx = col_cx + (-22 + i * 22) * scale
        side = 14 * scale
        verts = equilateral_triangle_vertices(mini_cx, mini_y, side)
        for tri in sierpinski_triangles(verts, d):
            _polygon(g, ns, tri, fill=TRIANGLE_COLOR, opacity="0.85")
        _text(g, ns, mini_cx, mini_y + 13 * scale, f"depth {d}",
              **{**ANNOTATION_STYLE, "font-size": str(round(3 * scale, 2)),
                 "text-anchor": "middle"})
        if i < 2:
            _text(g, ns, mini_cx + 8 * scale, mini_y, "\u2192",
                  **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2))})

    return g


def _annotation_dimension(parent, ns, target_x, target_y,
                           col_cx, anno_y, scale=1):
    """Annotation: fractional (Hausdorff) dimension callout (below fractal)."""
    g = _group(parent, ns)

    # Arrow from above the title up to the fractal target
    arrow_y = anno_y - 8 * scale
    _line(g, ns, col_cx, arrow_y, target_x, target_y,
          **CALLOUT_LINE_STYLE)
    _circle(g, ns, col_cx, arrow_y, 1 * scale, fill=ACCENT_COLOR)

    dim_val = f"{math.log(3) / math.log(2):.4f}"

    # Title
    _text(g, ns, col_cx, anno_y + 2 * scale, "Fractional Dimension",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    # Body text
    lines = [
        "A line is 1-D. A square is 2-D.",
        f"This fractal is {dim_val}-D!",
        "It\u2019s the Hausdorff dimension \u2014 not",
        "quite a line, not quite a plane,",
        "somewhere magically in between.",
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

def _panel_pascal(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Pascal\u2019s triangle mod 2 \u2192 Sierpi\u0144ski pattern."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Hidden in Pascal\u2019s Triangle",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Color the odd entries of Pascal\u2019s",
        "triangle and the Sierpi\u0144ski",
        "pattern emerges \u2014 a bridge between",
        "number theory and geometry.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Pascal's triangle mod 2 — rows of small squares, centred at col_cx
    cell = 3.2 * scale
    gap = 0.4 * scale
    step = cell + gap
    base_y = anno_y + 33 * scale
    center_x = col_cx
    num_rows = 8

    for n in range(num_rows):
        row_start_x = center_x - n * step / 2
        for k in range(n + 1):
            # C(n,k) is odd iff every bit of k is set in n (Kummer's theorem)
            is_odd = (n & k) == k
            rx = row_start_x + k * step
            ry = base_y + n * step
            fill = TRIANGLE_COLOR if is_odd else "none"
            opacity = "0.85" if is_odd else "0.15"
            _rect(g, ns, rx, ry, cell, cell,
                  fill=fill, stroke=TRIANGLE_COLOR,
                  **{"stroke-width": str(round(0.15 * scale, 3)),
                     "opacity": opacity})

    return g


def _panel_chaos_game(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the chaos game algorithm with dot demonstration."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale, "The Chaos Game",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Pick any starting point inside the",
        "triangle. Choose a random vertex \u2014",
        "jump halfway there. Repeat forever.",
        "The dots trace the Sierpi\u0144ski triangle!",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Small demonstration: chaos game scatter dots centred at col_cx
    tri_cx = col_cx
    tri_cy = anno_y + 48 * scale
    tri_side = 32 * scale
    demo_verts = equilateral_triangle_vertices(tri_cx, tri_cy, tri_side)

    # Faint outline triangle
    _polygon(g, ns, demo_verts, fill="none", stroke=TRIANGLE_COLOR,
             **{"stroke-width": str(round(0.2 * scale, 3)), "opacity": "0.2"})

    # Label vertices
    labels = ["A", "B", "C"]
    offsets = [(0, -3), (-4, 4), (4, 4)]
    for v, label, (dx, dy) in zip(demo_verts, labels, offsets):
        _text(g, ns, v[0] + dx * scale, v[1] + dy * scale, label,
              **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
                 "fill": ACCENT_COLOR, "text-anchor": "middle"})

    # Deterministic chaos game via LCG
    x = (demo_verts[0][0] + demo_verts[1][0]) / 2
    y = (demo_verts[0][1] + demo_verts[1][1]) / 2
    seed = 42
    dot_r = 0.3 * scale
    for i in range(210):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        vi = seed % 3
        vx, vy = demo_verts[vi]
        x = (x + vx) / 2
        y = (y + vy) / 2
        if i >= 10:  # skip initial iterations to converge from starting point
            _circle(g, ns, x, y, dot_r,
                    fill=TRIANGLE_COLOR, opacity="0.55")

    return g


def _panel_area_paradox(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the area/perimeter paradox with formula and visual."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale, "The Area Paradox",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "At each step, \u00BC of remaining area",
        "is removed. After infinitely many",
        "steps the total area reaches zero \u2014",
        "yet the boundary length grows",
        "without limit!",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Formulas — centred at col_cx
    formula_y = anno_y + 40 * scale
    _text(g, ns, col_cx, formula_y,
          "Area(n) = (\u00BE)\u207F \u2192 0",
          **{**ANNOTATION_STYLE, "font-size": str(round(4.2 * scale, 2)),
             "font-style": "italic", "text-anchor": "middle"})
    _text(g, ns, col_cx, formula_y + 7 * scale,
          "Perimeter(n) \u2192 \u221E",
          **{**ANNOTATION_STYLE, "font-size": str(round(4.2 * scale, 2)),
             "font-style": "italic", "text-anchor": "middle"})

    # Visual: three stages showing decreasing filled area — centred at col_cx
    demo_y = anno_y + 58 * scale
    for i, (d, label) in enumerate([(0, "n=0"), (1, "n=1"), (3, "n=3")]):
        cx = col_cx + (-18 + i * 18) * scale
        side = 12 * scale
        verts = equilateral_triangle_vertices(cx, demo_y, side)
        for tri in sierpinski_triangles(verts, d):
            _polygon(g, ns, tri, fill=TRIANGLE_COLOR, opacity="0.8")
        _text(g, ns, cx, demo_y + 12 * scale, label,
              **{**ANNOTATION_STYLE, "font-size": str(round(2.8 * scale, 2)),
                 "text-anchor": "middle"})

    return g


# ---------------------------------------------------------------------------
# Poster composition
# ---------------------------------------------------------------------------

# Colour palette – traditional museum/print aesthetic (ink on paper)
BG_COLOR = "#FFFEF8"              # warm ivory paper
TRIANGLE_COLOR = "#1C1C1C"        # near-black ink
TITLE_COLOR = "#1C1C1C"           # dark title text
ACCENT_COLOR = "#8B0000"          # deep museum red
FOOTER_PRIMARY_COLOR = "#555555"  # footer primary text
FOOTER_SECONDARY_COLOR = "#777777"  # footer secondary text


def generate_poster(depth=7, width_mm=420, height_mm=594,
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
        "The Sierpi\u0144ski Triangle",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(round(16 * w_scale, 2)),
            "fill": TITLE_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, subtitle_y,
        "A fractal of infinite complexity from a simple rule",
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

    # Header credits flanking the rule — "Designed by" left, "Designed for" right
    # (classic museum-print placement: small italic caps at the rule ends)
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

    # --- Main fractal (centred in the space between header and annotation) ---
    margin = width_mm * 0.12
    tri_side = width_mm - 2 * margin
    tri_h = tri_side * math.sqrt(3) / 2

    # Ensure the triangle top clears the header rule by ≥ 5 % of poster height
    min_top = rule_y + height_mm * 0.05
    # The annotation zone begins at 70 % of poster height
    anno_start_frac = 0.70
    max_bot = height_mm * anno_start_frac

    # Centre the triangle vertically in the safe band [min_top … max_bot]
    tri_top = min_top
    tri_bot = tri_top + tri_h
    if tri_bot > max_bot:
        # Shrink triangle to fit
        tri_h = max_bot - min_top
        tri_side = tri_h * 2 / math.sqrt(3)
        tri_bot = min_top + tri_h

    tri_cx = width_mm / 2
    # centroid y: top = cy - 2h/3, so cy = top + 2h/3
    tri_cy = min_top + 2 * tri_h / 3

    vertices = equilateral_triangle_vertices(tri_cx, tri_cy, tri_side)

    fractal_group = _group(svg, ns, id="fractal")
    for tri in sierpinski_triangles(vertices, depth):
        _polygon(fractal_group, ns, tri,
                 fill=TRIANGLE_COLOR, stroke="none", opacity="0.92")

    # --- Annotations (below the fractal in a three-column layout) ---
    anno_group = _group(svg, ns, id="annotations")

    fractal_bottom = vertices[1][1]  # bottom vertices share the same y

    # Subtle separator line between fractal and annotations
    anno_sep_y = fractal_bottom + 10 * h_scale
    _line(
        anno_group, ns,
        width_mm * 0.15, anno_sep_y,
        width_mm * 0.85, anno_sep_y,
        stroke=ACCENT_COLOR,
        **{"stroke-width": str(round(0.3 * w_scale, 3)), "opacity": "0.5"},
    )

    anno_y = anno_sep_y + 18 * h_scale  # annotation text starts here

    # Three-column symmetric layout — column centres at 15 %, 50 %, 85 % of
    # width so both outer columns are equidistant from their nearest border.
    col1_cx = width_mm * 0.15
    col2_cx = width_mm * 0.50
    col3_cx = width_mm * 0.85

    # Compute sub-triangle midpoints for precise arrow targets
    ab = midpoint(vertices[0], vertices[1])
    ac = midpoint(vertices[0], vertices[2])
    bc = midpoint(vertices[1], vertices[2])

    # Self-Similarity → centroid of top sub-triangle
    ss_target_x = (vertices[0][0] + ab[0] + ac[0]) / 3
    ss_target_y = (vertices[0][1] + ab[1] + ac[1]) / 3
    _annotation_self_similarity(anno_group, ns,
                                ss_target_x, ss_target_y,
                                col1_cx, anno_y, w_scale)

    # Recursion → centroid of removed centre triangle
    rec_target_x = (ab[0] + ac[0] + bc[0]) / 3
    rec_target_y = (ab[1] + ac[1] + bc[1]) / 3
    _annotation_recursion(anno_group, ns,
                          rec_target_x, rec_target_y,
                          col2_cx, anno_y, w_scale)

    # Dimension → centroid of bottom-right sub-triangle
    dim_target_x = (ac[0] + bc[0] + vertices[2][0]) / 3
    dim_target_y = (ac[1] + bc[1] + vertices[2][1]) / 3
    _annotation_dimension(anno_group, ns,
                          dim_target_x, dim_target_y,
                          col3_cx, anno_y, w_scale)

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

    _panel_pascal(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_chaos_game(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_area_paradox(edu_group, ns, col3_cx, row2_y, w_scale)

    # --- Footer ---
    footer_y = height_mm - 18 * h_scale
    footer_font = round(4 * w_scale, 2)
    footer_font_sm = round(3.5 * w_scale, 2)

    _text(
        svg, ns, width_mm / 2, footer_y,
        "Wac\u0142aw Sierpi\u0144ski first described this fractal in 1915.",
        **{
            "font-family": "Georgia, 'Times New Roman', serif",
            "font-size": str(footer_font),
            "fill": FOOTER_PRIMARY_COLOR,
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, footer_y + 6 * h_scale,
        f"Generated at depth {depth}  \u00b7  {3**depth:,} triangles",
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
        args.output = f"sierpinski_poster.{args.format}"

    print(f"Generating Sierpiński Triangle poster (depth={args.depth}) …")
    svg = generate_poster(
        depth=args.depth,
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
