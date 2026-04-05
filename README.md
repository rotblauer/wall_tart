# Wall Tart — Museum-Quality Mathematical Poster Generators

A collection of Python tools that generate museum-quality, annotated vector posters of iconic mathematical objects — suitable for large-format printing (A2 and above).

---

## 🔺 Sierpiński Triangle Poster

![sierpinski-preview](docs/generated/sierpinski_poster.svg)

### Quick Start

```bash
git clone https://github.com/rotblauer/wall_tart.git
cd wall_tart

# Generate an SVG poster (no dependencies needed)
python sierpinski_poster.py
```

This creates **`sierpinski_poster.svg`** — an A2-sized (420 × 594 mm) annotated poster at depth 7 (2,187 triangles).

### Features

- **Museum-style annotations** with leader-line callouts:
  | Annotation | Description |
  |---|---|
  | **Self-Similarity** | Arrow pointing to a sub-triangle explaining how every part mirrors the whole. |
  | **Recursion** | Visual step-by-step diagram (depth 0 → 1 → 2) showing the removal rule. |
  | **Fractional Dimension** | Kid-friendly note on the Hausdorff dimension (~1.585 — not 1-D, not 2-D!). |
- **Educational panels** — a second row of mathematical connections:
  | Panel | Description |
  |---|---|
  | **Hidden in Pascal's Triangle** | Pascal's triangle mod 2 visualisation — odd entries form the Sierpiński pattern. |
  | **The Chaos Game** | Scatter-dot demo of the random vertex-jumping algorithm that produces the fractal. |
  | **The Area Paradox** | Formulas and mini diagrams showing area → 0 yet perimeter → ∞. |

### Options

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

---

## 🦋 Lorenz Attractor Poster

![lorenz-preview](docs/generated/lorenz_poster.svg)

### Quick Start

```bash
# Generate the Lorenz attractor poster (no dependencies needed)
python lorenz_poster.py
```

This creates **`lorenz_poster.svg`** — an A2-sized (420 × 594 mm) annotated poster with 200,000 integration steps. The 3D trajectory of the strange attractor is projected to 2D, showing the iconic "butterfly" shape with a second diverging trajectory in red that demonstrates sensitive dependence on initial conditions.

### Features

- **Millions of points** rendered via a 4th-order Runge-Kutta integrator for a smooth, visually striking trajectory.
- **Museum-style annotations** with leader-line callouts:
  | Annotation | Description |
  |---|---|
  | **The Butterfly Effect** | Highlights two trajectories that start 10⁻¹⁰ apart but diverge wildly — sensitive dependence on initial conditions. |
  | **The Two 'Wings'** | Points out the two unstable fixed points that the trajectory orbits around. |
  | **Infinite Complexity** | Notes how the line never intersects itself despite being trapped in a bounded space. |
- **Educational panels** — a second row of scientific context:
  | Panel | Description |
  |---|---|
  | **The Equations** | The three Lorenz ODEs with parameter values (σ = 10, ρ = 28, β = 8/3). |
  | **Deterministic Chaos** | Mini divergence plot showing two initially close trajectories separating over time. |
  | **A Weather Model** | The meteorological origins of the Lorenz system and why long-term weather prediction is impossible. |

### Options

| Flag | Default | Description |
|---|---|---|
| `--steps N` | `200000` | Number of integration steps. Higher = more detail. |
| `--output FILE` | `lorenz_poster.<fmt>` | Output file path. |
| `--format FMT` | `svg` | Output format: `svg` or `pdf`. |
| `--width MM` | `420` | Poster width in millimetres (A2 default). |
| `--height MM` | `594` | Poster height in millimetres (A2 default). |
| `--designed-by TEXT` | *(none)* | Designer credit, e.g. `'Alice and Bob'`. |
| `--designed-for TEXT` | *(none)* | Client / purpose credit, e.g. `'the Science Museum'`. |

### Steps vs. Detail

