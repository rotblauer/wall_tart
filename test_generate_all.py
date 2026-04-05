#!/usr/bin/env python3
"""Tests for generate_all module."""

import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from generate_all import build_arg_parser, main, POSTER_NAMES


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
            ])
            assert os.path.exists(os.path.join(tmpdir, "sierpinski_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "lorenz_poster.svg"))
            assert os.path.exists(os.path.join(tmpdir, "logistic_map_poster.svg"))

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
