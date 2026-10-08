from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class EventType(Enum):
    AGENT = "agent"
    TOOL = "tool"
    LLM  = "llm"

class EventStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"

class Event(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    type: EventType
    name: str
    status: EventStatus

    timestamp: datetime
    duration_ms: float | None = None
    metadata: dict = {}

