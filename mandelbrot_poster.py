#!/usr/bin/env python3
"""
Mandelbrot / Julia Sets Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of the
Mandelbrot Set — the iconic fractal that encodes infinite complexity in
the simple iteration z² + c, together with representative Julia set
thumbnails showing the intimate connection between the two.

Usage:
    python mandelbrot_poster.py [OPTIONS]

Options:
    --resolution N       Grid width in pixels (default: 80)
    --max-iter N         Maximum escape iterations (default: 100)
    --output FILE        Output filename (default: mandelbrot_poster.svg)
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
# Mandelbrot / Julia helpers
# ---------------------------------------------------------------------------

def mandelbrot_escape(c_real, c_imag, max_iter=100):
    """Return the escape iteration count for a Mandelbrot point.

    Iterates z_{n+1} = z_n² + c starting from z_0 = 0.  If |z| exceeds 2
    before *max_iter* iterations the point has escaped; otherwise it is
    considered part of the Mandelbrot set.

    Parameters
    ----------
    c_real, c_imag : float
        Real and imaginary parts of the complex parameter *c*.
    max_iter : int
        Maximum number of iterations before declaring the point in-set.

    Returns
    -------
    int
        Iteration count at escape (0 to *max_iter*).  A value equal to
        *max_iter* means the point did not escape.
    """
    zr, zi = 0.0, 0.0
    for n in range(max_iter):
        zr2 = zr * zr
        zi2 = zi * zi
        if zr2 + zi2 > 4.0:
            return n
        zi = 2.0 * zr * zi + c_imag
        zr = zr2 - zi2 + c_real
    return max_iter


def julia_escape(z_real, z_imag, c_real, c_imag, max_iter=100):
    """Return the escape iteration count for a Julia set point.

    Iterates z_{n+1} = z_n² + c with a fixed *c* and variable starting
    point *z_0 = z_real + z_imag·i*.

    Parameters
    ----------
    z_real, z_imag : float
        Real and imaginary parts of the starting point.
    c_real, c_imag : float
        Real and imaginary parts of the fixed Julia parameter.
    max_iter : int
        Maximum number of iterations.

    Returns
    -------
    int
        Iteration count at escape (0 to *max_iter*).
    """
    zr, zi = z_real, z_imag
    for n in range(max_iter):
        zr2 = zr * zr
        zi2 = zi * zi
        if zr2 + zi2 > 4.0:
            return n
        zi = 2.0 * zr * zi + c_imag
        zr = zr2 - zi2 + c_real
    return max_iter


def compute_mandelbrot_grid(x_min, x_max, y_min, y_max,
                            width, height, max_iter=100, progress=None):
    """Compute a 2-D grid of Mandelbrot escape values.

    Parameters
    ----------
    x_min, x_max : float
        Real-axis range.
    y_min, y_max : float
        Imaginary-axis range.
    width, height : int
        Grid dimensions (columns × rows).
    max_iter : int
        Maximum escape iterations.
    progress : ProgressReporter or None
        Optional progress reporter updated once per row.

    Returns
    -------
    list[list[int]]
        A *height* × *width* grid where each entry is an escape count.
    """
    grid = []
    for row in range(height):
        ci = y_min + (y_max - y_min) * row / max(height - 1, 1)
        row_data = []
        for col in range(width):
            cr = x_min + (x_max - x_min) * col / max(width - 1, 1)
            row_data.append(mandelbrot_escape(cr, ci, max_iter))
        grid.append(row_data)
        if progress is not None:
            progress.update()
    return grid


def compute_julia_grid(c_real, c_imag, x_min, x_max, y_min, y_max,
                       width, height, max_iter=100, progress=None):
    """Compute a 2-D grid of Julia set escape values.

    Parameters
    ----------
    c_real, c_imag : float
        Fixed Julia parameter.
    x_min, x_max : float
        Real-axis range for starting points.
    y_min, y_max : float
        Imaginary-axis range for starting points.
    width, height : int
        Grid dimensions (columns × rows).
    max_iter : int
        Maximum escape iterations.
    progress : ProgressReporter or None
        Optional progress reporter updated once per row.

    Returns
    -------
    list[list[int]]
        A *height* × *width* grid of escape counts.
    """
    grid = []
    for row in range(height):
        zi = y_min + (y_max - y_min) * row / max(height - 1, 1)
        row_data = []
        for col in range(width):
            zr = x_min + (x_max - x_min) * col / max(width - 1, 1)
            row_data.append(julia_escape(zr, zi, c_real, c_imag, max_iter))
        grid.append(row_data)
        if progress is not None:
            progress.update()
    return grid


def _escape_to_color(escape, max_iter, set_color="#1C1C1C"):
    """Map escape iteration to an RGB hex color."""
    if escape >= max_iter:
        return set_color
    t = escape / max_iter
    r = int(9 * (1 - t) * t * t * t * 255)
    g = int(15 * (1 - t) * (1 - t) * t * t * 255)
    b = int(8.5 * (1 - t) * (1 - t) * (1 - t) * t * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Poster-specific colour
# ---------------------------------------------------------------------------

DIAGRAM_COLOR = "#1C1C1C"  # near-black ink


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_self_similarity(parent, ns, target_x, target_y,
                                col_cx, anno_y, scale=1, theme=None):
    """Annotation: infinite self-similarity and zooming."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Infinite Self-Similarity", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Zoom into the boundary of the",
        "Mandelbrot set and you will find",
        "miniature copies of the whole set,",
        "each surrounded by its own filigree.",
        "This self-similarity continues to",
        "infinite depth — no two zooms alike.",
    ], scale, theme=theme)
    return g