| Steps | Approx. Time (s) | Notes |
|---|---|---|
| 5,000 | < 1 | Quick preview |
| 50,000 | ~1 | Good detail |
| 200,000 | ~3 | Default — smooth, publication-quality |
| 1,000,000 | ~15 | Ultra-fine detail; larger file |

---

## 📈 Logistic Map Poster

![logistic-map-preview](docs/generated/logistic_map_poster.svg)

### Quick Start

```bash
# Generate the Logistic Map bifurcation poster (no dependencies needed)
python logistic_map_poster.py
```

This creates **`logistic_map_poster.svg`** — an A2-sized (420 × 594 mm) annotated poster with 2,000 r-parameter samples. The bifurcation diagram reveals how a simple population model transitions from stable equilibria through period doubling to full chaos, with surprising windows of order along the way.

### Features

- **Millions of points** plotted efficiently to capture fine bifurcation detail across 2,000+ r-parameter values.
- **Museum-style annotations** with leader-line callouts:
  | Annotation | Description |
  |---|---|
  | **Period Doubling Cascade** | Points to the distinct splits where the population alternates between 2, 4, 8… values — the road from order to chaos. |
  | **The Edge of Chaos** | Highlights the Feigenbaum point (r ≈ 3.5699) where the system becomes unpredictable. |
  | **Windows of Order** | A callout to the famous period-3 window at r ≈ 3.83, where brief moments of predictability emerge amid chaos. |
- **Educational panels** — a second row of mathematical context:
  | Panel | Description |
  |---|---|
  | **The Equation** | The logistic recurrence x_{n+1} = r·x_n(1 − x_n) with parameter ranges. |
  | **Feigenbaum's Constant** | The universal constant δ ≈ 4.669201… that governs all period-doubling cascades. |
  | **Population Biology** | Robert May's 1976 discovery that this simple model produces chaotic dynamics. |

### Options

| Flag | Default | Description |
|---|---|---|
| `--r-count N` | `2000` | Number of r-parameter samples. Higher = finer detail. |
| `--output FILE` | `logistic_map_poster.<fmt>` | Output file path. |
| `--format FMT` | `svg` | Output format: `svg` or `pdf`. |
| `--width MM` | `420` | Poster width in millimetres (A2 default). |
| `--height MM` | `594` | Poster height in millimetres (A2 default). |
| `--designed-by TEXT` | *(none)* | Designer credit, e.g. `'Alice and Bob'`. |
| `--designed-for TEXT` | *(none)* | Client / purpose credit, e.g. `'the Science Museum'`. |

### r-Count vs. Detail

| r-Count | Approx. Time (s) | Notes |
|---|---|---|
| 200 | < 1 | Quick preview |
| 2,000 | ~1 | Default — good balance of detail and speed |
| 5,000 | ~3 | High detail |
| 10,000 | ~6 | Ultra-fine detail; larger file |

---

## 🌀 Mandelbrot Set Poster

![mandelbrot-preview](docs/generated/mandelbrot_poster.svg)

### Quick Start

```bash
# Generate the Mandelbrot Set poster (no dependencies needed)
python mandelbrot_poster.py
```

This creates **`mandelbrot_poster.svg`** — an A2-sized (420 × 594 mm) annotated poster of the Mandelbrot Set with Julia set thumbnails. The escape-time algorithm colours each point by how quickly it diverges, revealing the iconic fractal boundary.

### Features

- **Escape-time colouring** renders the fractal boundary in a smooth gradient, with the set interior in dark ink.
- **Julia set thumbnails** — three representative Julia sets are displayed below the main image, each linked to its generating *c* parameter in the Mandelbrot plane.
- **Museum-style annotations** with leader-line callouts:
  | Annotation | Description |
  |---|---|
  | **Self-Similarity** | Zooming into the boundary reveals smaller copies of the whole set — infinite nesting at every scale. |
  | **Escape-Time Colouring** | Explains the algorithm: iterate z² + c and colour by how many steps until |z| > 2. |
  | **Julia Set Connection** | Each point *c* in the Mandelbrot set determines a unique Julia set — the poster visualises this correspondence. |
