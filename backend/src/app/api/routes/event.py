# Event API routes — receives trace events from SDK and stores them in memory.

import logging

from fastapi import APIRouter

logger = logging.getLogger("app.api.events")

event_router = APIRouter(prefix="/events", tags=["Events"])

# Temporary in-memory store (will be replaced by database later)
global_temp_TRACERS = {}
i = 1


@event_router.post("")
def receive_event(event: dict):
    """
    Receives a single trace event from the SDK.
    Data comes from: SDK send_events() → HTTP POST.
    Stores event in memory and returns confirmation.
    """
    global i
    try:
        global_temp_TRACERS[f"T{i}"] = event
        logger.info(f"Event received: T{i} | type={event.get('type')} | name={event.get('name')} | status={event.get('status')}")
        logger.debug(f"Event T{i} full payload: {event}")
        i = i + 1
        return {
            "status": "received",
            "event": event
        }
    except Exception as e:
        logger.exception(f"Failed to store event: {e}")
        return {"status": "error", "message": str(e)}


@event_router.get("/display")
def display_events():
    """
    Returns all stored events.
    Data goes to: browser or any GET request for debugging.
    """
    logger.debug(f"Display requested — returning {len(global_temp_TRACERS)} events")
    return global_temp_TRACERS