# SDK Tracer — creates traces and spans to track agent/tool/LLM execution.

import logging
import uuid
from datetime import datetime

from .models import Event, EventStatus, EventType
from .context import current_span, current_trace, current_events

logger = logging.getLogger("sdk.tracer")


class Tracer:
    """
    Creates a trace (unique ID) and records spans (start/complete/fail).
    Each span represents one unit of work: an agent step, tool call, or LLM call.
    """

    def __init__(self):
        self.trace_id = current_trace.get()

        if self.trace_id == "":
            self.trace_id = str(uuid.uuid4())
            current_trace.set(self.trace_id)

        self.events = []
        logger.debug(f"Tracer created | trace_id={self.trace_id}")

    def start(self, name: str, event_type: EventType, parent_span_id=None):
        if parent_span_id is None:
            parent_span_id = current_span.get()

        """
        Starts a new span. Returns the span_id.
        Called by: agents, tools, LLM wrappers when they begin work.
        """
        span_id = str(uuid.uuid4())

        try:
            event = Event(
                trace_id=self.trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                type=event_type,
                name=name,
                status=EventStatus.STARTED,
                timestamp=datetime.now(),
            )
            self.events.append(event)
            logger.debug(f"Span started | trace={self.trace_id[:8]} | span={span_id[:8]} | name={name} | type={event_type.value}")
        except Exception as e:
            logger.exception(f"Failed to create span '{name}': {e}")
            raise

        current_span.set(span_id)
        return span_id

    def complete(self, span_id: str, duration_ms: float):
        """
        Marks a span as completed with its duration.
        Called by: agents/tools/LLM wrappers when work finishes successfully.
        """
        for event in self.events:
            if event.span_id == span_id:
                event.status = EventStatus.COMPLETED
                event.duration_ms = duration_ms
                logger.debug(f"Span completed | span={span_id[:8]} | name={event.name} | duration={duration_ms:.1f}ms")
                return

        logger.warning(f"Span not found for completion | span_id={span_id}")

    def fail(self, span_id: str, duration_ms: float, error: str):
        """
        Marks a span as failed with error details.
        Called by: agents/tools/LLM wrappers when work fails.
        """
        for event in self.events:
            if event.span_id == span_id:
                event.status = EventStatus.FAILED
                event.duration_ms = duration_ms
                event.metadata = {"error": error}
                logger.error(f"Span failed | span={span_id[:8]} | name={event.name} | error={error}")
                return

        logger.warning(f"Span not found for failure | span_id={span_id}")

    def get_events(self):
        """Returns all recorded events. Used by send_events() to POST to backend."""
        return self.events