- **Educational panels** — a second row of mathematical context:
  | Panel | Description |
  |---|---|
  | **The Equation** | The defining iteration z_{n+1} = z_n² + c and what convergence/divergence means. |
  | **The Complex Plane** | What the axes represent: the real and imaginary parts of *c*. |
  | **Special Regions** | Famous features: the main cardioid, period-2 bulb, seahorse valley, and elephant valley. |

### Options

| Flag | Default | Description |
|---|---|---|
| `--resolution N` | `80` | Grid width in pixels. Higher = finer detail. |
| `--max-iter N` | `100` | Maximum escape iterations. Higher = more boundary detail. |
| `--output FILE` | `mandelbrot_poster.<fmt>` | Output file path. |
| `--format FMT` | `svg` | Output format: `svg`, `pdf`, or `png`. |
| `--width MM` | `420` | Poster width in millimetres (A2 default). |
| `--height MM` | `594` | Poster height in millimetres (A2 default). |
| `--designed-by TEXT` | *(none)* | Designer credit. |
| `--designed-for TEXT` | *(none)* | Client / purpose credit. |

---

## ⚛️ Double Pendulum Poster

![double-pendulum-preview](docs/generated/double_pendulum_poster.svg)

### Quick Start

```bash
# Generate the Double Pendulum poster (no dependencies needed)
python double_pendulum_poster.py
```

This creates **`double_pendulum_poster.svg`** — an A2-sized (420 × 594 mm) annotated poster showing the chaotic trajectory of a double pendulum. Three trajectories with nearly identical starting conditions diverge wildly, demonstrating sensitive dependence on initial conditions.

### Features

- **Three diverging trajectories** — starting angles differ by only 10⁻⁵ radians, yet the paths diverge dramatically.
- **4th-order Runge-Kutta integration** for accurate simulation of the coupled ODEs.
- **Museum-style annotations** with leader-line callouts:
  | Annotation | Description |
  |---|---|
  | **Sensitive Dependence** | How immeasurably small differences in initial conditions lead to completely different outcomes. |
  | **Phase Space** | The double pendulum lives in a 4-dimensional phase space (two angles, two angular velocities). |
  | **Energy Conservation** | Total energy is conserved — the motion is chaotic but not random. |
- **Educational panels** — a second row of scientific context:
  | Panel | Description |
  |---|---|
  | **The Equations** | The coupled ODEs of motion for the double pendulum system. |
  | **Chaos vs. Random** | Deterministic chaos looks random but is governed by exact equations. |
  | **Physical Systems** | Real-world chaotic systems: weather, planetary orbits, population dynamics. |

### Options

| Flag | Default | Description |
|---|---|---|
| `--steps N` | `10000` | Integration steps. Higher = longer trajectory. |
| `--output FILE` | `double_pendulum_poster.<fmt>` | Output file path. |
| `--format FMT` | `svg` | Output format: `svg`, `pdf`, or `png`. |
| `--width MM` | `420` | Poster width in millimetres (A2 default). |
| `--height MM` | `594` | Poster height in millimetres (A2 default). |
| `--designed-by TEXT` | *(none)* | Designer credit. |
| `--designed-for TEXT` | *(none)* | Client / purpose credit. |

---

## 🔲 Cellular Automata Poster

![cellular-automata-preview](docs/generated/cellular_automata_poster.svg)

### Quick Start

```bash
# Generate the Cellular Automata poster (no dependencies needed)
python cellular_automata_poster.py
```

This creates **`cellular_automata_poster.svg`** — an A2-sized (420 × 594 mm) annotated poster showcasing three elementary cellular automata (Rules 30, 90, and 110) side by side. Each starts from a single cell and evolves to reveal strikingly different patterns from simple rules.

### Features

