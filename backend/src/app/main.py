# App entry point — creates FastAPI app, sets up logging, registers routes.

import logging

from fastapi import FastAPI

from .api.routes.event import event_router
from .core.logging_config import setup_logging

# --- Logging setup (runs once when app starts) ---
setup_logging()
logger = logging.getLogger("app.main")

# --- FastAPI app ---
app = FastAPI(title="AI Observability Platform")

app.include_router(event_router, prefix="/v1")
logger.info("Registered route: /v1/events")


@app.get("/")
def health_check():
    """Returns server health status. Called by monitoring tools or browsers."""
    logger.debug("Health check requested")
    return {"status": "ok"}