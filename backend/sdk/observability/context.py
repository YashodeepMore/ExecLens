from contextvars import ContextVar

current_trace = ContextVar("current_trace", default="")
current_span = ContextVar("current_span", default="")
current_events = ContextVar("current_events", default=None)