def _annotation_escape_time(parent, ns, target_x, target_y,
                            col_cx, anno_y, scale=1, theme=None):
    """Annotation: escape-time colouring algorithm."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Escape-Time Colouring", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Each point is coloured by how many",
        "iterations it takes for |z| to",
        "exceed 2. Points that never escape",
        "are in the set (shown dark). The",
        "smooth colour gradient reveals the",
        "fractal boundary in vivid detail.",
    ], scale, theme=theme)
    return g


def _annotation_julia_connection(parent, ns, target_x, target_y,
                                 col_cx, anno_y, scale=1, theme=None):
    """Annotation: connection between Mandelbrot and Julia sets."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Julia Set Connection", scale, theme=theme,
                               show_line=False)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Every point c in the complex plane",
        "defines a unique Julia set. Points",
        "inside the Mandelbrot set produce",
        "connected Julia sets; points outside",
        "yield disconnected \u2018dust\u2019. The",
        "Mandelbrot set is their catalogue.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_equation(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the Mandelbrot iteration and its parameters."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Equation",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The Mandelbrot set is defined by",
        "iterating a single recurrence:",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    # Equation in italic — tspan dy used for subscripts (avoids Unicode subscript letters)
    eq_style = {
        **ANNOTATION_STYLE,
        "font-size": str(round(4.5 * scale, 2)),
        "font-style": "italic",
    }
    eq_y = anno_y + 24 * scale
    eq_x = col_cx - 24 * scale

    base_size = round(4.5 * scale, 2)
    sub_size = round(3.4 * scale, 2)
    sub_dy = round(1.8 * scale, 2)

    attrib = {"x": str(eq_x), "y": str(eq_y)}
    attrib.update(eq_style)
    eq_el = ET.SubElement(g, f"{{{ns}}}text", attrib=attrib)
    # z_{n+1} = z_n^2 + c  rendered with tspan dy offsets so subscripts
    # display correctly in all fonts and renderers (no Unicode subscript letters)
    for txt, dy, fs in [
        ("z",         None,     None),
        ("n+1",       sub_dy,   str(sub_size)),
        (" = z",     -sub_dy,   str(base_size)),
        ("n",         sub_dy,   str(sub_size)),
        ("\u00b2 + c", -sub_dy, str(base_size)),
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
            "z\u2080 = 0,   c \u2208 C",
            "In set if |z| stays \u2264 2 forever",
        ],
        line_height=5 * scale,
        **param_style,
    )

    return g


