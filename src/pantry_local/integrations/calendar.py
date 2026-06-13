"""Calendar-aware planning (design.md Section 7).

Time variance is the dominant constraint, so calendar integration is a launch
feature, not a nicety: late-meeting days auto-flag as short-cook (<=25 min) or
leftover nights, which the planner turns into time ceilings.

The Google Calendar fetch is an injectable seam (``calendar_client``); this module
only turns events into per-day cook-time limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

SHORT_COOK_LIMIT = 25      # minutes on a late night
LEFTOVER_LIMIT = 1         # effectively "no cooking" -> planner flags leftover/order-in
DEFAULT_LATE_HOUR = 18.0   # a meeting ending at/after 6pm makes it a short night
VERY_LATE_HOUR = 20.0      # at/after 8pm -> leftover night


@dataclass
class CalEvent:
    day: str          # "Mon", "Tue", ...
    end_hour: float   # 24h decimal, e.g. 18.5 for 6:30pm


def derive_time_limits(
    events: list[CalEvent],
    late_hour: float = DEFAULT_LATE_HOUR,
    very_late_hour: float = VERY_LATE_HOUR,
) -> dict[str, int]:
    """Return {day: minutes} ceilings from the day's latest-ending event."""
    latest: dict[str, float] = {}
    for ev in events:
        latest[ev.day] = max(latest.get(ev.day, 0.0), ev.end_hour)
    limits: dict[str, int] = {}
    for day, end in latest.items():
        if end >= very_late_hour:
            limits[day] = LEFTOVER_LIMIT
        elif end >= late_hour:
            limits[day] = SHORT_COOK_LIMIT
    return limits


def time_limits_from_client(
    days: list[str],
    calendar_client: Callable[[list[str]], list[dict]],
) -> dict[str, int]:
    """Fetch events via an injected client and derive limits.

    ``calendar_client(days)`` returns ``[{"day","end_hour"}, ...]``.
    """
    raw = calendar_client(days)
    events = [CalEvent(day=e["day"], end_hour=float(e["end_hour"])) for e in raw]
    return derive_time_limits(events)
