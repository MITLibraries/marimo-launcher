FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Copy project metadata
COPY pyproject.toml uv.lock* ./

# Copy CLI source
COPY launcher ./launcher

# Install package into system python, includes "marimo-launcher" script
RUN uv pip install --system .

EXPOSE 2718

ENTRYPOINT ["marimo-launcher"]
CMD []