- **Three classic rules** displayed side by side: Rule 30 (pseudo-random chaos), Rule 90 (Sierpiński triangle), and Rule 110 (Turing-complete computation).
- **Pixel-art aesthetic** — each cell is a crisp rectangle, producing distinctive triangular and complex patterns.
- **Museum-style annotations** with leader-line callouts:
  | Annotation | Description |
  |---|---|
  | **Rule 30** | Produces pseudo-random, chaotic output — used in Mathematica's random number generator. |
  | **Rule 90** | Generates the Sierpiński triangle, connecting to Pascal's triangle mod 2. |
  | **Rule 110** | Proven Turing-complete by Matthew Cook in 2004 — simple rules can perform any computation. |
- **Educational panels** — a second row of mathematical context:
  | Panel | Description |
  |---|---|
  | **How It Works** | The rule encoding: 8 possible neighbourhoods → 8-bit rule number (256 possible rules). |
  | **Wolfram's Classes** | Stephen Wolfram's four classes of cellular automata behaviour. |
  | **Computation** | Connection to universal computation and Wolfram's "A New Kind of Science." |

### Options

| Flag | Default | Description |
|---|---|---|
| `--cell-size N` | `2` | Cell size in mm. Smaller = more detail. |
| `--generations N` | `150` | Number of generations to simulate. |
| `--output FILE` | `cellular_automata_poster.<fmt>` | Output file path. |
| `--format FMT` | `svg` | Output format: `svg`, `pdf`, or `png`. |
| `--width MM` | `420` | Poster width in millimetres (A2 default). |
| `--height MM` | `594` | Poster height in millimetres (A2 default). |
| `--designed-by TEXT` | *(none)* | Designer credit. |
| `--designed-for TEXT` | *(none)* | Client / purpose credit. |

---

## Common Information

### Requirements

