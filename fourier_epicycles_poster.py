#!/usr/bin/env python3
"""
Fourier Epicycles Poster Generator

Generates a museum-quality, annotated vector poster (SVG/PDF) of
Fourier Epicycles — the elegant technique of reconstructing arbitrary
periodic curves from a sum of rotating circles, rooted in Joseph
Fourier's 1807 insight that any periodic signal can be decomposed
into simple sinusoidal waves.

Usage:
    python fourier_epicycles_poster.py [OPTIONS]

Options:
    --num-circles N      Number of Fourier circles (default: 32)
    --output FILE        Output filename (default: fourier_epicycles_poster.svg)
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
    _multiline_text,
    _polyline,
    _rect,
    _text,
    _line,
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
# Fourier helpers (pure-Python DFT)
# ---------------------------------------------------------------------------

N_SAMPLES = 128


def sample_target_curve(n_samples=N_SAMPLES):
    """Sample a star/flower target curve parametrically.

    The curve is defined as:
        x(t) = R * cos(t) * (1 + 0.3*cos(5*t))
        y(t) = R * sin(t) * (1 + 0.3*cos(5*t))

    Parameters
    ----------
    n_samples : int
        Number of evenly-spaced sample points around [0, 2π).

    Returns
    -------
    tuple[list[float], list[float]]
        Two lists (x_vals, y_vals) of sampled coordinates.
    """
    R = 1.0
    x_vals = []
    y_vals = []
    for i in range(n_samples):
        t = 2 * math.pi * i / n_samples
        r = R * (1 + 0.3 * math.cos(5 * t))
        x_vals.append(r * math.cos(t))
        y_vals.append(r * math.sin(t))
    return x_vals, y_vals


def dft(x_vals, y_vals, progress=None):
    """Compute the Discrete Fourier Transform (pure Python).

    Parameters
    ----------
    x_vals, y_vals : list[float]
        Real-valued signal samples (treated as real + imaginary parts of a
        complex signal z_n = x_n + i·y_n).
    progress : ProgressReporter or None
        Optional progress reporter updated once per frequency bin.

    Returns
    -------
    list[tuple[int, float, float]]
        List of (frequency, amplitude, phase) tuples for each coefficient.
    """
    N = len(x_vals)
    result = []
    for k in range(N):
        re_sum = 0.0
        im_sum = 0.0
        for n in range(N):
            angle = 2 * math.pi * k * n / N
            re_sum += x_vals[n] * math.cos(angle) + y_vals[n] * math.sin(angle)
            im_sum += -x_vals[n] * math.sin(angle) + y_vals[n] * math.cos(angle)
        re_sum /= N
        im_sum /= N
        amp = math.sqrt(re_sum ** 2 + im_sum ** 2)
        phase = math.atan2(im_sum, re_sum)
        result.append((k, amp, phase))
        if progress is not None:
            progress.update()
    return result


def reconstruct_curve(coefficients, n_points=256):
    """Reconstruct a curve by summing epicycles.

    Parameters
    ----------
    coefficients : list[tuple[int, float, float]]
        Sorted Fourier coefficients (frequency, amplitude, phase).
    n_points : int
        Number of points to sample along [0, 2π).

    Returns
    -------
    list[tuple[float, float]]
        Reconstructed (x, y) points.
    """
    points = []
    for i in range(n_points):
        t = 2 * math.pi * i / n_points
        x = 0.0
        y = 0.0
        for freq, amp, phase in coefficients:
            x += amp * math.cos(freq * t + phase)
            y += amp * math.sin(freq * t + phase)
        points.append((x, y))
    return points


def epicycle_arms(coefficients, t):
    """Compute the cumulative arm positions at time *t*.

    Returns a list of (cx, cy) points tracing the chain of circles
    from the origin through each epicycle centre.

    Parameters
    ----------
    coefficients : list[tuple[int, float, float]]
        Sorted Fourier coefficients (frequency, amplitude, phase).
    t : float
        Time parameter in [0, 2π).

    Returns
    -------
    list[tuple[float, float]]
        Cumulative positions of each circle centre.
    """
    positions = [(0.0, 0.0)]
    cx, cy = 0.0, 0.0
    for freq, amp, phase in coefficients:
        cx += amp * math.cos(freq * t + phase)
        cy += amp * math.sin(freq * t + phase)
        positions.append((cx, cy))
    return positions


# ---------------------------------------------------------------------------
# Poster-specific colours
# ---------------------------------------------------------------------------

EPICYCLE_CIRCLE_COLOR = "#AAAAAA"
EPICYCLE_DOT_COLOR = "#555555"


# ---------------------------------------------------------------------------
# Annotation builders
# ---------------------------------------------------------------------------

def _annotation_amplitude(parent, ns, target_x, target_y,
                          col_cx, anno_y, scale=1, theme=None):
    """Annotation: amplitude & frequency of each circle."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Amplitude & Frequency", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "Each circle\u2019s radius equals the",
        "amplitude of one Fourier coefficient,",
        "while its rotation speed equals the",
        "frequency. Large circles dominate the",
        "overall shape; small, fast circles",
        "add fine detail and sharp corners.",
    ], scale, theme=theme)
    return g


