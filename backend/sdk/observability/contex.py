# context.py

from contextvars import ContextVar

current_trace = ContextVar(
    "current_trace",
    default=None
)

current_span = ContextVar(
    "current_span",
    default=None
)