#!/usr/bin/env python3
"""
Hat Monotile Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of the Hat
aperiodic monotile — the first true "einstein" (one stone) discovered by
David Smith, Joseph Samuel Myers, Craig S. Kaplan, and Chaim Goodman-Strauss
in 2023.  The Hat is a 13-sided polykite that tiles the plane but only
aperiodically, settling a decades-old open problem.

Usage:
    python hat_tiling_poster.py [OPTIONS]

Options:
    --iterations N       Number of substitution iterations (default: 3)
    --output FILE        Output filename (default: hat_tiling_poster.svg)
    --format FMT         Output format: svg, pdf, or png (default: svg)
    --dpi N              Resolution for PNG output in dots per inch (default: 150)
    --width MM           Poster width in mm (default: 420, A2 width)
    --height MM          Poster height in mm (default: 594, A2 height)
    --designed-by TEXT   Designer credit (e.g. 'Alice and Bob')
    --designed-for TEXT  Client / purpose credit (e.g. 'the Science Museum')
"""

import argparse
import math
from collections import deque

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
# Hat tile geometry
# ---------------------------------------------------------------------------

# Basis vectors for the triangular (hex) grid.
# e1 = (1, 0),  e2 = (1/2, sqrt(3)/2)
_SQRT3 = math.sqrt(3)
_E1 = (1.0, 0.0)
_E2 = (0.5, _SQRT3 / 2.0)


def _hex_to_cart(a, b):
    """Convert triangular-grid coordinates (a, b) to Cartesian (x, y)."""
    return (a * _E1[0] + b * _E2[0], a * _E1[1] + b * _E2[1])


# The Hat polygon: canonical 13 vertices on the triangular grid.
# Coordinates from Smith et al. (2023), arXiv:2303.10798, Figure 1 / Table S1.
# Basis: a = (1, 0), b = (1/2, sqrt(3)/2).
#
# Index  (a,  b)   Cartesian (x, y)
#   1    (0,  0)   (0,      0     )
#   2    (1,  0)   (1,      0     )
#   3    (2,  0)   (2,      0     )
#   4    (3,  1)   (3.5,    0.866 )
#   5    (3,  2)   (4,      1.732 )
#   6    (2,  3)   (3.5,    2.598 )
#   7    (1,  3)   (2.5,    2.598 )
#   8    (0,  2)   (1,      1.732 )
#   9    (-1, 2)   (0,      1.732 )
#  10    (-2, 1)   (-1.5,   0.866 )
#  11    (-2, 0)   (-2,     0     )
#  12    (-1,-1)   (-1.5,  -0.866 )
#  13    (0, -1)   (-0.5,  -0.866 )
_HAT_GRID_COORDS = [
    (0, 0), (1, 0), (2, 0), (3, 1),
    (3, 2), (2, 3), (1, 3), (0, 2),
    (-1, 2), (-2, 1), (-2, 0), (-1, -1),
    (0, -1),
]

HAT_VERTICES = [_hex_to_cart(a, b) for a, b in _HAT_GRID_COORDS]


def _transform_hat(vertices, angle, tx, ty, scale=1.0, reflect=False):
    """Rotate, optionally reflect, scale and translate Hat vertices.

    Parameters
    ----------
    vertices : list[tuple[float, float]]
        Base Hat polygon vertices.
    angle : float
        Rotation angle in radians.
    tx, ty : float
        Translation offset applied after rotation.
    scale : float
        Uniform scale factor.
    reflect : bool
        If True, reflect across the x-axis before rotating.

    Returns
    -------
    list[tuple[float, float]]
        Transformed vertices.
    """
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    result = []
    for x, y in vertices:
        if reflect:
            y = -y
        rx = (x * cos_a - y * sin_a) * scale + tx
        ry = (x * sin_a + y * cos_a) * scale + ty
        result.append((rx, ry))
    return result


# ---------------------------------------------------------------------------
# Hat tiling via edge-matching BFS growth
# ---------------------------------------------------------------------------

# Each tile is stored as (angle, tx, ty, reflected).
# We grow the tiling outward from a single seed tile by matching edges
# with neighbours.  Every Hat placement is edge-to-edge on the
# triangular grid, guaranteeing a gap-free, overlap-free tiling.
# The Hat's key property (Smith et al., 2023) ensures that any valid
# edge-to-edge tiling is necessarily aperiodic.

