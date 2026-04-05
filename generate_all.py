#!/usr/bin/env python3
"""
Unified Poster Generator — generate all wall_tart posters in one command.

Usage:
    python generate_all.py [OPTIONS]

Generates all six posters (Sierpiński Triangle, Lorenz Attractor, Logistic
Map, Mandelbrot Set, Double Pendulum, and Cellular Automata) with shared
common arguments and optional poster-specific parameters.

Examples:
    # Generate all posters with defaults (SVG, A2 size)
    python generate_all.py

    # Generate all posters as PNG at 300 dpi into an output directory
    python generate_all.py --format png --dpi 300 --output-dir ./output

    # Generate only the Sierpiński poster at high depth
    python generate_all.py --posters sierpinski --sierpinski-depth 9

    # Custom size with credit lines
    python generate_all.py --width 594 --height 841 \\
        --designed-by "Alice" --designed-for "the Science Museum"

    # Generate all posters in the blueprint theme
    python generate_all.py --theme blueprint --output-dir ./output

    # Generate every poster in every theme for visual review
    python generate_all.py --theme all --output-dir ./themes
"""

import argparse
import os
import sys

from poster_utils import (
    AVAILABLE_THEMES, BASE_HEIGHT_MM, BASE_WIDTH_MM, DEFAULT_THEME,
    write_poster,
)

from sierpinski_poster import generate_poster as generate_sierpinski
from lorenz_poster import generate_poster as generate_lorenz
from logistic_map_poster import generate_poster as generate_logistic
from mandelbrot_poster import generate_poster as generate_mandelbrot
from double_pendulum_poster import generate_poster as generate_double_pendulum
from cellular_automata_poster import generate_poster as generate_cellular_automata


POSTER_NAMES = ("sierpinski", "lorenz", "logistic", "mandelbrot",
                "double_pendulum", "cellular_automata")


