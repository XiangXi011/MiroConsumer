FROM python:3.12-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

RUN groupadd --gid 10001 miroconsumer \
    && useradd --uid 10001 --gid miroconsumer --create-home --home-dir /app --shell /usr/sbin/nologin miroconsumer \
    && mkdir -p /app/backend \
    && chown -R miroconsumer:miroconsumer /app

WORKDIR /app/backend

COPY --chown=miroconsumer:miroconsumer backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY --chown=miroconsumer:miroconsumer backend ./

USER miroconsumer

EXPOSE 5001

CMD ["sh", "-c", "gunicorn 'app:create_app()' --bind 0.0.0.0:5001 --workers ${GUNICORN_WORKERS:-4} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-300} --access-logfile - --error-logfile -"]