# Pre-classify Hat edges by length for efficient matching.
# Short edges (length 1):  indices 0,1,3,4,5,7,9,10,11,12
# Long  edges (length √3): indices 2,6,8
_SHORT_EDGES = []
_LONG_EDGES = []

for _i in range(13):
    _v1 = HAT_VERTICES[_i]
    _v2 = HAT_VERTICES[(_i + 1) % 13]
    _elen = math.hypot(_v2[0] - _v1[0], _v2[1] - _v1[1])
    if _elen < 1.5:
        _SHORT_EDGES.append(_i)
    else:
        _LONG_EDGES.append(_i)


def _find_neighbor(ref_verts, edge_i, reflected_B, edge_j):
    """Compute a candidate neighbour placement that shares one edge.

    Given a placed tile (via its world-coordinate vertices *ref_verts*),
    compute the angle and position of a new tile whose edge *edge_j*
    (reversed) aligns exactly with edge *edge_i* of the placed tile.

    Parameters
    ----------
    ref_verts : list[tuple[float, float]]
        The 13 world-coordinate vertices of the placed (reference) tile.
    edge_i : int
        Edge index on the reference tile (0–12).
    reflected_B : bool
        Whether the candidate neighbour is reflected.
    edge_j : int
        Edge index on the candidate tile (0–12).

    Returns
    -------
    tuple[float, float, float] or None
        ``(angle, tx, ty)`` for the candidate tile, or *None* if the
        edges are incompatible (different length).
    """
    vi = ref_verts[edge_i]
    vi_next = ref_verts[(edge_i + 1) % 13]

    # Reversed edge direction (target direction for neighbour's edge)
    dx_rev = vi[0] - vi_next[0]
    dy_rev = vi[1] - vi_next[1]
    len_rev = math.hypot(dx_rev, dy_rev)

    # Edge j of the base Hat in local coordinates (possibly reflected)
    vj = HAT_VERTICES[edge_j]
    vj_next = HAT_VERTICES[(edge_j + 1) % 13]

    if reflected_B:
        vj = (vj[0], -vj[1])
        vj_next = (vj_next[0], -vj_next[1])

    dx_B = vj_next[0] - vj[0]
    dy_B = vj_next[1] - vj[1]
    len_B = math.hypot(dx_B, dy_B)

    # Only same-length edges can match
    if abs(len_B - len_rev) > 1e-6:
        return None

    # Rotation: Rot(θ) · d_B = d_rev
    # θ = atan2(d_rev_y · d_B_x − d_rev_x · d_B_y,
    #           d_rev_x · d_B_x + d_rev_y · d_B_y)
    dot_val = dx_rev * dx_B + dy_rev * dy_B
    cross_val = dy_rev * dx_B - dx_rev * dy_B
    theta = math.atan2(cross_val, dot_val)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    # Translation: world position of vertex j equals vi_next
    rx = vj[0] * cos_t - vj[1] * sin_t
    ry = vj[0] * sin_t + vj[1] * cos_t
    tx = vi_next[0] - rx
    ty = vi_next[1] - ry

    # Sanity check: vertex (j+1)%13 should equal vi
    rx2 = vj_next[0] * cos_t - vj_next[1] * sin_t
    ry2 = vj_next[0] * sin_t + vj_next[1] * cos_t
    if abs(rx2 + tx - vi[0]) > 1e-4 or abs(ry2 + ty - vi[1]) > 1e-4:
        return None

    return (theta, tx, ty)


def _centroid(verts):
    """Return the centroid of a list of vertices."""
    n = len(verts)
    return (sum(v[0] for v in verts) / n,
            sum(v[1] for v in verts) / n)


