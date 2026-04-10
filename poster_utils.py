#!/usr/bin/env python3
"""
Shared utilities for the wall_tart poster generators.

Provides SVG helpers, style constants, output helpers, layout helpers,
no-crossing annotation utilities, scaffold/finalize helpers, annotation
builders, a unified CLI runner, and common constants that are identical
across the Sierpiński, Lorenz, and Logistic Map posters.
"""

import argparse
import sys
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------

class ProgressReporter:
    """Lightweight terminal progress-bar that writes to *sys.stderr*.

    Usage::

        progress = ProgressReporter(total=steps, label="Lorenz: main")
        for _ in range(steps):
            # … do work …
            progress.update()
        progress.done()

    Parameters
    ----------
    total : int
        Total number of steps.
    label : str
        Short description shown to the left of the bar (≤ LABEL_WIDTH chars
        looks best).
    file : file-like or None
        Output stream.  Defaults to *sys.stderr*.
    """

    BAR_WIDTH = 28
    LABEL_WIDTH = 22

    def __init__(self, total, label="", file=None):
        self._total = max(total, 1)
        self._label = label
        self._file = file or sys.stderr
        self._current = 0
        self._last_pct = -1

    def update(self, current=None):
        """Advance the progress indicator.

        Call with an explicit *current* position (0-based count of completed
        steps) or with no arguments to increment by one step.
        """
        if current is not None:
            self._current = current
        else:
            self._current += 1
        pct = int(100 * self._current / self._total)
        if pct == self._last_pct:
            return
        self._last_pct = pct
        self._render(pct)

    def done(self):
        """Force display to 100 % and emit a trailing newline."""
        self._last_pct = -1
        self._render(100)
        print(file=self._file, flush=True)

    def _render(self, pct):
        filled = self.BAR_WIDTH * pct // 100
        arrow = ">" if filled < self.BAR_WIDTH else ""
        spaces = " " * (self.BAR_WIDTH - filled - len(arrow))
        bar = "=" * filled + arrow + spaces
        line = f"\r  {self._label:<{self.LABEL_WIDTH}} [{bar}] {pct:3d}%"
        print(line, end="", file=self._file, flush=True)


# ---------------------------------------------------------------------------
# Theming system
# ---------------------------------------------------------------------------

THEMES = {
    "classic": {
        "bg_color": "#FFFEF8",           # warm ivory paper
        "accent_color": "#8B0000",       # deep museum red
        "title_color": "#1C1C1C",        # dark title text
        "footer_primary": "#555555",     # footer primary text
        "footer_secondary": "#777777",   # footer secondary text
        "text_color": "#1C1C1C",         # general body text
        "border_color": "#1C1C1C",       # border strokes
        "content_primary": "#1C1C1C",    # primary visualization ink
        "content_secondary": "#2E5090",  # secondary visualization ink
    },
    "blueprint": {
        "bg_color": "#0A1628",           # deep cobalt blue
        "accent_color": "#00BFFF",       # cyan accent
        "title_color": "#FFFFFF",        # white title
        "footer_primary": "#8FAADC",     # light blue footer
        "footer_secondary": "#5B7DB1",   # muted blue footer
        "text_color": "#E0E8F0",         # off-white text
        "border_color": "#FFFFFF",       # white border
        "content_primary": "#E0E8F0",    # light lines on dark bg
        "content_secondary": "#5BC0EB",  # lighter blue
    },
    "chalkboard": {
        "bg_color": "#2B2B2B",           # charcoal gray
        "accent_color": "#FFB347",       # amber/yellow accent
        "title_color": "#F5F5DC",        # off-white title
        "footer_primary": "#C0B283",     # warm tan footer
        "footer_secondary": "#8B8B78",   # muted olive footer
        "text_color": "#F5F5DC",         # off-white text
        "border_color": "#F5F5DC",       # off-white border
        "content_primary": "#F5F5DC",    # chalk-white lines
        "content_secondary": "#A8D8EA",  # soft blue chalk
    },
}