- **Python 3.8+** (uses only the standard library for SVG output).
- *(Optional)* [`cairosvg`](https://cairosvg.org/) for PDF export.

### Advanced Usage

```bash
# Sierpiński: higher depth and custom output
python sierpinski_poster.py --depth 9 --output my_poster.svg

# Lorenz: more integration steps
python lorenz_poster.py --steps 500000 --output lorenz_hires.svg

# Logistic Map: more r-parameter samples
python logistic_map_poster.py --r-count 5000 --output logistic_hires.svg

# Mandelbrot: higher resolution
python mandelbrot_poster.py --resolution 200 --max-iter 200 --output mandelbrot_hires.svg

# Double Pendulum: longer trajectory
python double_pendulum_poster.py --steps 50000 --output pendulum_hires.svg

# Cellular Automata: more generations with smaller cells
python cellular_automata_poster.py --generations 300 --cell-size 1 --output automata_hires.svg

# Generate PDFs directly (requires cairosvg)
pip install cairosvg
python sierpinski_poster.py --format pdf --output sierpinski.pdf
python lorenz_poster.py --format pdf --output lorenz.pdf
python logistic_map_poster.py --format pdf --output logistic_map.pdf
python mandelbrot_poster.py --format pdf --output mandelbrot.pdf
python double_pendulum_poster.py --format pdf --output double_pendulum.pdf
python cellular_automata_poster.py --format pdf --output cellular_automata.pdf

# Custom poster dimensions (width × height in mm)
python sierpinski_poster.py --width 594 --height 841   # A1 size
python lorenz_poster.py --width 594 --height 841
python logistic_map_poster.py --width 594 --height 841
python mandelbrot_poster.py --width 594 --height 841
python double_pendulum_poster.py --width 594 --height 841
python cellular_automata_poster.py --width 594 --height 841

# Add custom credit lines
python sierpinski_poster.py --designed-by "Alice" --designed-for "the Science Museum"
python lorenz_poster.py --designed-by "Alice" --designed-for "the Science Museum"
python logistic_map_poster.py --designed-by "Alice" --designed-for "the Science Museum"
python mandelbrot_poster.py --designed-by "Alice" --designed-for "the Science Museum"
python double_pendulum_poster.py --designed-by "Alice" --designed-for "the Science Museum"
python cellular_automata_poster.py --designed-by "Alice" --designed-for "the Science Museum"
```

### Generate All Posters at Once

Use `generate_all.py` to generate every poster in a single command. Common
arguments (size, format, DPI, credits) apply to all posters, while
poster-specific parameters can be set individually:

```bash
# Generate all six posters with default settings
python generate_all.py

# Generate all posters as PNG at 300 DPI into an output directory
python generate_all.py --format png --dpi 300 --output-dir ./output

# Generate only the Sierpiński and Lorenz posters
python generate_all.py --posters sierpinski lorenz

# Custom size, credits, and poster-specific parameters
python generate_all.py \
  --width 594 --height 841 \
  --designed-by "Alice" --designed-for "the Science Museum" \
  --sierpinski-depth 9 \
  --lorenz-steps 500000 \
  --logistic-r-count 5000 \
  --mandelbrot-resolution 200 \
  --pendulum-steps 50000 \
  --automata-generations 300 \
  --output-dir ./output
```

| Flag | Default | Description |
|---|---|---|
| `--posters NAME [NAME ...]` | all | Which posters: `sierpinski`, `lorenz`, `logistic`, `mandelbrot`, `double_pendulum`, `cellular_automata`. |
| `--output-dir DIR` | `.` | Directory for output files. |
| `--format FMT` | `svg` | Output format: `svg`, `pdf`, or `png`. |
| `--dpi N` | `150` | Resolution for PNG output. |
| `--width MM` | `420` | Poster width in mm. |
| `--height MM` | `594` | Poster height in mm. |
| `--designed-by TEXT` | *(none)* | Designer credit. |
| `--designed-for TEXT` | *(none)* | Client / purpose credit. |
| `--sierpinski-depth N` | `7` | Sierpiński recursion depth. |
| `--lorenz-steps N` | `200000` | Lorenz integration steps. |
| `--logistic-r-count N` | `2000` | Logistic Map r-parameter samples. |
| `--mandelbrot-resolution N` | `80` | Mandelbrot grid width in pixels. |
| `--mandelbrot-max-iter N` | `100` | Mandelbrot maximum escape iterations. |
| `--pendulum-steps N` | `10000` | Double Pendulum integration steps. |
| `--automata-cell-size N` | `2` | Cellular Automata cell size in mm. |
| `--automata-generations N` | `150` | Cellular Automata generations. |

### Running Tests

```bash
pip install pytest
pytest test_poster_utils.py test_sierpinski.py test_lorenz.py test_logistic_map.py test_mandelbrot.py test_double_pendulum.py test_cellular_automata.py test_generate_all.py -v
```

### Docker

Build and run the poster generators in a container (includes `cairosvg` for PDF):

```bash
# Build the image
docker build -t wall-tart .

# Generate all posters at once
docker run -v "$(pwd)/output:/app/output" \
  wall-tart python generate_all.py --output-dir output

# Generate Sierpiński poster
docker run -v "$(pwd)/output:/app/output" \
  wall-tart python sierpinski_poster.py --depth 7 --output output/sierpinski_poster.svg

# Generate Lorenz poster
docker run -v "$(pwd)/output:/app/output" \
  wall-tart python lorenz_poster.py --steps 200000 --output output/lorenz_poster.svg

# Generate Logistic Map poster
docker run -v "$(pwd)/output:/app/output" \
  wall-tart python logistic_map_poster.py --r-count 2000 --output output/logistic_map_poster.svg

# Generate Mandelbrot poster
docker run -v "$(pwd)/output:/app/output" \
  wall-tart python mandelbrot_poster.py --resolution 80 --output output/mandelbrot_poster.svg

# Generate Double Pendulum poster
docker run -v "$(pwd)/output:/app/output" \
  wall-tart python double_pendulum_poster.py --steps 10000 --output output/double_pendulum_poster.svg

# Generate Cellular Automata poster
docker run -v "$(pwd)/output:/app/output" \
  wall-tart python cellular_automata_poster.py --generations 150 --output output/cellular_automata_poster.svg
```

### CI / GitHub Actions

The repository includes two workflows:

**`ci.yml`** — runs on every push and pull request to `main`:
1. Runs the full test suite (`test_poster_utils.py`, `test_sierpinski.py`, `test_lorenz.py`, `test_logistic_map.py`, `test_mandelbrot.py`, `test_double_pendulum.py`, `test_cellular_automata.py`, and `test_generate_all.py`) with `pytest`.
2. Builds the Docker image.
3. Generates sample posters and uploads them as build artifacts.

**`update-readme-images.yml`** — runs on every push to `main` that touches the poster generators, `poster_utils.py`, `generate_all.py`, or the workflow itself (and can be triggered manually via `workflow_dispatch`):
1. Regenerates `docs/generated/sierpinski_poster.svg`, `docs/generated/lorenz_poster.svg`, `docs/generated/logistic_map_poster.svg`, `docs/generated/mandelbrot_poster.svg`, `docs/generated/double_pendulum_poster.svg`, and `docs/generated/cellular_automata_poster.svg`.
2. Commits and pushes the updated images back to `main` so the README always shows the current output.

### How It Works

**Sierpiński Triangle**:
1. An equilateral triangle is defined by its centre and side length.
2. An iterative stack replaces naive recursion — at each step the triangle is split into three sub-triangles (the middle is removed).
3. The filled triangles are written as `<polygon>` elements inside an SVG document.
4. Leader lines connect explanatory text blocks to specific regions of the fractal.

**Lorenz Attractor**:
1. The Lorenz system of three coupled ODEs is integrated using a 4th-order Runge-Kutta method.
2. The 3D trajectory is projected to 2D via a rotation matrix for an optimal viewing angle.
3. The trajectory is rendered as `<polyline>` elements, with a second diverging trajectory to illustrate the butterfly effect.
4. Leader lines connect annotated text blocks to specific dynamics of the system.

**Logistic Map**:
1. The logistic recurrence x_{n+1} = r·x_n(1 − x_n) is iterated for thousands of r values across [2.5, 4.0].
2. For each r, transient iterations are discarded before collecting steady-state values — producing the bifurcation diagram.
3. Each (r, x) point is rendered as a tiny `<circle>` element in the SVG, capturing period doubling, chaos, and windows of order.
4. Leader lines connect annotated text blocks to specific mathematical milestones on the diagram.

**Mandelbrot Set**:
1. For each pixel in the grid, the escape-time algorithm iterates z_{n+1} = z_n² + c until |z| > 2 or the maximum iteration count is reached.
2. Points inside the set (that never escape) are coloured dark; escaped points receive a smooth colour gradient based on iteration count.
3. Three Julia set thumbnails are computed similarly and displayed below the main fractal.
4. Leader lines connect annotations to features of the fractal boundary.

**Double Pendulum**:
1. The coupled ODEs of the double pendulum are integrated using a 4th-order Runge-Kutta method — the same approach used for the Lorenz attractor.
2. Three trajectories with nearly identical initial conditions (differing by 10⁻⁵ radians) are computed to demonstrate sensitive dependence.
3. The tip position of the second pendulum mass is traced as `<polyline>` elements in different colours.
4. Leader lines connect annotations explaining chaos, phase space, and energy conservation.

**Cellular Automata**:
1. Elementary cellular automata (Rules 30, 90, 110) are computed using bitwise operations: each 3-cell neighbourhood maps to the rule number's corresponding bit.
2. Starting from a single active cell, each generation produces a new row based on the rule.
3. Active cells are rendered as filled `<rect>` elements, producing distinctive pixel-art patterns.
4. Leader lines connect annotations describing each rule's unique behaviour and significance.

## License

[MIT](LICENSE)
