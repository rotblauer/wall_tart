#!/usr/bin/env python3
"""Tests for generate_all module."""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from generate_all import build_arg_parser, main, POSTER_NAMES
from poster_utils import AVAILABLE_THEMES, DEFAULT_THEME


class TestBuildArgParser:
    def test_default_poster_list(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.posters == list(POSTER_NAMES)

    def test_select_single_poster(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--posters", "sierpinski"])
        assert args.posters == ["sierpinski"]

    def test_select_multiple_posters(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--posters", "sierpinski", "lorenz"])
        assert args.posters == ["sierpinski", "lorenz"]

    def test_default_format(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.format == "svg"

    def test_default_dimensions(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.width == 420
        assert args.height == 594

    def test_sierpinski_depth_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.sierpinski_depth == 7

    def test_lorenz_steps_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.lorenz_steps == 200000

    def test_logistic_r_count_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.logistic_r_count == 2000

    def test_mandelbrot_resolution_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.mandelbrot_resolution == 80

    def test_mandelbrot_max_iter_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.mandelbrot_max_iter == 100

    def test_pendulum_steps_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.pendulum_steps == 10000

    def test_automata_cell_size_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.automata_cell_size == 2

    def test_automata_generations_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.automata_generations == 150

    def test_fourier_num_circles_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.fourier_num_circles == 32

    def test_turing_grid_size_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.turing_grid_size == 60

    def test_turing_steps_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.turing_steps == 3000

    def test_penrose_subdivisions_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.penrose_subdivisions == 5

    def test_harmonograph_steps_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.harmonograph_steps == 10000

    def test_hat_iterations_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.hat_iterations == 3

    def test_koch_depth_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.koch_depth == 5

    def test_no_skip_flags_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        for name in POSTER_NAMES:
            assert getattr(args, f"no_{name}") is False

    def test_skip_mandelbrot(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--no-mandelbrot"])
        assert args.no_mandelbrot is True
        assert args.no_sierpinski is False

    def test_skip_multiple(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--no-lorenz", "--no-mandelbrot"])
        assert args.no_lorenz is True
        assert args.no_mandelbrot is True
        assert args.no_sierpinski is False

    def test_custom_output_dir(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--output-dir", "/tmp/out"])
        assert args.output_dir == "/tmp/out"


class TestMain:
    def test_generates_all_posters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--sierpinski-depth", "2",
                "--lorenz-steps", "500",
                "--logistic-r-count", "20",
                "--mandelbrot-resolution", "10",
                "--mandelbrot-max-iter", "10",
                "--pendulum-steps", "500",
                "--automata-generations", "10",
                "--fourier-num-circles", "5",
                "--turing-grid-size", "8",
                "--turing-steps", "10",
                "--penrose-subdivisions", "2",
                "--harmonograph-steps", "500",
                "--hat-iterations", "1",
                "--koch-depth", "2",
            ])
            assert os.path.exists(os.path.join(tmpdir, "sierpinski_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "lorenz_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "logistic_map_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "mandelbrot_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "double_pendulum_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "cellular_automata_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "fourier_epicycles_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "turing_patterns_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "penrose_tiling_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "harmonograph_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "hat_tiling_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "koch_snowflake_poster.svg"))

    def test_generates_single_poster(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--posters", "sierpinski",
                "--sierpinski-depth", "2",
            ])
            assert os.path.exists(os.path.join(tmpdir, "sierpinski_poster.svg"))
            assert not os.path.exists(os.path.join(tmpdir, "lorenz_poster.svg"))
            assert not os.path.exists(os.path.join(tmpdir, "logistic_map_poster.svg"))

    def test_output_files_are_valid_svg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--posters", "sierpinski",
                "--sierpinski-depth", "1",
            ])
            path = os.path.join(tmpdir, "sierpinski_poster.svg")
            tree = ET.parse(path)
            root = tree.getroot()
            assert root.tag.endswith("svg")

    def test_creates_output_dir(self):
        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, "new_subdir")
            main([
                "--output-dir", out,
                "--posters", "logistic",
                "--logistic-r-count", "20",
            ])
            assert os.path.isdir(out)
            assert os.path.exists(os.path.join(out, "logistic_map_poster.svg"))

    def test_custom_dimensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--posters", "sierpinski",
                "--sierpinski-depth", "1",
                "--width", "300",
                "--height", "400",
            ])
            path = os.path.join(tmpdir, "sierpinski_poster.svg")
            tree = ET.parse(path)
            root = tree.getroot()
            assert root.get("width") == "300.0mm"
            assert root.get("height") == "400.0mm"

    def test_default_theme(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.theme == DEFAULT_THEME

    def test_theme_blueprint(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--theme", "blueprint"])
        assert args.theme == "blueprint"

    def test_theme_all(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--theme", "all"])
        assert args.theme == "all"

    def test_generates_single_poster_with_theme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--posters", "sierpinski",
                "--sierpinski-depth", "1",
                "--theme", "blueprint",
            ])
            assert os.path.exists(os.path.join(tmpdir, "sierpinski_poster.svg"))

    def test_theme_all_generates_themed_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--posters", "sierpinski",
                "--sierpinski-depth", "1",
                "--theme", "all",
            ])
            for theme in AVAILABLE_THEMES:
                path = os.path.join(tmpdir, f"sierpinski_poster_{theme}.svg")
                assert os.path.exists(path), f"Missing {path}"

    def test_theme_all_file_content_valid_svg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--posters", "sierpinski",
                "--sierpinski-depth", "1",
                "--theme", "all",
            ])
            for theme in AVAILABLE_THEMES:
                path = os.path.join(tmpdir, f"sierpinski_poster_{theme}.svg")
                tree = ET.parse(path)
                root = tree.getroot()
                assert root.tag.endswith("svg")

    def test_skip_flag_excludes_poster(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            main([
                "--output-dir", tmpdir,
                "--sierpinski-depth", "2",
                "--lorenz-steps", "500",
                "--logistic-r-count", "20",
                "--mandelbrot-resolution", "10",
                "--mandelbrot-max-iter", "10",
                "--pendulum-steps", "500",
                "--automata-generations", "10",
                "--fourier-num-circles", "5",
                "--turing-grid-size", "8",
                "--turing-steps", "10",
                "--penrose-subdivisions", "2",
                "--harmonograph-steps", "500",
                "--hat-iterations", "1",
                "--koch-depth", "2",
                "--no-mandelbrot",
                "--no-lorenz",
            ])
            assert os.path.exists(os.path.join(tmpdir, "sierpinski_poster.svg"))
            assert not os.path.exists(os.path.join(tmpdir, "mandelbrot_poster.svg"))
            assert not os.path.exists(os.path.join(tmpdir, "lorenz_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "logistic_map_poster.svg"))

    def test_skip_all_generates_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skip_flags = [f"--no-{name.replace('_', '-')}"
                          for name in POSTER_NAMES]
            main(["--output-dir", tmpdir] + skip_flags)
            svg_files = [f for f in os.listdir(tmpdir) if f.endswith(".svg")]
            assert len(svg_files) == 0
