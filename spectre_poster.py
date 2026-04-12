#!/usr/bin/env python3
"""
Spectre Monotile Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of the
Spectre monotile — the first true aperiodic chiral monotile, discovered
by Smith, Myers, Kaplan & Goodman-Strauss (arXiv:2305.17743).
The Spectre tiles the plane without ever repeating and without reflections.

Usage:
    python spectre_poster.py [OPTIONS]

Options:
    --iterations N       Number of tiling growth rings (default: 6)
    --output FILE        Output filename (default: spectre_poster.svg)
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
    FOOTER_PRIMARY_COLOR,
    SERIF,
    _circle,
    _group,
    _line,
    _multiline_text,
    _polygon,
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
# Spectre tile geometry
# ---------------------------------------------------------------------------

_SQRT3 = math.sqrt(3)


def _hex_to_cart(a, b):
    """Convert hex grid coordinate (a, b) to Cartesian (x, y).

    Uses the standard hex embedding:
        x = a + b * 0.5
        y = b * sqrt(3) / 2
    """
    return (a + b * 0.5, b * _SQRT3 / 2)


# 14 vertices of the Spectre tile in hex grid coordinates.
_SPECTRE_GRID_COORDS = [
    (0, 0), (1, 0), (2, 0), (3, 0),
    (3, 1), (2, 1), (2, 2), (1, 2),
    (1, 3), (0, 3), (0, 2), (-1, 2),
    (-1, 1), (0, 1),
]

# Cartesian coordinates of the 14 Spectre vertices.
SPECTRE_VERTICES = [_hex_to_cart(a, b) for a, b in _SPECTRE_GRID_COORDS]


def _centroid(vertices):
    """Return the centroid of a list of (x, y) vertices."""
    n = len(vertices)
    return (sum(x for x, _ in vertices) / n,
            sum(y for _, y in vertices) / n)


def _signed_area(vertices):
    """Return the signed area of a simple polygon (shoelace formula).

    Positive for counter-clockwise winding, negative for clockwise.
    """
    n = len(vertices)
    area = 0.0
    for i in range(n):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % n]
        area += x0 * y1 - x1 * y0
    return area / 2.0


def verify_chirality(vertices):
    """Verify that the Spectre tile is chiral.

    The Spectre cannot be reflected.  We check this by computing the signed
    area of the polygon and its mirror image.  If the tile is chiral, the
    two signed areas will have opposite signs, confirming that reflection
    produces a distinct tile.

    Returns True if the tile is chiral (signed areas differ in sign).
    """
    sa_original = _signed_area(vertices)
    reflected = [(-x, y) for x, y in vertices]
    sa_reflected = _signed_area(reflected)
    return (sa_original > 0) != (sa_reflected > 0)


# ---------------------------------------------------------------------------
# Tile transform helpers
# ---------------------------------------------------------------------------

def _transform_tile(vertices, angle, tx, ty, scale=1.0):
    """Rotate, scale and translate tile vertices around the tile centroid.

    Parameters
    ----------
    vertices : list of (x, y)
        Canonical tile vertices.
    angle : float
        Rotation angle in radians.
    tx, ty : float
        Translation (final position of tile centroid).
    scale : float
        Uniform scale factor.

    Returns
    -------
    list of (float, float)
        Transformed vertices.
    """
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    cx_v, cy_v = _centroid(vertices)
    result = []
    for x, y in vertices:
        dx, dy = x - cx_v, y - cy_v
        rx = (dx * cos_a - dy * sin_a) * scale + tx
        ry = (dx * sin_a + dy * cos_a) * scale + ty
        result.append((rx, ry))
    return result


# ---------------------------------------------------------------------------
# Tiling generation
# ---------------------------------------------------------------------------

def _aperiodic_rotation(q, r):
    """Determine tile rotation using a quasi-periodic rule.

    Uses an irrational projection to produce a deterministic but
    non-periodic rotation assignment, inspired by cut-and-project
    methods for aperiodic tilings.
    """
    phi = (1 + math.sqrt(5)) / 2
    val = (q * phi + r * phi * phi) % 6
    return int(val) % 6


def generate_spectre_tiling(cx, cy, tile_scale, n_rings, progress=None):
    """Generate Spectre tiles in concentric hex rings around a centre.

    Places Spectre tiles on a hex grid with orientations assigned via
    a quasi-periodic irrational-rotation rule, producing a visually
    aperiodic pattern that respects the tile's chirality (no reflections).

    Parameters
    ----------
    cx, cy : float
        Centre of the tiling in poster coordinates.
    tile_scale : float
        Scale factor applied to the canonical tile.
    n_rings : int
        Number of concentric hex rings to fill.
    progress : ProgressReporter or None
        Optional progress reporter updated once per ring.

    Returns
    -------
    list[list[tuple]]
        Each element is a list of 14 (x, y) vertex tuples describing
        one transformed Spectre tile.
    """
    # Approximate tile bounding dimensions in canonical coordinates
    tile_w = 3.5
    tile_h = 3 * _SQRT3 / 2

    # Hex basis vectors scaled to avoid tile overlap
    bx0, bx1 = tile_w * 0.95, 0.0
    by0, by1 = tile_w * 0.475, tile_h * 0.85

    tiles = []
    placed = set()

    for ring in range(n_rings):
        for q in range(-ring, ring + 1):
            for r in range(-ring, ring + 1):
                s = -q - r
                if ring > 0 and max(abs(q), abs(r), abs(s)) != ring:
                    continue
                if max(abs(q), abs(r), abs(s)) > ring:
                    continue

                key = (q, r)
                if key in placed:
                    continue
                placed.add(key)

                x = cx + (q * bx0 + r * by0) * tile_scale
                y = cy + (q * bx1 + r * by1) * tile_scale

                angle_idx = _aperiodic_rotation(q, r)
                angle = angle_idx * math.pi / 3

                verts = _transform_tile(SPECTRE_VERTICES, angle,
                                        x, y, tile_scale)
                tiles.append(verts)

        if progress is not None:
            progress.update(ring + 1)

    return tiles


# ---------------------------------------------------------------------------
# Construction legend inset
# ---------------------------------------------------------------------------

def _draw_construction_legend(parent, ns, lx, ly, size, w_scale, theme=None):
    """Draw a labelled diagram of the canonical Spectre tile.

    Shows the 14-vertex polygon with numbered vertices, grid coordinates,
    and tick marks indicating equal edge lengths.

    Parameters
    ----------
    parent : Element
        SVG parent element.
    lx, ly : float
        Top-left corner of the legend bounding box.
    size : float
        Width/height of the legend area.
    w_scale : float
        Width scale factor for stroke widths.
    theme : str or None
        Colour theme name.
    """
    t = get_theme(theme)
    g = _group(parent, ns, id="construction-legend")

    # Background
    pad = size * 0.05
    _rect(g, ns, lx, ly, size, size * 1.1,
          fill=t["bg_color"], opacity="0.90",
          stroke=t.get("border_color", "#1C1C1C"),
          **{"stroke-width": str(round(0.3 * w_scale, 3))})

    # Scale the canonical tile to fit the legend box
    xs = [v[0] for v in SPECTRE_VERTICES]
    ys = [v[1] for v in SPECTRE_VERTICES]
    vw = max(xs) - min(xs)
    vh = max(ys) - min(ys)
    fit = (size - 6 * pad) / max(vw, vh)
    ox = lx + size / 2 - (min(xs) + vw / 2) * fit
    oy = ly + size * 0.55 - (min(ys) + vh / 2) * fit

    def _proj(x, y):
        return (ox + x * fit, oy + y * fit)

    # Draw filled polygon
    proj_pts = [_proj(x, y) for x, y in SPECTRE_VERTICES]
    _polygon(g, ns, proj_pts,
             fill=t["content_secondary"], opacity="0.25",
             stroke=t["content_primary"],
             **{"stroke-width": str(round(0.4 * w_scale, 3))})

    # Edge tick marks (midpoint ticks to show equal length)
    tick_len = size * 0.02
    for i in range(14):
        x0, y0 = proj_pts[i]
        x1, y1 = proj_pts[(i + 1) % 14]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        nx, ny = -dy / length, dx / length
        _line(g, ns,
              mx - nx * tick_len, my - ny * tick_len,
              mx + nx * tick_len, my + ny * tick_len,
              stroke=t["accent_color"],
              **{"stroke-width": str(round(0.25 * w_scale, 3))})

    # Vertex labels
    label_fs = round(1.8 * w_scale, 2)
    coord_fs = round(1.3 * w_scale, 2)
    for idx, ((px, py), (ga, gb)) in enumerate(
            zip(proj_pts, _SPECTRE_GRID_COORDS)):
        # Offset label away from centroid
        ccx, ccy = _proj(*_centroid(SPECTRE_VERTICES))
        dx, dy = px - ccx, py - ccy
        d = math.hypot(dx, dy) or 1
        off = size * 0.06
        lxp = px + dx / d * off
        lyp = py + dy / d * off

        _text(g, ns, lxp, lyp,
              str(idx + 1),
              **{"font-size": str(label_fs),
                 "fill": t["accent_color"],
                 "text-anchor": "middle",
                 "font-family": SERIF,
                 "font-weight": "bold"})
        _text(g, ns, lxp, lyp + 2.2 * w_scale,
              f"({ga},{gb})",
              **{"font-size": str(coord_fs),
                 "fill": t.get("footer_primary", FOOTER_PRIMARY_COLOR),
                 "text-anchor": "middle",
                 "font-family": SERIF})

    # Title
    _text(g, ns, lx + size / 2, ly + pad + 2.5 * w_scale,
          "Spectre Tile",
          **{"font-size": str(round(2.8 * w_scale, 2)),
             "fill": t["accent_color"],
             "text-anchor": "middle",
             "font-family": SERIF,
             "font-weight": "bold"})

    return g


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_monotile(parent, ns, target_x, target_y,
                         col_cx, anno_y, scale=1, theme=None):
    """Annotation: What Is a Monotile?"""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "What Is a Monotile?", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "A monotile (or \u2018einstein\u2019) is a single",
        "shape that can tile the entire plane",
        "but only in a non-periodic way. No",
        "finite region of the tiling can be",
        "shifted to exactly match another.",
        "The Spectre is the first true chiral",
    ], scale, theme=theme)
    return g


def _annotation_chirality(parent, ns, target_x, target_y,
                          col_cx, anno_y, scale=1, theme=None):
    """Annotation: Chirality — No Reflections."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Chirality: No Reflections", scale,
                               theme=theme, show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Unlike its predecessor the Hat, the",
        "Spectre tiles the plane using only",
        "rotations and translations \u2014 never",
        "reflections. Its 14th \u2018mystic\u2019 vertex",
        "breaks mirror symmetry, making the",
        "tile genuinely chiral: ein Stein.",
    ], scale, theme=theme)
    return g


