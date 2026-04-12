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
# Coordinates from Smith et al. (2023), arXiv:2303.10798, Figure 2 / Table 1.
# Basis: a = (1, 0), b = (1/2, sqrt(3)/2).
#
# Index  (a,  b)   Cartesian (x, y)
#   1    (0,  0)   (0,      0     )
#   2    (1,  0)   (1,      0     )
#   3    (2,  0)   (2,      0     )
#   4    (3,  0)   (3,      0     )
#   5    (3,  1)   (3.5,    0.866 )
#   6    (2,  1)   (2.5,    0.866 )
#   7    (2,  2)   (3,      1.732 )
#   8    (1,  2)   (2,      1.732 )
#   9    (1,  3)   (2.5,    2.598 )
#  10    (0,  3)   (1.5,    2.598 )
#  11    (0,  2)   (1,      1.732 )
#  12    (-1, 2)   (0,      1.732 )
#  13    (-1, 1)   (-0.5,   0.866 )
_HAT_GRID_COORDS = [
    (0, 0), (1, 0), (2, 0), (3, 0),
    (3, 1), (2, 1), (2, 2), (1, 2),
    (1, 3), (0, 3), (0, 2), (-1, 2),
    (-1, 1),
]

HAT_VERTICES = [_hex_to_cart(a, b) for a, b in _HAT_GRID_COORDS]


# Internal substitution hat — coordinates used by the Kaplan-style metatile
# engine (H/T/P/F hierarchy).  These are NOT the canonical outline; they are
# the basis-vector representation that the reference implementation uses to
# define edge matchings and metatile outlines.  The public ``HAT_VERTICES``
# above are used for rendering and display.
_SUBST_HAT_GRID_COORDS = [
    (0, 0), (-1, -1), (0, -2), (2, -2),
    (2, -1), (4, -2), (5, -1), (4, 0),
    (3, 0), (2, 2), (0, 3), (0, 2),
    (-1, 2),
]
_SUBST_HAT_VERTICES = [_hex_to_cart(a, b) for a, b in _SUBST_HAT_GRID_COORDS]

# Precompute centroids for both shapes — used when mapping substitution
# positions onto the canonical polygon.
_SUBST_CENTROID = (
    sum(x for x, _ in _SUBST_HAT_VERTICES) / len(_SUBST_HAT_VERTICES),
    sum(y for _, y in _SUBST_HAT_VERTICES) / len(_SUBST_HAT_VERTICES),
)
_CANON_CENTROID = (
    sum(x for x, _ in HAT_VERTICES) / len(HAT_VERTICES),
    sum(y for _, y in HAT_VERTICES) / len(HAT_VERTICES),
)


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
# Hat tiling via deterministic substitution (H/T/P/F metatiles)
# ---------------------------------------------------------------------------

# Affine matrix format:
# [a, b, c, d, e, f] where x' = a*x + b*y + c and y' = d*x + e*y + f
_IDENT = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)


def _pt_add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def _pt_sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def _aff_mul(A, B):
    return (
        A[0] * B[0] + A[1] * B[3],
        A[0] * B[1] + A[1] * B[4],
        A[0] * B[2] + A[1] * B[5] + A[2],
        A[3] * B[0] + A[4] * B[3],
        A[3] * B[1] + A[4] * B[4],
        A[3] * B[2] + A[4] * B[5] + A[5],
    )


def _aff_inv(T):
    det = T[0] * T[4] - T[1] * T[3]
    return (
        T[4] / det,
        -T[1] / det,
        (T[1] * T[5] - T[2] * T[4]) / det,
        -T[3] / det,
        T[0] / det,
        (T[2] * T[3] - T[0] * T[5]) / det,
    )


def _aff_trans(tx, ty):
    return (1.0, 0.0, tx, 0.0, 1.0, ty)


def _aff_rot(ang):
    c = math.cos(ang)
    s = math.sin(ang)
    return (c, -s, 0.0, s, c, 0.0)


def _aff_rot_about(p, ang):
    return _aff_mul(_aff_trans(p[0], p[1]),
                    _aff_mul(_aff_rot(ang), _aff_trans(-p[0], -p[1])))


def _trans_pt(M, P):
    return (M[0] * P[0] + M[1] * P[1] + M[2],
            M[3] * P[0] + M[4] * P[1] + M[5])


def _match_seg(p, q):
    return (q[0] - p[0], p[1] - q[1], p[0],
            q[1] - p[1], q[0] - p[0], p[1])


def _match_two(p1, q1, p2, q2):
    return _aff_mul(_match_seg(p2, q2), _aff_inv(_match_seg(p1, q1)))


