#!/usr/bin/env python3
"""
Unified Poster Generator — generate all wall_tart posters in one command.

Usage:
    python generate_all.py [OPTIONS]

Generates all three posters (Sierpiński Triangle, Lorenz Attractor, and
Logistic Map) with shared common arguments and optional poster-specific
parameters.

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
"""

import argparse
import os
import sys

from poster_utils import BASE_HEIGHT_MM, BASE_WIDTH_MM, write_poster

from sierpinski_poster import generate_poster as generate_sierpinski
from lorenz_poster import generate_poster as generate_lorenz
from logistic_map_poster import generate_poster as generate_logistic


POSTER_NAMES = ("sierpinski", "lorenz", "logistic")


def build_arg_parser():
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate all wall_tart mathematical posters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python generate_all.py\n"
            "  python generate_all.py --format png --dpi 300 --output-dir ./output\n"
            "  python generate_all.py --posters sierpinski lorenz\n"
            "  python generate_all.py --sierpinski-depth 9 --lorenz-steps 500000\n"
        ),
    )

    # --- Which posters to generate ---
    parser.add_argument(
        "--posters", nargs="+", default=list(POSTER_NAMES),
        choices=POSTER_NAMES, metavar="NAME",
        help=(
            "Which posters to generate (default: all). "
            "Choices: sierpinski, lorenz, logistic."
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

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    os.makedirs(args.output_dir, exist_ok=True)

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
    }

    for name in args.posters:
        info = posters[name]
        filepath = os.path.join(
            args.output_dir, f"{info['filename']}.{args.format}"
        )

        print(f"Generating {info['label']} \u2026")
        svg = info["generate"](**info["kwargs"], **common_kwargs)

        write_poster(svg, args.format, filepath, dpi=args.dpi)
        print(f"  Saved to {filepath}")

    print(f"\nDone — {len(args.posters)} poster(s) generated.")


if __name__ == "__main__":
    main()
