from .event import Event
from pydantic import BaseModel

class Trace(BaseModel):
    trace_id:str
    events: list[Event] = []
    