def _point_in_polygon(px, py, polygon):
    """Ray-casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and \
                (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def generate_hat_tiling(iterations, progress=None):
    """Generate a Hat tiling as a list of tile descriptors.

    Grows an edge-to-edge Hat tiling outward from a single seed tile
    using breadth-first edge matching.  The number of tiles scales
    roughly as ``7 ** iterations``.

    Parameters
    ----------
    iterations : int
        Controls the number of tiles generated (default: 3).
        Tile count scales as ``6 ** (iterations + 1)``:
        0 → ~7, 1 → ~36, 2 → ~216, 3 → ~1296.
    progress : ProgressReporter or None
        Optional progress reporter (total should equal *iterations*).

    Returns
    -------
    list[tuple[float, float, float, bool]]
        Each element is ``(angle, tx, ty, reflected)`` describing one
        Hat tile placement.
    """
    # Target tile count scales with iterations
    max_tiles = max(7, int(6 ** (min(iterations, 5) + 1.0)))

    # Start with a single unreflected Hat at the origin
    tiles = [(0.0, 0.0, 0.0, False)]
    verts_cache = {0: list(HAT_VERTICES)}

    # --- Spatial hash for overlap detection ---
    cell_size = 4.0
    spatial = {}          # (ix, iy) → [(cx, cy, tile_idx, verts)]

    def _hash_key(x, y):
        return (int(math.floor(x / cell_size)),
                int(math.floor(y / cell_size)))

    def _register(idx):
        vs = verts_cache[idx]
        cx, cy = _centroid(vs)
        key = _hash_key(cx, cy)
        spatial.setdefault(key, []).append((cx, cy, idx, vs))

    def _overlaps(new_verts):
        """Return True if *new_verts* overlaps any existing tile."""
        ncx, ncy = _centroid(new_verts)
        ix, iy = _hash_key(ncx, ncy)
        for di in range(-1, 2):
            for dj in range(-1, 2):
                for ecx, ecy, _eidx, everts in spatial.get(
                        (ix + di, iy + dj), []):
                    # Quick distance pre-check
                    if abs(ncx - ecx) > 7 or abs(ncy - ecy) > 7:
                        continue
                    # Centroid-in-polygon test (both directions)
                    if _point_in_polygon(ncx, ncy, everts):
                        return True
                    if _point_in_polygon(ecx, ecy, new_verts):
                        return True
        return False

    _register(0)

    # --- BFS growth ---
    boundary = deque((0, i) for i in range(13))
    matched = set()

    # Progress bookkeeping
    report_step = max(1, max_tiles // max(iterations, 1))

    while boundary and len(tiles) < max_tiles:
        tile_idx, edge_idx = boundary.popleft()

        if (tile_idx, edge_idx) in matched:
            continue

        ref_verts = verts_cache[tile_idx]

        # Determine candidate edge indices by length
        edge_len = math.hypot(
            ref_verts[(edge_idx + 1) % 13][0] - ref_verts[edge_idx][0],
            ref_verts[(edge_idx + 1) % 13][1] - ref_verts[edge_idx][1],
        )
        candidates = _SHORT_EDGES if edge_len < 1.5 else _LONG_EDGES

        placed = False
        # Prefer unreflected neighbours (matches ~1 : 6 reflected ratio)
        for reflected_B in (False, True):
            if placed:
                break
            for edge_j in candidates:
                result = _find_neighbor(ref_verts, edge_idx,
                                        reflected_B, edge_j)
                if result is None:
                    continue

                theta, tx, ty = result
                new_verts = _transform_hat(HAT_VERTICES, theta, tx, ty,
                                           reflect=reflected_B)

                if _overlaps(new_verts):
                    continue

                # Accept this placement
                new_idx = len(tiles)
                tiles.append((theta, tx, ty, reflected_B))
                verts_cache[new_idx] = new_verts
                _register(new_idx)

                matched.add((tile_idx, edge_idx))
                matched.add((new_idx, edge_j))

                for i in range(13):
                    if (new_idx, i) not in matched:
                        boundary.append((new_idx, i))

                placed = True
                break

        # Report progress periodically
        if progress is not None and len(tiles) % report_step == 0:
            step = min(iterations, int(iterations * len(tiles) / max_tiles))
            progress.update(step)

    if progress is not None:
        progress.update(iterations)

    return tiles


def render_hat_tiles(tiles, cx, cy, scale, clip_w, clip_h):
    """Convert tile descriptors to polygon vertex lists for rendering.

    Parameters
    ----------
    tiles : list[tuple[float, float, float, bool]]
        Tile descriptors from :func:`generate_hat_tiling`.
    cx, cy : float
        Centre of the rendering area.
    scale : float
        Scale factor applied to all tile coordinates.
    clip_w, clip_h : float
        Width and height of the clipping rectangle centred at (cx, cy).

    Returns
    -------
    list[tuple[list[tuple[float, float]], bool]]
        Each element is ``(vertices, reflected)`` — the polygon vertices
        and whether the tile is reflected.
    """
    half_w = clip_w / 2
    half_h = clip_h / 2
    result = []
    for angle, tx, ty, reflected in tiles:
        verts = _transform_hat(HAT_VERTICES, angle, tx, ty, scale=1.0,
                               reflect=reflected)
        # Scale and translate to rendering area
        rendered = [(x * scale + cx, y * scale + cy) for x, y in verts]
        # Clip: keep tile if its centroid falls within bounds
        mx = sum(v[0] for v in rendered) / len(rendered)
        my = sum(v[1] for v in rendered) / len(rendered)
        if (cx - half_w <= mx <= cx + half_w and
                cy - half_h <= my <= cy + half_h):
            result.append((rendered, reflected))
    return result


# ---------------------------------------------------------------------------
# Canonical Hat legend (13-vertex construction diagram)
# ---------------------------------------------------------------------------

def _draw_canonical_hat_legend(parent, ns, cx, cy, size, theme=None):
    """Draw a single canonical Hat with labeled vertices and grid reference.

    Renders the Hat polygon at position (cx, cy) scaled to *size* mm, with
    each of the 13 canonical vertices numbered and annotated with their
    triangular-grid coordinates (a, b).  A faint triangular-grid backdrop is
    also drawn to show the geometric construction.

    Parameters
    ----------
    parent : xml.etree.ElementTree.Element
        SVG parent element to attach the diagram to.
    ns : str
        SVG namespace string.
    cx, cy : float
        Centre of the diagram in SVG user units (mm).
    size : float
        Approximate diameter of the diagram in mm.
    theme : str or None
        Colour theme name.
    """
    t = get_theme(theme)
    g = _group(parent, ns, id="canonical-hat-legend")

    # Scale: fit the Hat bounding box inside *size* mm.
    xs = [x for x, _ in HAT_VERTICES]
    ys = [y for _, y in HAT_VERTICES]
    hat_span = max(max(xs) - min(xs), max(ys) - min(ys))
    sc = size / hat_span * 0.82        # a little padding
    ox = cx - (max(xs) + min(xs)) / 2 * sc
    oy = cy - (max(ys) + min(ys)) / 2 * sc

    def to_svg(x, y):
        """Convert Hat-space coords to SVG coords (y flipped for screen)."""
        return ox + x * sc, oy - y * sc

    # --- Background grid (faint triangular grid lines) ---
    grid_g = _group(g, ns, id="hat-legend-grid")
    grid_color = t.get("border_color", "#888888")
    grid_kw = {"stroke": grid_color, "stroke-opacity": "0.18",
                "stroke-width": str(round(0.22, 3))}

    # Draw a small portion of the triangular lattice as reference
    a_range = range(-3, 6)
    b_range = range(-2, 5)
    for b in b_range:
        # Horizontal-ish lines (constant b)
        pts = [(a, b) for a in a_range]
        for i in range(len(pts) - 1):
            x0, y0 = to_svg(*_hex_to_cart(*pts[i]))
            x1, y1 = to_svg(*_hex_to_cart(*pts[i + 1]))
            _line(grid_g, ns, x0, y0, x1, y1, **grid_kw)
    for a in a_range:
        # Diagonal lines (constant a)
        pts = [(a, b) for b in b_range]
        for i in range(len(pts) - 1):
            x0, y0 = to_svg(*_hex_to_cart(*pts[i]))
            x1, y1 = to_svg(*_hex_to_cart(*pts[i + 1]))
            _line(grid_g, ns, x0, y0, x1, y1, **grid_kw)
    for diff in range(min(a_range) + min(b_range), max(a_range) + max(b_range) + 1):
        # Third family: a + b = const
        pts = [(a, diff - a) for a in a_range
               if min(b_range) <= diff - a <= max(b_range)]
        for i in range(len(pts) - 1):
            x0, y0 = to_svg(*_hex_to_cart(*pts[i]))
            x1, y1 = to_svg(*_hex_to_cart(*pts[i + 1]))
            _line(grid_g, ns, x0, y0, x1, y1, **grid_kw)

    # --- Hat polygon fill ---
    poly_pts = [to_svg(x, y) for x, y in HAT_VERTICES]
    _polygon(g, ns, poly_pts,
             fill=t["content_primary"],
             opacity="0.55",
             stroke=t.get("border_color", "#1C1C1C"),
             **{"stroke-width": str(round(0.35, 3)), "stroke-opacity": "0.85"})

    # --- Vertex dots and labels ---
    dot_r = size * 0.018
    label_offset = size * 0.055
    label_kw = {
        "font-family": SERIF,
        "font-size": str(round(size * 0.065, 2)),
        "fill": t.get("title_color", "#1C1C1C"),
        "text-anchor": "middle",
    }
    coord_kw = {
        "font-family": SERIF,
        "font-size": str(round(size * 0.048, 2)),
        "fill": t.get("text_color", "#444444"),
        "text-anchor": "middle",
    }

    for idx, ((ga, gb), (hx, hy)) in enumerate(
            zip(_HAT_GRID_COORDS, HAT_VERTICES)):
        sx, sy = to_svg(hx, hy)
        _circle(g, ns, sx, sy, dot_r,
                fill=t.get("accent_color", ACCENT_COLOR),
                stroke="none")

        # Nudge label outward from centroid
        mx = sum(p[0] for p in poly_pts) / len(poly_pts)
        my = sum(p[1] for p in poly_pts) / len(poly_pts)
        dx, dy = sx - mx, sy - my
        dist = math.hypot(dx, dy) or 1.0
        lx = sx + dx / dist * label_offset
        ly = sy + dy / dist * label_offset - dot_r * 0.5

        # Vertex index (1-based)
        _text(g, ns, lx, ly, str(idx + 1), **label_kw)
        # Grid coordinates below
        _text(g, ns, lx, ly + size * 0.072,
              f"({ga},{gb})", **coord_kw)

    # --- Legend title ---
    _text(g, ns, cx, oy - max(ys) * sc - size * 0.12,
          "Canonical 13-Vertex Hat Construction",
          **{**label_kw,
             "font-size": str(round(size * 0.075, 2)),
             "fill": t.get("accent_color", ACCENT_COLOR)})

    # --- Legend key: reflected vs unreflected colour swatches ---
    swatch_y = oy - min(ys) * sc + size * 0.10
    swatch_w, swatch_h = size * 0.12, size * 0.065
    swatch_kw = {
        "font-family": SERIF,
        "font-size": str(round(size * 0.06, 2)),
        "fill": t.get("text_color", "#444444"),
        "dominant-baseline": "middle",
    }
    # Unreflected swatch
    ux = cx - size * 0.28
    _rect(g, ns, ux - swatch_w / 2, swatch_y - swatch_h / 2,
          swatch_w, swatch_h,
          fill=t["content_primary"], opacity="0.75",
          stroke=t.get("border_color", "#1C1C1C"),
          **{"stroke-width": "0.25"})
    _text(g, ns, ux + swatch_w * 0.85, swatch_y,
          "Unreflected", **swatch_kw)
    # Reflected swatch
    rx = cx + size * 0.10
    _rect(g, ns, rx - swatch_w / 2, swatch_y - swatch_h / 2,
          swatch_w, swatch_h,
          fill=t["content_secondary"], opacity="0.75",
          stroke=t.get("border_color", "#1C1C1C"),
          **{"stroke-width": "0.25"})
    _text(g, ns, rx + swatch_w * 0.85, swatch_y,
          "Reflected", **swatch_kw)

    return g


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_einstein(parent, ns, target_x, target_y,
                         col_cx, anno_y, scale=1, theme=None):
    """Annotation: the Einstein tile concept."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "The Einstein Tile", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "\u2018Ein Stein\u2019 \u2014 German for \u2018one",
        "stone\u2019 \u2014 names the dream of a single",
        "shape that tiles the entire plane",
        "yet can never do so periodically.",
        "The Hat is the first monotile proven",
        "to be aperiodic (with reflected copies).",
    ], scale, theme=theme)
    return g


