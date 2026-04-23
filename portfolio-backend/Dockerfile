# ── build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV POETRY_VERSION=2.3.4 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd -m -u 1000 -s /bin/bash app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--no-server-header"]
