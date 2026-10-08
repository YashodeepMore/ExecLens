# SDK Server — sends collected trace events to the backend API via HTTP.

import logging

import httpx

logger = logging.getLogger("sdk.server")

BACKEND_URL = "http://localhost:8000/v1/events"


def send_events(events):
    """
    Sends each event to the backend API one by one via HTTP POST.
    Data comes from: Tracer.get_events() (list of Event objects).
    Data goes to: FastAPI POST /v1/events endpoint.
    """
    for event in events:
        try:
            response = httpx.post(
                BACKEND_URL,
                json=event.model_dump(mode="json"),
            )
            response.raise_for_status()
            logger.debug(f"Event sent | name={event.name} | status={event.status.value} | → {BACKEND_URL}")
        except httpx.ConnectError:
            logger.error(f"Cannot connect to backend at {BACKEND_URL} — is the server running?")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Backend rejected event | name={event.name} | HTTP {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error sending event '{event.name}': {e}")
            raise

    logger.info(f"All events sent | count={len(events)} | → {BACKEND_URL}")