def _annotation_aperiodic(parent, ns, target_x, target_y,
                           col_cx, anno_y, scale=1, theme=None):
    """Annotation: aperiodic order in the Hat tiling."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Aperiodic Order", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "The Hat fills the plane edge to",
        "edge with no gaps or overlaps, yet",
        "no translation can map the tiling",
        "onto itself. Every finite patch",
        "recurs infinitely often, but the",
        "whole pattern never repeats.",
    ], scale, theme=theme)
    return g


def _annotation_simple_shape(parent, ns, target_x, target_y,
                              col_cx, anno_y, scale=1, theme=None):
    """Annotation: the surprising simplicity of the Hat."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "A Simple Shape", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Just 13 sides and 8 kite shapes",
        "compose the Hat \u2014 a polykite on the",
        "triangular grid. Its outline is so",
        "simple it can be drawn by hand, yet",
        "its tiling behaviour is profoundly",
        "complex and inherently non-periodic.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_how_it_tiles(parent, ns, col_cx, anno_y, scale=1):
    """Panel: how the Hat tiling is constructed."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "How the Hat Tiles",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The Hat tiles through a hierarchical",
        "substitution system. Small clusters",
        "of Hats combine into four metatile",
        "types (H, T, P, F) that themselves",
        "tile by substitution. About one in",
        "every seven Hats is a reflected copy;",
        "the rest are unreflected, ensuring",
        "the pattern never repeats.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )
    return g


def _panel_discovery(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the discovery story."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Discovery",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "In late 2022, hobbyist David Smith",
        "noticed a curious shape while playing",
        "with paper cut-outs. Teaming with",
        "mathematicians Myers, Kaplan, and",
        "Goodman-Strauss, they proved it was",
        "a true aperiodic monotile \u2014 solving",
        "a problem open for over 60 years.",
        "Their paper appeared in March 2023.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )
    return g


def _panel_significance(parent, ns, col_cx, anno_y, scale=1):
    """Panel: mathematical significance and the Spectre."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Mathematical Significance",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The Hat requires reflections: some",
        "tiles are mirrored copies. In May",
        "2023 the same team unveiled the",
        "\u2018Spectre\u2019 \u2014 a modified monotile that",
        "tiles aperiodically without any",
        "reflections at all. Together these",
        "discoveries reshape our fundamental",
        "understanding of geometric order.",
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

