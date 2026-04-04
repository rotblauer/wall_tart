# Sierpiński Triangle Poster Generator

A Python tool that generates a museum-quality, annotated vector poster of the **Sierpiński Triangle** fractal — suitable for large-format printing (A2 and above).

![poster-preview](https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Sierpinski_triangle.svg/220px-Sierpinski_triangle.svg.png)

## Features

- **High-resolution vector output** (SVG) that scales to any poster size.
- **Museum-style annotations** with leader-line callouts:
  | Annotation | Description |
  |---|---|
  | **Self-Similarity** | Arrow pointing to a sub-triangle explaining how every part mirrors the whole. |
  | **Recursion** | Visual step-by-step diagram (depth 0 → 1 → 2) showing the removal rule. |
  | **Fractional Dimension** | Kid-friendly note on the Hausdorff dimension (~1.585 — not 1-D, not 2-D!). |
- **Efficient iterative algorithm** — handles deep recursion depths without hitting Python's stack limit.
- Optional **PDF export** via `cairosvg`.

## Requirements

- **Python 3.8+** (uses only the standard library for SVG output).
- *(Optional)* [`cairosvg`](https://cairosvg.org/) for PDF export.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/rotblauer/wall_tart.git
cd wall_tart
```

### 2. Generate an SVG poster (no dependencies needed)

```bash
python sierpinski_poster.py
```

This creates **`sierpinski_poster.svg`** — an A2-sized (420 × 594 mm) annotated poster at depth 7 (2,187 triangles).

### 3. Open or print the SVG

Open the SVG in any modern browser (Chrome, Firefox, Safari) or a vector editor like [Inkscape](https://inkscape.org/) to view, export, or send to a large-format printer.

## Advanced Usage

```bash
# Custom recursion depth (more detail) and output file
python sierpinski_poster.py --depth 9 --output my_poster.svg

# Generate a PDF directly (requires cairosvg)
pip install cairosvg
python sierpinski_poster.py --format pdf --output sierpinski.pdf

# Custom poster dimensions (width × height in mm)
python sierpinski_poster.py --width 594 --height 841   # A1 size

# Add a custom credit line
python sierpinski_poster.py --designed-by "Alice and Bob" --designed-for "the Science Museum"
```

### All Options

| Flag | Default | Description |
|---|---|---|
| `--depth N` | `7` | Fractal recursion depth. Higher values produce more detail. |
| `--output FILE` | `sierpinski_poster.<fmt>` | Output file path. |
| `--format FMT` | `svg` | Output format: `svg` or `pdf`. |
| `--width MM` | `420` | Poster width in millimetres (A2 default). |
| `--height MM` | `594` | Poster height in millimetres (A2 default). |
| `--designed-by TEXT` | *(none)* | Designer credit, e.g. `'Alice and Bob'`. |
| `--designed-for TEXT` | *(none)* | Client / purpose credit, e.g. `'the Science Museum'`. |

### Depth vs. Triangle Count

| Depth | Triangles | Notes |
|---|---|---|
| 5 | 243 | Quick preview |
| 7 | 2,187 | Default — good balance of detail and speed |
| 9 | 19,683 | High detail |
| 11 | 177,147 | Very fine detail; larger file |

## Running Tests

```bash
pip install pytest
pytest test_sierpinski.py -v
```

## Docker

Build and run the poster generator in a container (includes `cairosvg` for PDF):

```bash
# Build the image
docker build -t sierpinski-poster .

# Generate an SVG poster
docker run -v "$(pwd)/output:/app/output" \
  sierpinski-poster --depth 7 --output output/sierpinski_poster.svg

# Generate a PDF poster
docker run -v "$(pwd)/output:/app/output" \
  sierpinski-poster --depth 9 --format pdf --output output/sierpinski.pdf
```

## CI / GitHub Actions

The repository includes a CI workflow (`.github/workflows/ci.yml`) that:

1. Runs the full test suite with `pytest`.
2. Builds the Docker image.
3. Generates a sample poster and uploads it as a build artifact.

## How It Works

1. **Geometry**: An equilateral triangle is defined by its centre and side length.
2. **Iteration**: An iterative stack replaces naive recursion — at each step the triangle is split into three sub-triangles (the middle is removed). This continues to the target depth.
3. **SVG Generation**: The filled triangles are written as `<polygon>` elements inside an SVG document using Python's built-in `xml.etree.ElementTree`.
4. **Annotations**: Leader lines (with arrowhead markers) connect explanatory text blocks to specific regions of the fractal.

## License

[MIT](LICENSE)
