"""
Naming conventions
classes - CamelCase
functions - lower_case_with_underscores
variables - lower_case_with_underscores
constants - UPPER_CASE_WITH_UNDERSCORES
"""
from enum import Enum


class MopsEvent:
    """Simple event class with time when event should occur and event type."""
    def __init__(self, time, event_type, packet, router_idx):
        self.time = time
        self.type = event_type
        self.packet = packet
        self.router_idx = router_idx

    def __lt__(self, other):  # if you want to know something about this write to me directly
        if self.time == other.time:
            if self.type == MopsEventType.START_SERVICE:
                return False
            elif self.type == MopsEventType.ARRIVAL:
                return True
        else:
            return self.time < other.time


class MopsEventType(Enum):
    ARRIVAL = 1
    START_SERVICE = 2
    END_SERVICE = 3
