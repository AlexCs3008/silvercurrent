# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Install uv from its official slim image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Pre-create the package dir so uv_build can resolve the project metadata.
RUN mkdir -p src/silvercurrent
COPY src/silvercurrent/__init__.py src/silvercurrent/__init__.py

RUN uv sync --frozen --no-dev

# Now copy the rest of the source.
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "silvercurrent.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