AVAILABLE_THEMES = list(THEMES.keys())
DEFAULT_THEME = "classic"


def get_theme(name=None):
    """Return the colour dictionary for the named theme.

    Falls back to ``DEFAULT_THEME`` when *name* is ``None`` or not found.
    """
    if name is None:
        name = DEFAULT_THEME
    return THEMES.get(name, THEMES[DEFAULT_THEME])


# ---------------------------------------------------------------------------
# Style constants (classic defaults — kept for backward compatibility)
# ---------------------------------------------------------------------------

BG_COLOR = THEMES["classic"]["bg_color"]
ACCENT_COLOR = THEMES["classic"]["accent_color"]
TITLE_COLOR = THEMES["classic"]["title_color"]
FOOTER_PRIMARY_COLOR = THEMES["classic"]["footer_primary"]
FOOTER_SECONDARY_COLOR = THEMES["classic"]["footer_secondary"]

HEADER_FONT = "'Playfair Display', Georgia, 'Times New Roman', serif"
BODY_FONT = (
    "'Inter', 'Helvetica Neue', Arial, sans-serif, "
    "system-ui, -apple-system, 'Segoe UI', Roboto, "
    "'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol'"
)
SERIF = HEADER_FONT  # backward-compatible alias

ANNOTATION_STYLE = {
    "font-family": BODY_FONT,
    "fill": "#1C1C1C",
}

CALLOUT_LINE_STYLE = {
    "stroke": "#8B0000",
    "stroke-width": "0.5",
    "stroke-dasharray": "2,1.5",
    "marker-end": "url(#arrowhead)",
}

# Column centres as fractions of poster width (left, centre, right)
COLUMN_CENTERS = (0.15, 0.50, 0.85)


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

BASE_WIDTH_MM = 420       # A2 width — reference for w_scale
BASE_HEIGHT_MM = 594      # A2 height — reference for h_scale
CONTENT_TOP_MARGIN_FRAC = 0.05   # fraction of height below header rule
ANNO_START_FRAC = 0.70           # fraction of height where annotations begin


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


def _add_font_style(svg, ns):
    """Inject a <style> block that imports web fonts for consistent typography."""
    style = ET.SubElement(svg, f"{{{ns}}}style")
    style.text = (
        "@import url('https://fonts.googleapis.com/css2?"
        "family=Playfair+Display:ital,wght@0,400;0,700;1,400"
        "&family=Inter:wght@300;400;500&display=swap');"
    )
    return style