def _intersect(p1, q1, p2, q2):
    d = ((q2[1] - p2[1]) * (q1[0] - p1[0]) -
         (q2[0] - p2[0]) * (q1[1] - p1[1]))
    ua = (((q2[0] - p2[0]) * (p1[1] - p2[1]) -
           (q2[1] - p2[1]) * (p1[0] - p2[0])) / d)
    return (p1[0] + ua * (q1[0] - p1[0]),
            p1[1] + ua * (q1[1] - p1[1]))


class _BaseHat:
    def __init__(self, label):
        self.label = label
        self.shape = _SUBST_HAT_VERTICES


class _MetaTile:
    def __init__(self, shape, width):
        self.shape = shape
        self.width = width
        self.children = []

    def add_child(self, T, geom):
        self.children.append((T, geom))

    def eval_child(self, n, i):
        T, geom = self.children[n]
        return _trans_pt(T, geom.shape[i])

    def recenter(self):
        cx = sum(p[0] for p in self.shape) / len(self.shape)
        cy = sum(p[1] for p in self.shape) / len(self.shape)
        self.shape = [(p[0] - cx, p[1] - cy) for p in self.shape]
        M = _aff_trans(-cx, -cy)
        self.children = [(_aff_mul(M, T), geom) for T, geom in self.children]


def _build_initial_metatiles():
    h1_hat = _BaseHat("H1")
    h_hat = _BaseHat("H")
    t_hat = _BaseHat("T")
    p_hat = _BaseHat("P")
    f_hat = _BaseHat("F")

    hr3 = _SQRT3 / 2.0

    h_outline = [
        (0.0, 0.0), (4.0, 0.0), (4.5, hr3),
        (2.5, 5 * hr3), (1.5, 5 * hr3), (-0.5, hr3),
    ]
    h_init = _MetaTile(h_outline, 2.0)
    h_init.add_child(_match_two(_SUBST_HAT_VERTICES[5], _SUBST_HAT_VERTICES[7],
                                h_outline[5], h_outline[0]), h_hat)
    h_init.add_child(_match_two(_SUBST_HAT_VERTICES[9], _SUBST_HAT_VERTICES[11],
                                h_outline[1], h_outline[2]), h_hat)
    h_init.add_child(_match_two(_SUBST_HAT_VERTICES[5], _SUBST_HAT_VERTICES[7],
                                h_outline[3], h_outline[4]), h_hat)
    h_init.add_child(_aff_mul(
        _aff_trans(2.5, hr3),
        _aff_mul((-0.5, -hr3, 0.0, hr3, -0.5, 0.0),
                 (0.5, 0.0, 0.0, 0.0, -0.5, 0.0))), h1_hat)

    t_outline = [(0.0, 0.0), (3.0, 0.0), (1.5, 3 * hr3)]
    t_init = _MetaTile(t_outline, 2.0)
    t_init.add_child((0.5, 0.0, 0.5, 0.0, 0.5, hr3), t_hat)

    p_outline = [(0.0, 0.0), (4.0, 0.0), (3.0, 2 * hr3), (-1.0, 2 * hr3)]
    p_init = _MetaTile(p_outline, 2.0)
    p_init.add_child((0.5, 0.0, 1.5, 0.0, 0.5, hr3), p_hat)
    p_init.add_child(_aff_mul(
        _aff_trans(0.0, 2 * hr3),
        _aff_mul((0.5, hr3, 0.0, -hr3, 0.5, 0.0),
                 (0.5, 0.0, 0.0, 0.0, 0.5, 0.0))), p_hat)

    f_outline = [
        (0.0, 0.0), (3.0, 0.0), (3.5, hr3),
        (3.0, 2 * hr3), (-1.0, 2 * hr3),
    ]
    f_init = _MetaTile(f_outline, 2.0)
    f_init.add_child((0.5, 0.0, 1.5, 0.0, 0.5, hr3), f_hat)
    f_init.add_child(_aff_mul(
        _aff_trans(0.0, 2 * hr3),
        _aff_mul((0.5, hr3, 0.0, -hr3, 0.5, 0.0),
                 (0.5, 0.0, 0.0, 0.0, 0.5, 0.0))), f_hat)

    return h_init, t_init, p_init, f_init