def _panel_complex_plane(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the complex plane and what the axes represent."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Complex Plane",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The horizontal axis represents the",
        "real part of c, and the vertical axis",
        "the imaginary part. Each pixel is a",
        "complex number c = a + bi. The set",
        "lives in a region roughly from",
        "\u22122.5 to 1 on the real axis and",
        "\u22121.1 to 1.1 on the imaginary axis,",
        "centred slightly left of the origin.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_special_regions(parent, ns, col_cx, anno_y, scale=1):
    """Panel: famous regions of the Mandelbrot set."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Special Regions",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "The large heart-shaped body is the",
        "main cardioid, where c produces a",
        "single attracting fixed point. The",
        "circular bulb to its left is the",
        "period-2 region. Between the bulbs",
        "lie intricate structures nicknamed",
        "\u2018Seahorse Valley\u2019 and \u2018Elephant",
        "Valley\u2019, rich with spiral filaments.",
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

def _add_ellipse_clip(svg, ns, clip_id, cx, cy, rx, ry):
    """Insert a ``<clipPath>`` containing an ellipse into the SVG ``<defs>``.

    Creates the ``<defs>`` element if it does not already exist in *svg*.

    Parameters
    ----------
    svg : Element
        The root ``<svg>`` element.
    ns : str
        SVG namespace URI.
    clip_id : str
        Unique ``id`` for the ``<clipPath>`` element.
    cx, cy : float
        Centre of the ellipse in poster coordinates (mm).
    rx, ry : float
        Horizontal and vertical radii of the ellipse (mm).

    Returns
    -------
    Element
        The newly created ``<clipPath>`` element.
    """
    defs = svg.find(f"{{{ns}}}defs")
    if defs is None:
        defs = ET.SubElement(svg, f"{{{ns}}}defs")
    clip = ET.SubElement(defs, f"{{{ns}}}clipPath", attrib={"id": clip_id})
    ET.SubElement(
        clip,
        f"{{{ns}}}ellipse",
        attrib={
            "cx": str(round(cx, 4)),
            "cy": str(round(cy, 4)),
            "rx": str(round(rx, 4)),
            "ry": str(round(ry, 4)),
        },
    )
    return clip


def _draw_grid(parent, ns, grid, max_iter, gx, gy, cell_w, cell_h,
               set_color="#1C1C1C", fade_edges=False):
    """Render a 2-D escape-time grid as coloured SVG rectangles.

    When *fade_edges* is True, cells with very low escape counts (far from
    the fractal boundary) are rendered with reduced opacity so outer regions
    blend smoothly into the poster background instead of forming abrupt dark
    rectangles.
    """
    # ~1/12 of max_iter provides a smooth fade zone at the grid edges
    fade_iters = max(1, max_iter // 12) if fade_edges else 0
    for row_idx, row_data in enumerate(grid):
        for col_idx, escape in enumerate(row_data):
            if fade_edges and escape == 0:
                continue
            color = _escape_to_color(escape, max_iter, set_color)
            extra = {}
            if fade_iters and 0 < escape < fade_iters and escape < max_iter:
                op = escape / fade_iters
                # Skip cells that would be nearly invisible (< 2 % opacity)
                if op < 0.02:
                    continue
                extra["fill-opacity"] = str(round(op, 3))
            _rect(parent, ns,
                  round(gx + col_idx * cell_w, 2),
                  round(gy + row_idx * cell_h, 2),
                  round(cell_w + 0.5, 2),
                  round(cell_h + 0.5, 2),
                  fill=color, **extra)


def _draw_julia_inset(parent, ns, panel_x, panel_y, panel_w, panel_h,
                      c_real, c_imag, label, marker_px, marker_py,
                      j_grid, max_iter, set_color, w_scale, h_scale,
                      line_stop_y=None, fade_edges=False, theme=None,
                      clip_path_id=None):
    """Draw a Julia set inset panel on the Mandelbrot poster.

    Renders the Julia grid inside a styled panel and places a small circular
    marker at the corresponding *c* point on the main fractal.

    Parameters
    ----------
    parent : Element
        SVG group to draw into.
    ns : str
        SVG namespace URI.
    panel_x, panel_y, panel_w, panel_h : float
        Position and size of the panel (poster coordinates, mm).
    c_real, c_imag : float
        Julia parameter *c*.
    label : str
        Caption text shown below the panel.
    marker_px, marker_py : float
        Poster-coordinate location of *c* on the main Mandelbrot grid.
    j_grid : list[list[int]]
        Precomputed Julia escape grid.
    max_iter : int
        Maximum escape iterations (used for colour mapping).
    set_color : str
        Hex colour for in-set pixels.
    w_scale, h_scale : float
        Poster scaling factors.
    line_stop_y : float or None
        Unused; retained for API compatibility.
    fade_edges : bool
        When True, cells with very low escape counts are rendered with
        reduced opacity and no solid panel background / border is drawn,
        so the Julia structure floats on the poster background.
    theme : str or None
        Poster theme name.
    clip_path_id : str or None
        When provided, the ``clip-path="url(#clip_path_id)"`` attribute is
        applied to the grid sub-group so the rendered cells are clipped to
        the pre-registered elliptical ``<clipPath>``.  The label, marker
        circle, and connector line are drawn outside the clip so they remain
        fully visible.
    """
    t = get_theme(theme)
    border_color = t["border_color"]
    bg_color = t["bg_color"]

    inset_group = _group(parent, ns)

    # --- Panel background (only when not fading edges) ---
    if not fade_edges:
        _rect(inset_group, ns, panel_x, panel_y, panel_w, panel_h,
              fill=bg_color, stroke="none",
              **{"fill-opacity": "0.90"})

    # --- Render Julia grid inside the panel ---
    j_rows = len(j_grid)
    j_cols = len(j_grid[0]) if j_rows > 0 else 1
    j_cell_w = panel_w / j_cols
    j_cell_h = panel_h / j_rows
    # Grid cells go into their own sub-group so the optional elliptical clip
    # only affects the fractal cells, not the label or marker circle.
    grid_group = _group(inset_group, ns)
    if clip_path_id:
        grid_group.set("clip-path", f"url(#{clip_path_id})")
    _draw_grid(grid_group, ns, j_grid, max_iter,
               panel_x, panel_y, j_cell_w, j_cell_h,
               set_color=set_color, fade_edges=fade_edges)

    # --- Panel border (only when not fading edges) ---
    if not fade_edges:
        _rect(inset_group, ns, panel_x, panel_y, panel_w, panel_h,
              fill="none", stroke=border_color,
              **{"stroke-width": str(round(0.45 * w_scale, 3))})

    # --- Caption label below the panel ---
    label_style = {
        "font-family": SERIF,
        "font-size": str(round(3.0 * w_scale, 2)),
        "fill": FOOTER_PRIMARY_COLOR,
        "text-anchor": "middle",
        "font-style": "italic",
    }
    _text(inset_group, ns,
          round(panel_x + panel_w / 2, 2),
          round(panel_y + panel_h + 4.5 * h_scale, 2),
          label, **label_style)

    # --- Circular marker at c on the main fractal ---
    marker_r = round(1.8 * w_scale, 2)
    _circle(inset_group, ns,
            round(marker_px, 2), round(marker_py, 2), marker_r,
            fill="none", stroke=border_color,
            **{"stroke-width": str(round(0.5 * w_scale, 3)),
               "opacity": "0.85"})
    # Centre dot
    _circle(inset_group, ns,
            round(marker_px, 2), round(marker_py, 2),
            round(0.6 * w_scale, 2),
            fill=border_color,
            **{"opacity": "0.85"})

    return inset_group


def generate_poster(resolution=80, max_iter=100,
                    width_mm=BASE_WIDTH_MM, height_mm=BASE_HEIGHT_MM,
                    designed_by=None, designed_for=None, theme=None, verbose=True):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    resolution : int
        Horizontal pixel count for the Mandelbrot grid.
    max_iter : int
        Maximum escape iterations for colouring.
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
    set_color = t["content_primary"]

    sc = build_poster_scaffold(
        "The Mandelbrot & Julia Sets",
        subtitle="Infinite complexity from z\u00b2 + c",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    margin, avail_w, avail_h = ca["margin"], ca["avail_w"], ca["avail_h"]

    # Main fractal expands to use the full available content height
    fractal_h = avail_h

    # --- Compute Mandelbrot grid ---
    mb_x_min, mb_x_max = -2.5, 1.0
    mb_y_min, mb_y_max = -1.1, 1.1
    mb_aspect = (mb_x_max - mb_x_min) / (mb_y_max - mb_y_min)
    grid_w = resolution
    grid_h = max(1, int(resolution / mb_aspect))

    _pm = ProgressReporter(grid_h, "Mandelbrot: grid") if verbose else None
    grid = compute_mandelbrot_grid(mb_x_min, mb_x_max, mb_y_min, mb_y_max,
                                   grid_w, grid_h, max_iter, progress=_pm)
    if _pm:
        _pm.done()

    # Fit grid into fractal area, centred
    cell_w = avail_w / grid_w
    cell_h = fractal_h / grid_h
    # Keep square-ish cells to avoid distortion
    cell_size = min(cell_w, cell_h)
    render_w = cell_size * grid_w
    render_h = cell_size * grid_h
    fractal_x = margin + (avail_w - render_w) / 2
    fractal_y = min_top + (fractal_h - render_h) / 2

    # --- Draw Mandelbrot set ---
    # Wrap the fractal cells in an elliptical clip to dissolve the hard
    # rectangular grid boundary.  The ellipse is sized to encompass the
    # full extent of the Mandelbrot set while clipping the featureless
    # corners of the rectangular render area.
    _add_ellipse_clip(
        svg, ns, "mandelbrotClip",
        cx=fractal_x + render_w / 2,
        cy=fractal_y + render_h / 2,
        rx=render_w / 2 * 0.87,
        ry=render_h / 2 * 0.98,
    )
    fractal_group = _group(svg, ns, id="fractal")
    fractal_group.set("clip-path", "url(#mandelbrotClip)")
    _draw_grid(fractal_group, ns, grid, max_iter,
               fractal_x, fractal_y, cell_size, cell_size,
               set_color=set_color, fade_edges=True)

    # --- Axis labels ---
    axis_style = {
        "font-family": SERIF,
        "font-size": str(round(4 * w_scale, 2)),
        "fill": FOOTER_PRIMARY_COLOR,
        "font-style": "italic",
    }
    _text(svg, ns, margin + avail_w / 2, min_top + fractal_h + 5 * h_scale,
          "Re(c)",
          **{**axis_style, "text-anchor": "middle"})
    y_label = _text(svg, ns, margin - 8 * w_scale,
                    min_top + fractal_h / 2, "Im(c)",
                    **{**axis_style, "text-anchor": "middle"})
    y_label.set("transform",
                f"rotate(-90, {margin - 8 * w_scale}, {min_top + fractal_h / 2})")

    # Helper: map Mandelbrot complex coords to poster pixel coordinates
    def _mb_to_poster(cr, ci):
        px = fractal_x + (cr - mb_x_min) / (mb_x_max - mb_x_min) * render_w
        py = fractal_y + (ci - mb_y_min) / (mb_y_max - mb_y_min) * render_h
        return (px, py)

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Self-similarity: point near a mini-brot on the real axis
    ss_target = _mb_to_poster(-1.76, 0.0)
    # Escape-time: point on the boundary
    et_target = _mb_to_poster(-0.16, 1.04)
    # Julia connection: point to the c-value marker of the first Julia set
    jc_target = _mb_to_poster(-0.7, 0.27015)

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_self_similarity, ss_target[0], ss_target[1]),
            (_annotation_escape_time, et_target[0], et_target[1]),
            (_annotation_julia_connection, jc_target[0], jc_target[1]),
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

    _panel_equation(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_complex_plane(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_special_regions(edu_group, ns, col3_cx, row2_y, w_scale)

    # --- Julia set inline panels (placed in inter-column gaps) ---
    # Following the same pattern as the logistic-map poster's zoom panels,
    # each Julia inset sits in the horizontal gap between adjacent annotation
    # columns.  Two panels per row × two annotation rows = four Julia sets.
    julia_group = _group(svg, ns, id="julia_sets")
    julia_cs = [
        (-0.7,   0.27015, "c = \u22120.70 + 0.27i"),
        (0.355,  0.355,   "c = 0.355 + 0.355i"),
        (-0.8,   0.156,   "c = \u22120.80 + 0.16i"),
        (0.285,  0.01,    "c = 0.285 + 0.01i"),
    ]

    julia_res = max(10, resolution // 3)
    julia_h_res = max(8, julia_res)

    # Dynamic sizing from the inter-column gap (works at any poster size)
    col_gap = col2_cx - col1_cx
    row1_avail_h = row2_sep_y - anno_sep_y
    panel_side = min(col_gap * 0.40, row1_avail_h * 0.65)

    # Horizontal centres: midpoints of each inter-column gap
    panel_cx_left = (col1_cx + col2_cx) / 2
    panel_cx_right = (col2_cx + col3_cx) / 2

    # Vertical centres: aligned with annotation text in each row
    panel_cy_r1 = anno_y + panel_side / 2 + 1 * h_scale
    panel_cy_r2 = row2_y + panel_side / 2 + 1 * h_scale

    julia_panel_specs = [
        (julia_cs[0], panel_cx_left,  panel_cy_r1, anno_sep_y),
        (julia_cs[1], panel_cx_right, panel_cy_r1, anno_sep_y),
        (julia_cs[2], panel_cx_left,  panel_cy_r2, row2_sep_y),
        (julia_cs[3], panel_cx_right, panel_cy_r2, row2_sep_y),
    ]

    for j_idx, ((cr, ci, label), pcx, pcy, stop_y) in enumerate(julia_panel_specs):
        _pj = ProgressReporter(julia_h_res, f"Julia: {label[:16]}") if verbose else None
        j_grid = compute_julia_grid(cr, ci, -1.5, 1.5, -1.2, 1.2,
                                    julia_res, julia_h_res, max_iter, progress=_pj)
        if _pj:
            _pj.done()
        marker_px, marker_py = _mb_to_poster(cr, ci)
        # Elliptical clip for this Julia inset — clips only the grid cells so
        # labels and marker circles remain fully visible outside the clip region.
        julia_clip_id = f"juliaClip{j_idx}"
        _add_ellipse_clip(
            svg, ns, julia_clip_id,
            cx=pcx,
            cy=pcy,
            rx=panel_side / 2 * 0.90,
            ry=panel_side / 2 * 0.90,
        )
        _draw_julia_inset(
            julia_group, ns,
            panel_x=pcx - panel_side / 2,
            panel_y=pcy - panel_side / 2,
            panel_w=panel_side, panel_h=panel_side,
            c_real=cr, c_imag=ci,
            label=label,
            marker_px=marker_px, marker_py=marker_py,
            j_grid=j_grid,
            max_iter=max_iter,
            set_color=set_color,
            w_scale=w_scale, h_scale=h_scale,
            line_stop_y=stop_y,
            fade_edges=True,
            theme=theme,
            clip_path_id=julia_clip_id,
        )

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Discovered by Benoît Mandelbrot in 1980, "
            "this set reveals nature\u2019s hidden geometry."
        ),
        secondary_line=(
            f"Generated with {resolution}\u00d7{grid_h} grid  "
            f"\u00b7  max {max_iter} iterations  "
            f"\u00b7  {len(julia_cs)} Julia set insets at {julia_res}\u00d7{julia_h_res}"
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
        description="Generate an annotated Mandelbrot / Julia Sets poster.",
    )
    parser.add_argument(
        "--resolution", type=int, default=80, dest="resolution",
        help="Grid width in pixels (default: 80). Higher = finer.",
    )
    parser.add_argument(
        "--max-iter", type=int, default=100, dest="max_iter",
        help="Maximum escape iterations (default: 100). Higher = more detail.",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        resolution=args.resolution,
        max_iter=args.max_iter,
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
        filename_prefix="mandelbrot_poster",
        poster_label=(
            f"Mandelbrot poster "
            f"(resolution={args.resolution}, max_iter={args.max_iter})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
