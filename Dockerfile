FROM python:3.12-slim

# System dependencies for cairosvg (PDF export)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir cairosvg

WORKDIR /app
COPY sierpinski_poster.py lorenz_poster.py logistic_map_poster.py ./

ENTRYPOINT []