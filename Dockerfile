FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SESSION_NAME=/app/session/save \
    DOWNLOAD_PATH=/app/downloads

WORKDIR /app

COPY pyproject.toml README.md ./
COPY saveit/ ./saveit/
RUN pip install --no-cache-dir .

RUN addgroup -S app && \
    adduser -S app -G app && \
    mkdir -p /app/downloads /app/session && \
    chown -R app:app /app

USER app

VOLUME ["/app/downloads", "/app/session"]

CMD ["python", "-m", "saveit"]
