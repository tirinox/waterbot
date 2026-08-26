# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.12.6 AS uv

FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend ./backend
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

RUN groupadd --system waterbot \
    && useradd --system --gid waterbot --home-dir /app waterbot \
    && install -d -o waterbot -g waterbot /app /data /tmp/matplotlib \
    && ln -s /data/db.json /app/db.json

WORKDIR /app
COPY --from=builder --chown=waterbot:waterbot /app/.venv ./.venv
COPY --chown=waterbot:waterbot backend ./backend

USER waterbot
EXPOSE 9421

CMD ["python", "backend/backend_main.py"]