def _annotation_phase(parent, ns, target_x, target_y,
                      col_cx, anno_y, scale=1, theme=None):
    """Annotation: phase alignment of each circle."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Phase Alignment", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "The starting angle of each circle",
        "\u2014 its phase \u2014 determines where on",
        "the orbit it begins tracing. Shift",
        "one phase and the whole shape warps.",
        "The DFT captures exactly the right",
        "phase for every frequency component.",
    ], scale, theme=theme)
    return g


def _annotation_convergence(parent, ns, target_x, target_y,
                            col_cx, anno_y, scale=1, theme=None):
    """Annotation: convergence — more circles, better approximation."""
    g = draw_annotation_header(parent, ns, col_cx, anno_y, target_x, target_y,
                               "Convergence", scale, theme=theme)
    draw_annotation_body(g, ns, col_cx, anno_y, [
        "More circles yield a better match,",
        "but even a handful capture the basic",
        "outline. This is the key insight of",
        "Fourier analysis: complex signals",
        "converge rapidly when decomposed",
        "into their strongest frequencies.",
    ], scale, theme=theme)
    return g


# ---------------------------------------------------------------------------
# Educational panel builders (second row)
# ---------------------------------------------------------------------------

def _panel_fourier_transform(parent, ns, col_cx, anno_y, scale=1):
    """Panel: the Fourier Transform explained."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "The Fourier Transform",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Any periodic signal can be broken",
        "into a sum of sine and cosine waves",
        "of different frequencies. The Fourier",
        "Transform finds the amplitude and",
        "phase of each wave. In the discrete",
        "case (DFT), N samples yield exactly",
        "N frequency components \u2014 a perfect,",
        "lossless representation of the data.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_ancient_astronomy(parent, ns, col_cx, anno_y, scale=1):
    """Panel: Ptolemy's epicycles and ancient astronomy."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Ancient Astronomy",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "Two millennia before Fourier, Ptolemy",
        "modelled planetary motion as circles",
        "riding on circles \u2014 epicycles. His",
        "system predicted positions remarkably",
        "well. In a deep sense, Ptolemy was",
        "performing a Fourier decomposition of",
        "orbital motion, centuries before the",
        "mathematics was formalised.",
    ]
    _multiline_text(
        g, ns, col_cx, anno_y + 9 * scale,
        lines, line_height=5 * scale,
        **{**ANNOTATION_STYLE, "font-size": str(round(3.8 * scale, 2)),
           "text-anchor": "middle"},
    )

    return g


def _panel_modern_applications(parent, ns, col_cx, anno_y, scale=1):
    """Panel: modern applications of Fourier analysis."""
    g = _group(parent, ns)

    _text(g, ns, col_cx, anno_y + 2 * scale,
          "Modern Applications",
          **{**ANNOTATION_STYLE, "font-size": str(round(5 * scale, 2)),
             "fill": ACCENT_COLOR, "text-anchor": "middle"})

    lines = [
        "JPEG compression discards high-",
        "frequency coefficients the eye won\u2019t",
        "miss. Music synthesisers build rich",
        "timbres from pure tones. MRI scanners",
        "reconstruct images from frequency-",
        "domain data. Wherever signals meet",
        "mathematics, the Fourier Transform",
        "is the essential tool.",
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

def generate_poster(num_circles=32, width_mm=BASE_WIDTH_MM,
                    height_mm=BASE_HEIGHT_MM, designed_by=None,
                    designed_for=None, theme=None, verbose=True):
    """Build and return the full poster as an ElementTree SVG root.

    Parameters
    ----------
    num_circles : int
        Number of Fourier circles to use for the full reconstruction
        (default: 32).
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
        title="Fourier Epicycles",
        subtitle="Drawing with circles upon circles",
        width_mm=width_mm, height_mm=height_mm,
        designed_by=designed_by, designed_for=designed_for,
        theme=theme,
    )
    svg, ns = sc["svg"], sc["ns"]
    w_scale, h_scale, rule_y = sc["w_scale"], sc["h_scale"], sc["rule_y"]

    # --- Content area ---
    ca = content_area(rule_y, width_mm, height_mm, margin_frac=0.10)
    min_top, max_bot = ca["min_top"], ca["max_bot"]
    avail_h = ca["avail_h"]

    # --- Column centres ---
    col1_cx, col2_cx, col3_cx = [width_mm * f for f in COLUMN_CENTERS]

    # Panel radius: fit within column width and available height
    panel_w = width_mm * 0.28
    label_gap = 10 * h_scale
    panel_max_r = min(panel_w / 2, (avail_h - label_gap) / 2) * 0.85

    # --- Compute Fourier data ---
    x_vals, y_vals = sample_target_curve(N_SAMPLES)
    _p = ProgressReporter(N_SAMPLES, "Fourier: DFT") if verbose else None
    coefficients = dft(x_vals, y_vals, progress=_p)
    if _p:
        _p.done()

    # Sort by amplitude descending and take top num_circles
    sorted_coeffs = sorted(coefficients, key=lambda c: c[1], reverse=True)
    full_coeffs = sorted_coeffs[:num_circles]
    partial_coeffs = sorted_coeffs[:5]

    # --- Reconstruct curves ---
    n_draw = 256
    original_pts = list(zip(x_vals, y_vals))
    full_pts = reconstruct_curve(full_coeffs, n_draw)
    partial_pts = reconstruct_curve(partial_coeffs, n_draw)

    # Compute scaling: find extent of original curve
    all_x = [p[0] for p in original_pts]
    all_y = [p[1] for p in original_pts]
    extent = max(
        max(abs(v) for v in all_x),
        max(abs(v) for v in all_y),
    )
    scale_factor = panel_max_r / extent if extent > 0 else 1.0

    # Vertical centre of the drawing area
    draw_cy = min_top + (avail_h - label_gap) / 2
    curve_color = t["accent_color"]
    primary_color = t["content_primary"]

    # --- Helper: transform points to poster space ---
    def to_poster(pts, cx, cy):
        return [
            (round(cx + p[0] * scale_factor, 2),
             round(cy + p[1] * scale_factor, 2))
            for p in pts
        ]

    # --- Draw the three panels ---
    epicycles_group = _group(svg, ns, id="epicycles")

    # -- Panel 1: Original curve --
    orig_poster = to_poster(original_pts, col1_cx, draw_cy)
    # Close the curve by appending the first point
    orig_poster.append(orig_poster[0])
    _polyline(epicycles_group, ns, orig_poster,
              stroke=primary_color,
              **{"stroke-width": str(round(0.8 * w_scale, 2))})

    # -- Panel 2: Full reconstruction with epicycle ghosts --
    full_poster = to_poster(full_pts, col2_cx, draw_cy)
    full_poster.append(full_poster[0])
    _polyline(epicycles_group, ns, full_poster,
              stroke=curve_color,
              **{"stroke-width": str(round(0.8 * w_scale, 2))})

    # Draw ghost circles at t=0
    arms = epicycle_arms(full_coeffs, 0.0)
    for i, (freq, amp, phase) in enumerate(full_coeffs):
        arm_cx = col2_cx + arms[i][0] * scale_factor
        arm_cy = draw_cy + arms[i][1] * scale_factor
        r = amp * scale_factor
        if r > 0.3 * w_scale:
            _circle(epicycles_group, ns,
                    round(arm_cx, 2), round(arm_cy, 2), round(r, 2),
                    fill="none",
                    stroke=EPICYCLE_CIRCLE_COLOR,
                    **{"stroke-width": str(round(0.25 * w_scale, 2)),
                       "opacity": "0.4"})
            _circle(epicycles_group, ns,
                    round(arm_cx, 2), round(arm_cy, 2),
                    round(0.6 * w_scale, 2),
                    fill=EPICYCLE_DOT_COLOR, opacity="0.5")

    # -- Panel 3: Partial reconstruction (5 circles) --
    partial_poster = to_poster(partial_pts, col3_cx, draw_cy)
    partial_poster.append(partial_poster[0])
    _polyline(epicycles_group, ns, partial_poster,
              stroke=t["content_secondary"],
              **{"stroke-width": str(round(0.8 * w_scale, 2))})

    # --- Panel labels ---
    label_y = draw_cy + panel_max_r + 8 * h_scale
    label_style = {
        "font-family": SERIF,
        "font-size": str(round(5 * w_scale, 2)),
        "fill": ACCENT_COLOR,
        "text-anchor": "middle",
    }
    _text(svg, ns, col1_cx, label_y, "Original Curve", **label_style)
    _text(svg, ns, col2_cx, label_y,
          f"Full Reconstruction ({num_circles} circles)", **label_style)
    _text(svg, ns, col3_cx, label_y, "5 Circles Only", **label_style)

    # --- Annotations ---
    anno_group = _group(svg, ns, id="annotations")

    anno_sep_y = max_bot + 12 * h_scale
    draw_row_separator(anno_group, ns, width_mm, anno_sep_y, w_scale,
                       opacity="0.5", theme=theme)

    anno_y = anno_sep_y + 18 * h_scale

    # Arrow targets: centre of each panel
    target_y = draw_cy

    draw_annotation_row(
        anno_group, ns, anno_y,
        [col1_cx, col2_cx, col3_cx],
        [
            (_annotation_amplitude, col1_cx, target_y),
            (_annotation_phase, col2_cx, target_y),
            (_annotation_convergence, col3_cx, target_y),
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

    _panel_fourier_transform(edu_group, ns, col1_cx, row2_y, w_scale)
    _panel_ancient_astronomy(edu_group, ns, col2_cx, row2_y, w_scale)
    _panel_modern_applications(edu_group, ns, col3_cx, row2_y, w_scale)

    finalize_poster(
        svg, ns, width_mm, height_mm, w_scale, h_scale,
        primary_line=(
            "Joseph Fourier\u2019s insight (1807): "
            "any periodic signal is a sum of simple waves."
        ),
        secondary_line=(
            f"Generated with {num_circles} circles  "
            f"\u00b7  {N_SAMPLES} sample points  "
            f"\u00b7  Pure-Python DFT"
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
        description="Generate an annotated Fourier Epicycles poster.",
    )
    parser.add_argument(
        "--num-circles", type=int, default=32, dest="num_circles",
        help="Number of Fourier circles (default: 32).",
    )
    add_common_poster_args(parser)
    return parser


def _generate_from_args(args):
    """Adapter: call generate_poster with parsed CLI arguments."""
    return generate_poster(
        num_circles=args.num_circles,
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
        filename_prefix="fourier_epicycles_poster",
        poster_label=(
            f"Fourier Epicycles poster "
            f"(num_circles={args.num_circles})"
        ),
        argv=argv,
    )


if __name__ == "__main__":
    main()