def _add_arrow_marker(svg, ns, accent_color=None):
    """Add a minimalist dot marker for callout leader lines.

    Uses a small solid circle instead of the traditional heavy arrowhead,
    giving an architectural, museum-quality feel.
    """
    if accent_color is None:
        accent_color = ACCENT_COLOR
    defs = ET.SubElement(svg, f"{{{ns}}}defs")
    marker = ET.SubElement(
        defs,
        f"{{{ns}}}marker",
        attrib={
            "id": "arrowhead",
            "markerWidth": "6",
            "markerHeight": "6",
            "refX": "3",
            "refY": "3",
            "orient": "auto",
        },
    )
    ET.SubElement(
        marker,
        f"{{{ns}}}circle",
        attrib={
            "cx": "3",
            "cy": "3",
            "r": "2",
            "fill": accent_color,
        },
    )
    return defs


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def draw_poster_header(svg, ns, width_mm, height_mm, w_scale, h_scale,
                       title, subtitle, designed_by=None, designed_for=None,
                       theme=None):
    """Draw title, subtitle, rule, and optional inline credits.

    Returns rule_y so the caller can place content below the rule.
    """
    t = get_theme(theme)
    title_y = height_mm * 0.047
    subtitle_y = height_mm * 0.064
    rule_y = height_mm * 0.074

    _text(
        svg, ns, width_mm / 2, title_y, title,
        **{
            "font-family": HEADER_FONT,
            "font-size": str(round(16 * w_scale, 2)),
            "fill": t["title_color"],
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, subtitle_y, subtitle,
        **{
            "font-family": BODY_FONT,
            "font-size": str(round(6 * w_scale, 2)),
            "fill": t["accent_color"],
            "text-anchor": "middle",
        },
    )

    # Thin rule beneath the header
    _line(
        svg, ns,
        width_mm * 0.15, rule_y,
        width_mm * 0.85, rule_y,
        stroke=t["accent_color"],
        **{"stroke-width": str(round(0.4 * w_scale, 3))},
    )

    # Header credits flanking the rule
    header_credit_y = rule_y + 5 * h_scale
    header_credit_style = {
        "font-family": BODY_FONT,
        "font-size": str(round(3.8 * w_scale, 2)),
        "font-style": "italic",
        "fill": t["footer_secondary"],
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
                       designed_by=None, designed_for=None, theme=None):
    """Draw footer text lines and optional credit.

    Returns footer_y (the y coordinate of the primary footer line).
    """
    t = get_theme(theme)
    footer_y = height_mm - 18 * h_scale
    footer_font = round(4 * w_scale, 2)
    footer_font_sm = round(3.5 * w_scale, 2)

    _text(
        svg, ns, width_mm / 2, footer_y, primary_line,
        **{
            "font-family": BODY_FONT,
            "font-size": str(footer_font),
            "fill": t["footer_primary"],
            "text-anchor": "middle",
        },
    )
    _text(
        svg, ns, width_mm / 2, footer_y + 6 * h_scale, secondary_line,
        **{
            "font-family": BODY_FONT,
            "font-size": str(footer_font_sm),
            "fill": t["footer_secondary"],
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
                "font-family": BODY_FONT,
                "font-size": str(footer_font_sm),
                "fill": t["footer_secondary"],
                "font-style": "italic",
                "text-anchor": "middle",
            },
        )

    return footer_y


def draw_poster_border(svg, ns, width_mm, height_mm, w_scale, theme=None):
    """Draw the decorative double border (outer + inner rect)."""
    t = get_theme(theme)
    border_w = round(0.8 * w_scale, 3)
    border_w_inner = round(0.2 * w_scale, 3)
    _rect(
        svg, ns, 4, 4, width_mm - 8, height_mm - 8,
        fill="none", stroke=t["border_color"],
        **{"stroke-width": str(border_w)},
    )
    _rect(
        svg, ns, 7, 7, width_mm - 14, height_mm - 14,
        fill="none", stroke=t["border_color"],
        **{"stroke-width": str(border_w_inner)},
    )


def draw_row_separator(parent, ns, width_mm, y, w_scale, opacity="0.5",
                       theme=None):
    """Draw a full-width separator line at y."""
    t = get_theme(theme)
    _line(
        parent, ns,
        width_mm * 0.15, y,
        width_mm * 0.85, y,
        stroke=t["accent_color"],
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


def draw_annotation_row(parent, ns, anno_y, col_centers, annotations, scale,
                        theme=None):
    """Draw annotation callouts in order, ensuring no arrows cross.

    col_centers: sorted list of 3 column-centre x values
    annotations: list of 3 (callable, target_x, target_y) tuples
    Each callable has signature: func(parent, ns, target_x, target_y, col_cx, anno_y, scale, theme=None)
    """
    for (func, tx, ty), col_cx in zip(
        assign_annotations_no_crossing(annotations), col_centers
    ):
        func(parent, ns, tx, ty, col_cx, anno_y, scale, theme=theme)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_svg(svg_root, filepath):
    """Write the SVG element tree to *filepath*."""
    tree = ET.ElementTree(svg_root)
    ET.indent(tree, space="  ")
    tree.write(filepath, encoding="unicode", xml_declaration=True)


def _require_cairosvg():
    """Import and return cairosvg, or exit with a helpful error message."""
    try:
        import cairosvg
        return cairosvg
    except ImportError:
        print(
            "Error: 'cairosvg' is required for PDF/PNG output.\n"
            "Install it with:  pip install cairosvg",
            file=sys.stderr,
        )
        sys.exit(1)


def write_pdf(svg_root, filepath):
    """Write the poster as PDF via cairosvg (must be installed)."""
    cairosvg = _require_cairosvg()
    svg_bytes = ET.tostring(svg_root, encoding="unicode", xml_declaration=True)
    cairosvg.svg2pdf(bytestring=svg_bytes.encode("utf-8"), write_to=filepath)


def write_png(svg_root, filepath, dpi=150):
    """Write the poster as PNG via cairosvg (must be installed).

    The pixel dimensions are derived from the SVG's declared width/height and
    the requested *dpi* so that the raster output faithfully represents the
    vector layout at the chosen resolution.
    """
    cairosvg = _require_cairosvg()
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
    """Add --output, --format, --dpi, --width, --height, --theme, --designed-by, --designed-for."""
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
        "--width", type=float, default=BASE_WIDTH_MM,
        help=f"Poster width in mm (default: {BASE_WIDTH_MM}, A2).",
    )
    parser.add_argument(
        "--height", type=float, default=BASE_HEIGHT_MM,
        help=f"Poster height in mm (default: {BASE_HEIGHT_MM}, A2).",
    )
    parser.add_argument(
        "--theme", type=str, default=DEFAULT_THEME,
        choices=AVAILABLE_THEMES,
        help=(
            f"Color theme (default: {DEFAULT_THEME}). "
            f"Choices: {', '.join(AVAILABLE_THEMES)}."
        ),
    )
    parser.add_argument(
        "--designed-by", type=str, default=None, dest="designed_by",
        help="Designer credit, e.g. 'Alice and Bob'.",
    )
    parser.add_argument(
        "--designed-for", type=str, default=None, dest="designed_for",
        help="Client / purpose credit, e.g. 'the Science Museum'.",
    )


# ---------------------------------------------------------------------------
# Poster scaffold and finalize helpers
# ---------------------------------------------------------------------------

def build_poster_scaffold(title, subtitle, width_mm=BASE_WIDTH_MM,
                          height_mm=BASE_HEIGHT_MM, designed_by=None,
                          designed_for=None, theme=None):
    """Set up common poster elements and return computed layout values.

    Creates the SVG root, background, header (title/subtitle/rule/credits),
    font style block, and callout marker.  Returns a dict with all the
    values a poster-specific ``generate_poster`` function needs to place
    its unique content.

    Returns
    -------
    dict
        Keys: ``svg``, ``ns``, ``w_scale``, ``h_scale``, ``rule_y``,
        ``width_mm``, ``height_mm``, ``designed_by``, ``designed_for``,
        ``theme``.
    """
    t = get_theme(theme)
    svg, ns = _svg_root(width_mm, height_mm)

    w_scale = width_mm / BASE_WIDTH_MM
    h_scale = height_mm / BASE_HEIGHT_MM

    # Font embedding
    _add_font_style(svg, ns)

    _rect(svg, ns, 0, 0, width_mm, height_mm, fill=t["bg_color"])

    rule_y = draw_poster_header(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        title=title,
        subtitle=subtitle,
        designed_by=designed_by,
        designed_for=designed_for,
        theme=theme,
    )

    _add_arrow_marker(svg, ns, accent_color=t["accent_color"])

    return {
        "svg": svg,
        "ns": ns,
        "w_scale": w_scale,
        "h_scale": h_scale,
        "rule_y": rule_y,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "designed_by": designed_by,
        "designed_for": designed_for,
        "theme": theme,
    }


def content_area(rule_y, width_mm, height_mm, margin_frac=0.10):
    """Compute the content area boundaries below the header.

    Parameters
    ----------
    rule_y : float
        Y-coordinate of the header rule line.
    width_mm, height_mm : float
        Poster dimensions in millimetres.
    margin_frac : float
        Horizontal margin as a fraction of width (default: 0.10).

    Returns
    -------
    dict
        Keys: ``min_top``, ``max_bot``, ``margin``, ``avail_w``, ``avail_h``.
    """
    min_top = rule_y + height_mm * CONTENT_TOP_MARGIN_FRAC
    max_bot = height_mm * ANNO_START_FRAC
    margin = width_mm * margin_frac
    avail_w = width_mm - 2 * margin
    avail_h = max_bot - min_top
    return {
        "min_top": min_top,
        "max_bot": max_bot,
        "margin": margin,
        "avail_w": avail_w,
        "avail_h": avail_h,
    }


def finalize_poster(svg, ns, width_mm, height_mm, w_scale, h_scale,
                    primary_line, secondary_line,
                    designed_by=None, designed_for=None, theme=None):
    """Draw the footer and border — the common closing of every poster."""
    draw_poster_footer(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=primary_line,
        secondary_line=secondary_line,
        designed_by=designed_by,
        designed_for=designed_for,
        theme=theme,
    )
    draw_poster_border(svg, ns, width_mm, height_mm, w_scale, theme=theme)


# ---------------------------------------------------------------------------
# Annotation builder helpers
# ---------------------------------------------------------------------------

def draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                           title, scale, theme=None, show_line=True):
    """Draw the common annotation callout elements.

    Creates a ``<g>`` group, draws the arrow line from the callout origin
    to the target point, a small accent circle, and the annotation title.

    Parameters
    ----------
    show_line : bool
        When False, skip drawing the dashed callout line (and its arrowhead)
        to the target point.  The accent circle and title are still rendered.

    Returns the group element so the caller can append body content.
    """
    t = get_theme(theme)
    callout = {
        "stroke": t["accent_color"],
        "stroke-width": "0.5",
        "stroke-dasharray": "2,1.5",
        "marker-end": "url(#arrowhead)",
    }
    anno_style = {
        "font-family": BODY_FONT,
        "fill": t["text_color"],
    }

    g = _group(parent, ns)

    arrow_y = anno_y - 8 * scale
    if show_line:
        _line(g, ns, col_cx, arrow_y, target_x, target_y, **callout)
    _circle(g, ns, col_cx, arrow_y, 1 * scale, fill=t["accent_color"])

    _text(g, ns, col_cx, anno_y + 2 * scale, title,
          **{**anno_style, "font-size": str(round(5 * scale, 2)),
             "fill": t["accent_color"], "text-anchor": "middle"})

    return g


