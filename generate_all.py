#!/usr/bin/env python3
"""
Unified Poster Generator — generate all wall_tart posters in one command.

Usage:
    python generate_all.py [OPTIONS]

Generates all twelve posters (Sierpiński Triangle, Lorenz Attractor, Logistic
Map, Mandelbrot Set, Double Pendulum, Cellular Automata, Fourier
Epicycles, Turing Patterns, Penrose Tiling, Harmonograph, Hat Monotile,
and Koch Snowflake) with shared common arguments and optional
poster-specific parameters.

Examples:
    # Generate all posters with defaults (SVG, A2 size)
    python generate_all.py

    # Generate all posters as PNG at 300 dpi into an output directory
    python generate_all.py --format png --dpi 300 --output-dir ./output

    # Generate only the Sierpiński poster at high depth
    python generate_all.py --posters sierpinski --sierpinski-depth 9

    # Skip specific posters
    python generate_all.py --no-mandelbrot --no-lorenz

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
from fourier_epicycles_poster import generate_poster as generate_fourier_epicycles
from turing_patterns_poster import generate_poster as generate_turing_patterns
from penrose_tiling_poster import generate_poster as generate_penrose_tiling
from harmonograph_poster import generate_poster as generate_harmonograph
from hat_tiling_poster import generate_poster as generate_hat_tiling
from koch_snowflake_poster import generate_poster as generate_koch_snowflake


POSTER_NAMES = ("sierpinski", "lorenz", "logistic", "mandelbrot",
                "double_pendulum", "cellular_automata", "fourier_epicycles",
                "turing_patterns", "penrose_tiling", "harmonograph",
                "hat_tiling", "koch_snowflake")


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
            "double_pendulum, cellular_automata, fourier_epicycles, "
            "turing_patterns, penrose_tiling, harmonograph, "
            "hat_tiling, koch_snowflake."
        ),
    )

    # --- Skip flags: --no-<poster> to exclude individual posters ---
    skip = parser.add_argument_group("skip options")
    for name in POSTER_NAMES:
        skip.add_argument(
            f"--no-{name.replace('_', '-')}", action="store_true",
            dest=f"no_{name}",
            help=f"Skip the {name.replace('_', ' ')} poster.",
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

    fourier = parser.add_argument_group("Fourier Epicycles options")
    fourier.add_argument(
        "--fourier-num-circles", type=int, default=32,
        dest="fourier_num_circles",
        help="Number of Fourier circles (default: 32).",
    )

    turing = parser.add_argument_group("Turing Patterns options")
    turing.add_argument(
        "--turing-grid-size", type=int, default=60,
        dest="turing_grid_size",
        help="Grid width/height (default: 60).",
    )
    turing.add_argument(
        "--turing-steps", type=int, default=3000,
        dest="turing_steps",
        help="Simulation steps (default: 3000).",
    )

    penrose = parser.add_argument_group("Penrose Tiling options")
    penrose.add_argument(
        "--penrose-subdivisions", type=int, default=5,
        dest="penrose_subdivisions",
        help="Number of subdivisions (default: 5).",
    )

    harmonograph_group = parser.add_argument_group("Harmonograph options")
    harmonograph_group.add_argument(
        "--harmonograph-steps", type=int, default=10000,
        dest="harmonograph_steps",
        help="Simulation steps (default: 10000).",
    )

    hat = parser.add_argument_group("Hat Monotile options")
    hat.add_argument(
        "--hat-iterations", type=int, default=3,
        dest="hat_iterations",
        help="Number of cluster expansion iterations (default: 3).",
    )

    koch = parser.add_argument_group("Koch Snowflake options")
    koch.add_argument(
        "--koch-depth", type=int, default=5,
        dest="koch_depth",
        help="Koch curve recursion depth (default: 5).",
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
        "fourier_epicycles": {
            "generate": generate_fourier_epicycles,
            "kwargs": {"num_circles": args.fourier_num_circles},
            "filename": "fourier_epicycles_poster",
            "label": (
                f"Fourier Epicycles "
                f"(num_circles={args.fourier_num_circles})"
            ),
        },
        "turing_patterns": {
            "generate": generate_turing_patterns,
            "kwargs": {
                "grid_size": args.turing_grid_size,
                "steps": args.turing_steps,
            },
            "filename": "turing_patterns_poster",
            "label": (
                f"Turing Patterns (grid_size={args.turing_grid_size}, "
                f"steps={args.turing_steps})"
            ),
        },
        "penrose_tiling": {
            "generate": generate_penrose_tiling,
            "kwargs": {"subdivisions": args.penrose_subdivisions},
            "filename": "penrose_tiling_poster",
            "label": (
                f"Penrose Tiling "
                f"(subdivisions={args.penrose_subdivisions})"
            ),
        },
        "harmonograph": {
            "generate": generate_harmonograph,
            "kwargs": {"steps": args.harmonograph_steps},
            "filename": "harmonograph_poster",
            "label": (
                f"Harmonograph "
                f"(steps={args.harmonograph_steps:,})"
            ),
        },
        "hat_tiling": {
            "generate": generate_hat_tiling,
            "kwargs": {"iterations": args.hat_iterations},
            "filename": "hat_tiling_poster",
            "label": (
                f"Hat Monotile "
                f"(iterations={args.hat_iterations})"
            ),
        },
        "koch_snowflake": {
            "generate": generate_koch_snowflake,
            "kwargs": {"depth": args.koch_depth},
            "filename": "koch_snowflake_poster",
            "label": (
                f"Koch Snowflake "
                f"(depth={args.koch_depth})"
            ),
        },
    }

    # Apply --no-<poster> skip flags
    selected = [name for name in args.posters
                if not getattr(args, f"no_{name}", False)]

    total = 0
    for theme in themes:
        suffix = f"_{theme}" if len(themes) > 1 else ""
        for name in selected:
            info = posters[name]
            filepath = os.path.join(
                args.output_dir,
                f"{info['filename']}{suffix}.{args.format}",
            )

            label = info["label"]
            if len(themes) > 1:
                label = f"{label} [{theme}]"
            print(f"Generating {label} \u2026", flush=True)
            svg = info["generate"](
                **info["kwargs"], **common_kwargs, theme=theme,
            )

            write_poster(svg, args.format, filepath, dpi=args.dpi)
            print(f"  Saved to {filepath}")
            total += 1

    print(f"\nDone — {total} poster(s) generated.")


if __name__ == "__main__":
    main()
