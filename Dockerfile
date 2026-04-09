# I'm guessing this dockerfile is now very out of date
# because of the transition to uv

FROM python:3.12-slim

# Install system dependencies (same as before)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy uv binary from the official lightweight image (fastest & cleanest way)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Enable some uv performance / reproducibility options
ENV UV_COMPILE_BYTECODE=1 
ENV UV_LINK_MODE=copy 
ENV UV_SYSTEM_PYTHON=1  
 # Install directly into system Python (ideal for containers)

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy your application code
COPY . .

# Optional: run as non-root user (recommended for security)
# RUN useradd -m -U appuser && chown -R appuser:appuser /app
# USER appuser

CMD ["uv", "run", "app.py"]
