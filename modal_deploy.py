"""Deploy Safe Child to Modal (free tier, no credit card required).

Usage:
    export MODAL_TOKEN_ID=... MODAL_TOKEN_SECRET=...   # from https://modal.com/settings
    export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    # optional: export SUPABASE_URL=... SUPABASE_KEY=...
    modal deploy modal_deploy.py

What it does:
- Builds a Modal image with the app code, pip deps, and a pre-built Reflex
  production frontend (bun + vite run once at image build time).
- Serves the Reflex ASGI app (compiled frontend mounted + backend websocket
  /_event, /ping, /_upload on one endpoint) via @modal.asgi_app().
- WebSockets are supported by Modal's ASGI infrastructure; the Reflex JS
  client rewrites its localhost api_url to the endpoint's own domain.
- Scale-to-zero: the container stops when idle, so the $5/mo no-card free
  tier comfortably covers a low-traffic demo app.

No secrets are stored in this file; they are read from the environment at
deploy time and stored as a Modal Secret.
"""

import os

import modal

APP_NAME = "safe-child"

image = (
    modal.Image.debian_slim(python_version="3.12")
    # curl/unzip: reflex downloads bun on first use to build the frontend.
    .apt_install("curl", "unzip")
    .pip_install("reflex==0.9.12", "supabase", "PyJWT")
    .add_local_dir(
        ".",
        remote_path="/app",
        copy=True,
        ignore=[
            ".venv",
            ".web",
            ".git",
            ".states",
            "qa",
            "__pycache__",
            "modal_deploy.py",
        ],
    )
    # Compile the Reflex app, then build the production frontend bundle once
    # here (image build has generous CPU/RAM) instead of on every cold start.
    .run_commands(
        "cd /app && reflex compile",
        "cd /app && python -c "
        "\"from pathlib import Path; from reflex.utils import build; "
        "build.setup_frontend_prod(Path('/app'))\"",
    )
)

app = modal.App(APP_NAME, image=image)


def _secret_dict() -> dict:
    d = {"JWT_SECRET": os.environ.get("JWT_SECRET") or "dev-only-change-me"}
    for key in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_KEY"):
        val = os.environ.get(key, "").strip()
        if val:
            d[key] = val
    return d


@app.function(
    memory=1024,
    scaledown_window=300,  # keep warm 5 min after last request
    secrets=[modal.Secret.from_dict(_secret_dict())],
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app(label="safe-child")
def serve():
    """Return the Reflex production ASGI app (frontend + backend, one server)."""
    import os
    import sys

    os.chdir("/app")
    sys.path.insert(0, "/app")

    # Mirror what `reflex run --env prod` sets up, minus the server itself.
    # NOTE: `environment` must be the EnvironmentVariables *instance* from
    # reflex_base, not the `reflex.environment` module (Reflex 0.9.x).
    from reflex import constants
    from reflex_base.environment import environment

    environment.REFLEX_ENV_MODE.set(constants.Env.PROD)
    environment.REFLEX_MOUNT_FRONTEND_COMPILED_APP.set(True)

    from safe_child.safe_child import app as rx_app

    return rx_app()