def generate_poster(iterations=3, width_mm=BASE_WIDTH_MM,
                    height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None,
                    verbose=True):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    iterations : int
        Number of cluster expansion iterations (default: 3).
    width_mm, height_mm : float
        Poster dimensions in millimetres (default: A2).
    designed_by, designed_for : str or None
        Optional credit lines.
    theme : str or None
        Colour theme name.
    verbose : bool
        If True, show progress during generation.

    Returns
    -------
    xml.etree.ElementTree.Element
        The root ``<svg>`` element.
    """
    t = get_theme(theme)

    sc = build_poster_scaffold(
        title="The Hat Monotile",
        subtitle="A single shape that tiles the plane, but never periodically",
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
    tile_scale = min(avail_w, avail_h) / 2 * 0.95 / max(
        max(abs(x) for x, _ in HAT_VERTICES),
        max(abs(y) for _, y in HAT_VERTICES),
    ) * 0.33

    _pp = ProgressReporter(iterations, "Hat: iterations") if verbose else None
    raw_tiles = generate_hat_tiling(iterations, progress=_pp)
    if _pp:
        _pp.done()

    rendered = render_hat_tiles(raw_tiles, center_x, center_y,
                                tile_scale, avail_w, avail_h)

    # --- Render tiles ---
    tiling_group = _group(svg, ns, id="hat-tiling")

    hat_color = t["content_primary"]
    hat_reflected_color = t["content_secondary"]
    stroke_color = t.get("border_color", "#1C1C1C")

    for verts, reflected in rendered:
        fill = hat_reflected_color if reflected else hat_color
        _polygon(tiling_group, ns, verts,
                 fill=fill, opacity="0.75",
                 stroke=stroke_color,
                 **{"stroke-width": str(round(0.15 * w_scale, 3)),
                    "stroke-opacity": "0.3"})

    # --- Canonical Hat legend inset (upper-right content area) ---
    legend_group = _group(svg, ns, id="canonical-hat-legend-inset")
    legend_size = min(avail_w, avail_h) * 0.28
    legend_cx = width_mm - legend_size * 0.52
    legend_cy = min_top + legend_size * 0.55
    _draw_canonical_hat_legend(legend_group, ns, legend_cx, legend_cy,
                               legend_size, theme=theme)

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    target_y = center_y + avail_h * 0.15

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_einstein, col1_cx, target_y),
            (_annotation_aperiodic, col2_cx, target_y),
            (_annotation_simple_shape, col3_cx, target_y),
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

    _panel_how_it_tiles(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_discovery(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_significance(edu_group, ns, col3_cx, row2_y, w_scale)

    tile_count = len(rendered)
    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "The Hat monotile \u2014 discovered by Smith, Myers, Kaplan "
            "& Goodman-Strauss, 2023."
        ),
        secondary_line=(
            f"Generated with {iterations} iteration"
            f"{'s' if iterations != 1 else ''}  "
            f"\u00b7  {tile_count:,} tiles rendered  "
            f"\u00b7  13 vertices \u00b7 8 kites"
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
        description="Generate an annotated Hat Monotile poster.",
    )
    parser.add_argument(
        "--iterations", type=int, default=3,
        help="Number of cluster expansion iterations (default: 3).",
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
        filename_prefix="hat_tiling_poster",
        poster_label=(
            f"Hat Monotile poster "
            f"(iterations={args.iterations})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