def build_arg_parser():
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate all wall_tart mathematical posters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python generate_all.py\n"
            "  python generate_all.py --format png --dpi 300 --output-dir ./output\n"
            "  python generate_all.py --posters sierpinski lorenz mandelbrot\n"
            "  python generate_all.py --sierpinski-depth 9 --lorenz-steps 500000\n"
        ),
    )

    # --- Which posters to generate ---
    parser.add_argument(
        "--posters", nargs="+", default=list(POSTER_NAMES),
        choices=POSTER_NAMES, metavar="NAME",
        help=(
            "Which posters to generate (default: all). "
            "Choices: sierpinski, lorenz, logistic, mandelbrot, "
            "double_pendulum, cellular_automata."
        ),
    )

    # --- Common output arguments ---
    common = parser.add_argument_group("common output options")
    common.add_argument(
        "--output-dir", type=str, default=".", dest="output_dir",
        help="Directory for output files (default: current directory).",
    )
    common.add_argument(
        "--format", type=str, choices=["svg", "pdf", "png"], default="svg",
        help="Output format (default: svg).",
    )
    common.add_argument(
        "--dpi", type=int, default=150,
        help="Resolution for PNG output in dots per inch (default: 150).",
    )
    common.add_argument(
        "--width", type=float, default=BASE_WIDTH_MM,
        help=f"Poster width in mm (default: {BASE_WIDTH_MM}, A2).",
    )
    common.add_argument(
        "--height", type=float, default=BASE_HEIGHT_MM,
        help=f"Poster height in mm (default: {BASE_HEIGHT_MM}, A2).",
    )
    common.add_argument(
        "--designed-by", type=str, default=None, dest="designed_by",
        help="Designer credit, e.g. 'Alice and Bob'.",
    )
    common.add_argument(
        "--designed-for", type=str, default=None, dest="designed_for",
        help="Client / purpose credit, e.g. 'the Science Museum'.",
    )
    common.add_argument(
        "--theme", type=str, default=DEFAULT_THEME,
        choices=AVAILABLE_THEMES + ["all"],
        help=(
            f"Color theme (default: {DEFAULT_THEME}). "
            f"Choices: {', '.join(AVAILABLE_THEMES)}, all. "
            "Use 'all' to generate every poster in every theme."
        ),
    )

    # --- Poster-specific arguments ---
    sierpinski = parser.add_argument_group("Sierpiński Triangle options")
    sierpinski.add_argument(
        "--sierpinski-depth", type=int, default=7, dest="sierpinski_depth",
        help="Recursion depth (default: 7). Higher = more detail.",
    )

    lorenz = parser.add_argument_group("Lorenz Attractor options")
    lorenz.add_argument(
        "--lorenz-steps", type=int, default=200000, dest="lorenz_steps",
        help="Integration steps (default: 200000). Higher = more detail.",
    )

    logistic = parser.add_argument_group("Logistic Map options")
    logistic.add_argument(
        "--logistic-r-count", type=int, default=2000, dest="logistic_r_count",
        help="Number of r-parameter samples (default: 2000). Higher = finer.",
    )

    mandelbrot = parser.add_argument_group("Mandelbrot Set options")
    mandelbrot.add_argument(
        "--mandelbrot-resolution", type=int, default=80,
        dest="mandelbrot_resolution",
        help="Grid width in pixels (default: 80). Higher = finer.",
    )
    mandelbrot.add_argument(
        "--mandelbrot-max-iter", type=int, default=100,
        dest="mandelbrot_max_iter",
        help="Maximum escape iterations (default: 100).",
    )

    pendulum = parser.add_argument_group("Double Pendulum options")
    pendulum.add_argument(
        "--pendulum-steps", type=int, default=10000,
        dest="pendulum_steps",
        help="Integration steps (default: 10000). Higher = more detail.",
    )

    automata = parser.add_argument_group("Cellular Automata options")
    automata.add_argument(
        "--automata-cell-size", type=int, default=2,
        dest="automata_cell_size",
        help="Cell size in mm (default: 2).",
    )
    automata.add_argument(
        "--automata-generations", type=int, default=150,
        dest="automata_generations",
        help="Number of generations (default: 150).",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    os.makedirs(args.output_dir, exist_ok=True)

    # Determine which themes to generate
    themes = AVAILABLE_THEMES if args.theme == "all" else [args.theme]

    common_kwargs = {
        "width_mm": args.width,
        "height_mm": args.height,
        "designed_by": args.designed_by,
        "designed_for": args.designed_for,
    }

    posters = {
        "sierpinski": {
            "generate": generate_sierpinski,
            "kwargs": {"depth": args.sierpinski_depth},
            "filename": "sierpinski_poster",
            "label": f"Sierpiński Triangle (depth={args.sierpinski_depth})",
        },
        "lorenz": {
            "generate": generate_lorenz,
            "kwargs": {"steps": args.lorenz_steps},
            "filename": "lorenz_poster",
            "label": f"Lorenz Attractor (steps={args.lorenz_steps:,})",
        },
        "logistic": {
            "generate": generate_logistic,
            "kwargs": {"r_count": args.logistic_r_count},
            "filename": "logistic_map_poster",
            "label": f"Logistic Map (r_count={args.logistic_r_count:,})",
        },
        "mandelbrot": {
            "generate": generate_mandelbrot,
            "kwargs": {
                "resolution": args.mandelbrot_resolution,
                "max_iter": args.mandelbrot_max_iter,
            },
            "filename": "mandelbrot_poster",
            "label": (
                f"Mandelbrot Set (resolution={args.mandelbrot_resolution}, "
                f"max_iter={args.mandelbrot_max_iter})"
            ),
        },
        "double_pendulum": {
            "generate": generate_double_pendulum,
            "kwargs": {"steps": args.pendulum_steps},
            "filename": "double_pendulum_poster",
            "label": f"Double Pendulum (steps={args.pendulum_steps:,})",
        },
        "cellular_automata": {
            "generate": generate_cellular_automata,
            "kwargs": {
                "cell_size": args.automata_cell_size,
                "generations": args.automata_generations,
            },
            "filename": "cellular_automata_poster",
            "label": (
                f"Cellular Automata (cell_size={args.automata_cell_size}, "
                f"generations={args.automata_generations})"
            ),
        },
    }

    total = 0
    for theme in themes:
        suffix = f"_{theme}" if len(themes) > 1 else ""
        for name in args.posters:
            info = posters[name]
            filepath = os.path.join(
                args.output_dir,
                f"{info['filename']}{suffix}.{args.format}",
            )

            label = info["label"]
            if len(themes) > 1:
                label = f"{label} [{theme}]"
            print(f"Generating {label} \u2026")
            svg = info["generate"](
                **info["kwargs"], **common_kwargs, theme=theme,
            )

            write_poster(svg, args.format, filepath, dpi=args.dpi)
            print(f"  Saved to {filepath}")
            total += 1

    print(f"\nDone — {total} poster(s) generated.")


if __name__ == "__main__":
    main()