def _construct_patch(H, T, P, F):
    rules = [
        ["H"],
        [0, 0, "P", 2],
        [1, 0, "H", 2],
        [2, 0, "P", 2],
        [3, 0, "H", 2],
        [4, 4, "P", 2],
        [0, 4, "F", 3],
        [2, 4, "F", 3],
        [4, 1, 3, 2, "F", 0],
        [8, 3, "H", 0],
        [9, 2, "P", 0],
        [10, 2, "H", 0],
        [11, 4, "P", 2],
        [12, 0, "H", 2],
        [13, 0, "F", 3],
        [14, 2, "F", 1],
        [15, 3, "H", 4],
        [8, 2, "F", 1],
        [17, 3, "H", 0],
        [18, 2, "P", 0],
        [19, 2, "H", 2],
        [20, 4, "F", 3],
        [20, 0, "P", 2],
        [22, 0, "H", 2],
        [23, 4, "F", 3],
        [23, 0, "F", 3],
        [16, 0, "P", 2],
        [9, 4, 0, 2, "T", 2],
        [4, 0, "F", 3],
    ]

    ret = _MetaTile([], H.width)
    shapes = {"H": H, "T": T, "P": P, "F": F}

    for r in rules:
        if len(r) == 1:
            ret.add_child(_IDENT, shapes[r[0]])
            continue
        if len(r) == 4:
            poly = ret.children[r[0]][1].shape
            Tm = ret.children[r[0]][0]
            p = _trans_pt(Tm, poly[(r[1] + 1) % len(poly)])
            q = _trans_pt(Tm, poly[r[1]])
            nshp = shapes[r[2]]
            npoly = nshp.shape
            ret.add_child(
                _match_two(npoly[r[3]], npoly[(r[3] + 1) % len(npoly)], p, q),
                nshp,
            )
            continue

        ch_p = ret.children[r[0]]
        ch_q = ret.children[r[2]]
        p = _trans_pt(ch_q[0], ch_q[1].shape[r[3]])
        q = _trans_pt(ch_p[0], ch_p[1].shape[r[1]])
        nshp = shapes[r[4]]
        npoly = nshp.shape
        ret.add_child(
            _match_two(npoly[r[5]], npoly[(r[5] + 1) % len(npoly)], p, q),
            nshp,
        )

    return ret


def _construct_metatiles(patch):
    bps1 = patch.eval_child(8, 2)
    bps2 = patch.eval_child(21, 2)
    rbps = _trans_pt(_aff_rot_about(bps1, -2.0 * math.pi / 3.0), bps2)

    p72 = patch.eval_child(7, 2)
    p252 = patch.eval_child(25, 2)

    llc = _intersect(bps1, rbps, patch.eval_child(6, 2), p72)
    w = _pt_sub(patch.eval_child(6, 2), llc)

    new_h_outline = [llc, bps1]
    w = _trans_pt(_aff_rot(-math.pi / 3), w)
    new_h_outline.append(_pt_add(new_h_outline[1], w))
    new_h_outline.append(patch.eval_child(14, 2))
    w = _trans_pt(_aff_rot(-math.pi / 3), w)
    new_h_outline.append(_pt_sub(new_h_outline[3], w))
    new_h_outline.append(patch.eval_child(6, 2))

    new_h = _MetaTile(new_h_outline, patch.width * 2.0)
    for idx in [0, 9, 16, 27, 26, 6, 1, 8, 10, 15]:
        new_h.add_child(*patch.children[idx])

    new_p_outline = [p72, _pt_add(p72, _pt_sub(bps1, llc)), bps1, llc]
    new_p = _MetaTile(new_p_outline, patch.width * 2.0)
    for idx in [7, 2, 3, 4, 28]:
        new_p.add_child(*patch.children[idx])

    new_f_outline = [
        bps2, patch.eval_child(24, 2), patch.eval_child(25, 0),
        p252, _pt_add(p252, _pt_sub(llc, bps1)),
    ]
    new_f = _MetaTile(new_f_outline, patch.width * 2.0)
    for idx in [21, 20, 22, 23, 24, 25]:
        new_f.add_child(*patch.children[idx])

    aaa = new_h_outline[2]
    bbb = _pt_add(new_h_outline[1], _pt_sub(new_h_outline[4], new_h_outline[5]))
    ccc = _trans_pt(_aff_rot_about(bbb, -math.pi / 3), aaa)
    new_t = _MetaTile([bbb, ccc, aaa], patch.width * 2.0)
    new_t.add_child(*patch.children[11])

    new_h.recenter()
    new_t.recenter()
    new_p.recenter()
    new_f.recenter()

    return new_h, new_t, new_p, new_f


