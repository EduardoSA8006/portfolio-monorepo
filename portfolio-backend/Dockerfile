# ── build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3 AS builder

ENV POETRY_VERSION=2.3.4 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd -m -u 1000 -s /bin/bash app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=app:app . .

USER app

EXPOSE 8000

# exec form via `sh -c` so ${WEB_CONCURRENCY} is expanded at container
# boot (plain JSON-array exec form skips shell expansion). Default is 2,
# tuned for a 2-vCPU VPS — set WEB_CONCURRENCY in .env to override.
# `exec` replaces the shell with uvicorn so PID 1 receives signals.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --no-server-header"]
