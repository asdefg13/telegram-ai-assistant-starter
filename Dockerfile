FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first: this layer is cached until pyproject.toml changes.
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install ".[supabase]"

COPY app ./app

# Long polling needs no inbound port, and a non-root user costs nothing.
RUN useradd --create-home --uid 10001 botuser
USER botuser

CMD ["python", "-m", "app.main"]
