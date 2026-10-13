# SDK Decorators — wraps functions with automatic tracing and event sending.

from pydantic import functional_validators
from pydantic import functional_validators
from pydantic import functional_validators
from pydantic import functional_validators
from pydantic import functional_validators
from pydantic import functional_validators
from pydantic import functional_validators
from pydantic import functional_validators
from pydantic import functional_validators
from sdk.observability import tracer
import logging
import time
from functools import wraps

from .models import EventType
from .tracer import Tracer
from .server import send_events
from .context import current_span

logger = logging.getLogger("sdk.decorators")


def observe(func):
    """
    Decorator that auto-traces a function.
    Wraps the function call with a Tracer span and sends events to the backend.
    Use: @observe on any agent function you want to monitor.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracer = Tracer()
        previous_span = current_span.get()

        span_id = tracer.start(
            name=func.__name__,
            event_type=EventType.AGENT,
            parent_span_id=previous_span,
        )

        logger.info(f"@observe started | function={func.__name__}")
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)

            duration = (time.perf_counter() - start_time) * 1000
            tracer.complete(span_id, duration)
            logger.info(f"@observe completed | function={func.__name__} | duration={duration:.1f}ms")

            try:
                send_events(tracer.get_events())
                current_span.set(previous_span)
            except Exception as e:
                logger.error(f"@observe failed to send events | function={func.__name__} | error={e}")
            current_span.set(previous_span)
            return result

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            tracer.fail(span_id, duration, str(e))
            logger.error(f"@observe caught exception | function={func.__name__} | duration={duration:.1f}ms | error={e}")

            try:
                send_events(tracer.get_events())
                current_span.set(previous_span)
            except Exception as send_err:
                logger.error(f"@observe failed to send failure events | function={func.__name__} | error={send_err}")
            current_span.set(previous_span)
            raise

    return wrapper