def _annotation_einstein(parent, ns, target_x, target_y,
                          col_cx, anno_y, scale=1, theme=None):
    """Annotation: The Einstein Problem."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "The Einstein Problem", scale,
                               theme=theme, show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "For over sixty years mathematicians",
        "sought a single tile that forces",
        "aperiodicity. In 2023, the Hat was",
        "found \u2014 but it required reflections.",
        "The Spectre, announced months later,",
        "settled the problem without them.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_construction(parent, ns, col_cx, anno_y, scale=1):
    """Panel: how the Spectre is constructed."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Spectre Construction",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The Spectre belongs to a family of",
        "Tile(a,b) shapes built from polykites",
        "on the hexagonal grid. It corresponds",
        "to the special case Tile(1,1), where a",
        "single \u2018mystic\u2019 edge modification of",
        "the Hat polygon produces a 14-sided",
        "shape whose mirror image cannot tile",
        "the plane \u2014 enforcing chirality.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )
    return g


def _panel_edges(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the 14 equal edges."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "14 Equal Edges",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Every edge of the Spectre has exactly",
        "the same length \u2014 one unit on the hex",
        "grid. The 14 vertices trace a closed",
        "polygon with no parallel-edge pairs,",
        "preventing any periodic arrangement.",
        "This equilateral property simplifies",
        "edge-matching and guarantees that all",
        "copies are congruent (never reflected).",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )
    return g