def _flatten_hats(geom, T_world, out):
    if isinstance(geom, _BaseHat):
        a, b, tx, d, e, ty = T_world
        det = a * e - b * d
        scale = math.hypot(a, d)
        if scale == 0:
            return
        reflected = det < 0
        # Store the full affine transform — do NOT normalise tx/ty by scale.
        out.append((a, b, tx, d, e, ty, reflected))
        return

    for T_child, g_child in geom.children:
        _flatten_hats(g_child, _aff_mul(T_world, T_child), out)


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

    Builds an exact substitution tiling using the H/T/P/F metatile
    hierarchy from the Hat construction.

    Parameters
    ----------
    iterations : int
        Number of substitution iterations (default: 3).
        Tile count in the rendered H-metatile patch grows rapidly with
        each iteration (e.g. 4, 25, 169, 1156, ...).
    progress : ProgressReporter or None
        Optional progress reporter (total should equal *iterations*).

    Returns
    -------
    list[tuple[float, float, float, float, float, float, bool]]
        Each element is ``(a, b, tx, d, e, ty, reflected)`` — the full
        affine transform (computed for the internal substitution hat)
        together with a reflection flag.
    """
    iterations = max(0, int(iterations))
    h_meta, t_meta, p_meta, f_meta = _build_initial_metatiles()

    for i in range(iterations):
        patch = _construct_patch(h_meta, t_meta, p_meta, f_meta)
        h_meta, t_meta, p_meta, f_meta = _construct_metatiles(patch)
        if progress is not None:
            progress.update(i + 1)

    if progress is not None:
        progress.update(iterations)

    tiles = []
    _flatten_hats(h_meta, _IDENT, tiles)
    return tiles


def render_hat_tiles(tiles, cx, cy, scale, clip_w, clip_h):
    """Convert tile descriptors to polygon vertex lists for rendering.

    Each tile descriptor carries the full affine transform produced by the
    substitution engine (computed for the internal substitution hat).  The
    rendering maps the canonical ``HAT_VERTICES`` polygon onto each tile
    position by:

    1. Computing the world-space centroid of the *internal* hat via the
       affine.
    2. Drawing the *canonical* hat centred at that world centroid with
       matching rotation, reflection, and scale.

    Parameters
    ----------
    tiles : list[tuple[float, float, float, float, float, float, bool]]
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

    scx, scy = _SUBST_CENTROID
    ccx, ccy = _CANON_CENTROID

    result = []
    for a_m, b_m, tx, d_m, e_m, ty, reflected in tiles:
        # World-space centroid from the internal substitution hat
        wc_x = a_m * scx + b_m * scy + tx
        wc_y = d_m * scx + e_m * scy + ty

        # Extract rotation angle and uniform scale from the affine
        sub_scale = math.hypot(a_m, d_m)
        if sub_scale == 0:
            continue
        angle = math.atan2(d_m / sub_scale, a_m / sub_scale)

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Render canonical hat centred at the world centroid
        verts = []
        for hx, hy in HAT_VERTICES:
            dx = (hx - ccx) * sub_scale
            dy = (hy - ccy) * sub_scale
            if reflected:
                dy = -dy
            rx = dx * cos_a - dy * sin_a + wc_x
            ry = dx * sin_a + dy * cos_a + wc_y
            verts.append((rx * scale + cx, ry * scale + cy))

        # Clip: keep tile if its centroid falls within bounds
        mx = sum(v[0] for v in verts) / len(verts)
        my = sum(v[1] for v in verts) / len(verts)
        if (cx - half_w <= mx <= cx + half_w and
                cy - half_h <= my <= cy + half_h):
            result.append((verts, reflected))
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
        Number of substitution iterations (default: 3).
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

    _pp = ProgressReporter(iterations, "Hat: iterations") if verbose else None
    raw_tiles = generate_hat_tiling(iterations, progress=_pp)
    if _pp:
        _pp.done()

    # Compute tile_scale from the actual tiling extent so that the full
    # patch fits comfortably inside the content area.
    scx, scy = _SUBST_CENTROID
    max_ext = 1.0
    for a_m, b_m, tx_m, d_m, e_m, ty_m, _r in raw_tiles:
        wc_x = a_m * scx + b_m * scy + tx_m
        wc_y = d_m * scx + e_m * scy + ty_m
        ext = max(abs(wc_x), abs(wc_y))
        if ext > max_ext:
            max_ext = ext
    # Add a hat-radius margin so edge tiles are fully visible
    hat_r = max(max(abs(x) for x, _ in HAT_VERTICES),
                max(abs(y) for _, y in HAT_VERTICES))
    max_ext += hat_r
    tile_scale = min(avail_w, avail_h) / 2 * 0.95 / max_ext

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
        help="Number of substitution iterations (default: 3).",
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
