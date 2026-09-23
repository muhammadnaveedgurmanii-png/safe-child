# Safe Child — production image for Hugging Face Spaces (Docker, free tier).
#
# `reflex run --env prod` serves the compiled frontend AND the backend
# (websocket /_event, /ping, /_upload) from ONE server. The JS client rewrites
# the localhost api_url to the Space's own domain at runtime, so no reverse
# proxy is needed — the container only has to listen on 7860.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    REFLEX_TELEMETRY_ENABLED=false

# curl/unzip: reflex downloads bun on first boot to build the frontend.
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 7860

# Koyeb/Render inject $PORT at runtime; default 7860 (HF Spaces convention).
CMD ["sh", "-c", "reflex run --env prod --frontend-port ${PORT:-7860}"]