def draw_annotation_body(g, ns, col_cx, anno_y, lines, scale, theme=None):
    """Draw the common annotation body text (multiline, below the title)."""
    t = get_theme(theme)
    anno_style = {
        "font-family": BODY_FONT,
        "fill": t["text_color"],
    }
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**anno_style, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )


# ---------------------------------------------------------------------------
# Unified CLI runner
# ---------------------------------------------------------------------------

def run_poster_main(build_arg_parser, generate_from_args, filename_prefix,
                    poster_label, argv=None):
    """Run the common CLI main() logic for any poster generator.

    Parameters
    ----------
    build_arg_parser : callable
        Factory that returns a configured ``argparse.ArgumentParser``.
    generate_from_args : callable
        Adapter that accepts a parsed ``argparse.Namespace`` and returns
        an SVG root element.  Typically calls the poster-specific
        ``generate_poster`` function with the relevant arguments.
    filename_prefix : str
        Default filename stem, e.g. ``"sierpinski_poster"``.
    poster_label : str
        Human-readable label printed while generating, e.g.
        ``"Sierpiński Triangle poster (depth=7)"``.
    argv : list[str] or None
        CLI arguments (defaults to ``sys.argv[1:]``).
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.output is None:
        args.output = f"{filename_prefix}.{args.format}"

    print(f"Generating {poster_label} \u2026")
    svg = generate_from_args(args)

    write_poster(svg, args.format, args.output, dpi=args.dpi)
    print(f"Saved to {args.output}")