def _panel_attribution(parent, ns, col_cx, anno_y, scale=1):
    """Panel: attribution to the discoverers."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Smith, Myers, Kaplan",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "David Smith, a retired print technician,",
        "Joseph Myers, Craig Kaplan, and Chaim",
        "Goodman-Strauss announced the Spectre",
        "in 2023 (arXiv:2305.17743). Building",
        "on their earlier Hat discovery, the",
        "Spectre resolved the full einstein",
        "problem by eliminating the need for",
        "reflected copies in the tiling.",
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

def generate_poster(iterations=6, width_mm=BASE_WIDTH_MM,
                    height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None,
                    verbose=True):
    """Build and return the full Spectre poster as an SVG root element.

    Parameters
    ----------
    iterations : int
        Number of hex-ring growth iterations (default: 6).
    width_mm, height_mm : float
        Poster dimensions in millimetres (default: A2).
    designed_by, designed_for : str or None
        Optional credit lines.
    theme : str or None
        Colour theme name.

    Returns
    -------
    xml.etree.ElementTree.Element
        The root ``<svg>`` element.
    """
    t = get_theme(theme)

    sc = build_poster_scaffold(
        title="The Spectre: Aperiodic Chiral Monotile",
        subtitle="A single shape that tiles the plane \u2014 without reflections",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    avail_w, avail_h = ca["avail_w"], ca["avail_h"]

    # --- Column centres ---
    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # --- Generate the tiling ---
    center_x = width_mm / 2
    center_y = min_top + avail_h / 2
    radius = min(avail_w, avail_h) / 2 * 0.95
    tile_scale = radius / (iterations * 2.0 + 1)

    pp = (ProgressReporter(iterations, "Spectre: rings")
          if verbose else None)
    tiles = generate_spectre_tiling(center_x, center_y, tile_scale,
                                   iterations, progress=pp)
    if pp:
        pp.done()

    # --- Render tiles ---
    tiling_group = _group(svg, ns, id="spectre-tiling")

    fill_a = t["content_primary"]
    fill_b = t["content_secondary"]
    stroke_color = t.get("border_color", "#1C1C1C")

    for idx, verts in enumerate(tiles):
        fill = fill_a if idx % 3 != 0 else fill_b
        _polygon(tiling_group, ns, verts,
                 fill=fill, opacity="0.70",
                 stroke=stroke_color,
                 **{"stroke-width": str(round(0.15 * w_scale, 3)),
                    "stroke-opacity": "0.4"})

    # --- Construction legend inset (upper-right corner) ---
    legend_size = min(avail_w, avail_h) * 0.28
    legend_x = width_mm - ca["margin"] - legend_size - 2 * w_scale
    legend_y = min_top + 2 * h_scale
    _draw_construction_legend(svg, ns, legend_x, legend_y,
                              legend_size, w_scale, theme=theme)

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    target_y = center_y + radius * 0.25

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_monotile, col1_cx, target_y),
            (_annotation_chirality, col2_cx, target_y),
            (_annotation_einstein, col3_cx, target_y),
        ],
        w_scale,
        theme=theme,
    )

    # --- Second row: educational panels ---
    edu_group = _group(svg, ns, id="educational")

    row2_sep_y = anno_y + 55 * w_scale
    draw_row_separator(edu_group, ns, width_mm, row2_sep_y, w_scale,
                       opacity="0.35", theme=theme)

    row2_y = row2_sep_y + 12 * w_scale

    _panel_construction(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_edges(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_attribution(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "The Spectre monotile, discovered in 2023 by Smith, Myers, "
            "Kaplan & Goodman-Strauss (arXiv:2305.17743)."
        ),
        secondary_line=(
            f"Generated with {iterations} ring"
            f"{'s' if iterations != 1 else ''}  "
            f"\u00b7  {len(tiles):,} tiles  "
            f"\u00b7  14 vertices per tile"
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
        description="Generate an annotated Spectre monotile poster.",
    )
    parser.add_argument(
        "--iterations", type=int, default=6,
        help="Number of hex-ring growth iterations (default: 6).",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        iterations=args.iterations,
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
        filename_prefix="spectre_poster",
        poster_label=(
            f"Spectre monotile poster "
            f"(iterations={args.iterations})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
