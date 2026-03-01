# ---- builder: install dependencies via uv into .venv ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency manifests first to leverage Docker layer caching --
# dependencies change less often than source code
COPY pyproject.toml uv.lock ./

# Install runtime dependencies (no dev, no project itself yet)
RUN uv sync --frozen --no-dev --no-install-project

# Now copy the actual source code and install the project package
COPY bot/ bot/
COPY alembic/ alembic/
COPY alembic.ini ./
RUN uv sync --frozen --no-dev


# ---- runtime: minimal image with only what's needed to run ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the fully built virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source and migration files
COPY bot/ bot/
COPY alembic/ alembic/
COPY alembic.ini ./

# Ensure the venv's Python is used by default
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "bot"]
