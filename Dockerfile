FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/dolr-ai/amorae-web"
LABEL org.opencontainers.image.description="Amorae — adult AI-chat web surface (Level-2 isolated from YRAL)"

# Pull the Debian security fixes published after the base image was built
# (openssl, perl, util-linux, sqlite… flagged by Trivy on 2026-10-05).
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 appuser && \
    useradd  --system --uid 1001 --gid appuser --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser app/ .

USER appuser

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "4"]
