# syntax=docker/dockerfile:1.7
# ---------- builder: compile wheels (mysqlclient needs build tools) ----------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------- runtime ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEBUG=False
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmariadb3 netcat-openbsd curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && rm -rf /wheels
COPY --chown=app:app . .
COPY --chown=app:app docker/ca.pem /app/docker/ca.pem
RUN chmod +x docker/entrypoint.sh \
    && mkdir -p /app/staticfiles && chown app:app /app/staticfiles
USER app
# Collect static files at build time (needs a throw-away key only for this step)
RUN SECRET_KEY=build-only DEBUG=False python manage.py collectstatic --noinput
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ || exit 1
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "Business.wsgi:application", "--bind", "0.0.0.0:8000", "--access-logfile", "-"]
