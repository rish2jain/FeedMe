"""Append-only event log.

A lightweight history of what happened — cooks, receipts, scans, plans — used by
depletion prediction (v3) and the fixed-sensing trigger (v4). Kept deliberately
simple (JSONL-ish list in one file); the point is a durable signal of usage
cadence, not an analytics warehouse.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

KIND_COOK = "cook"
KIND_RECEIPT = "receipt"
KIND_SCAN = "scan"
KIND_PLAN = "plan"
KIND_PLAN_SESSION = "plan_session"

# Design §9 kill criterion: if planning skipped by week 6, fix friction first.
PLAN_SESSION_KILL_WEEKS = 6


@dataclass
class Event:
    ts: str  # ISO datetime
    kind: str
    data: dict

    def event_date(self) -> date | None:
        try:
            return datetime.fromisoformat(self.ts).date()
        except ValueError:
            return None


class EventLog:
    def __init__(self, events: list[Event] | None = None) -> None:
        self._events: list[Event] = list(events or [])

    def append(self, kind: str, data: dict | None = None, ts: str | None = None) -> Event:
        ev = Event(ts=ts or datetime.now().isoformat(timespec="seconds"),
                   kind=kind, data=data or {})
        self._events.append(ev)
        return ev

    def all(self) -> list[Event]:
        return list(self._events)

    def by_kind(self, kind: str) -> list[Event]:
        return [e for e in self._events if e.kind == kind]

    def since(self, start: date) -> list[Event]:
        out = []
        for e in self._events:
            d = e.event_date()
            if d and d >= start:
                out.append(e)
        return out

    def to_dict(self) -> dict:
        return {"events": [asdict(e) for e in self._events]}

    @classmethod
    def from_dict(cls, d: dict) -> "EventLog":
        return cls([Event(**e) for e in d.get("events", [])])


def load_events(path: str | Path) -> EventLog:
    p = Path(path)
    if not p.exists():
        return EventLog()
    return EventLog.from_dict(json.loads(p.read_text()))


def save_events(log: EventLog, path: str | Path) -> None:
    Path(path).write_text(json.dumps(log.to_dict(), indent=2))


def plan_session_status(log: EventLog, today: date | None = None) -> dict:
    """Report planning-session cadence for the §9 kill criterion."""
    today = today or date.today()
    sessions = log.by_kind(KIND_PLAN_SESSION)
    completed = [e for e in sessions if e.data.get("completed")]
    last_date: date | None = None
    for ev in reversed(completed):
        d = ev.event_date()
        if d:
            last_date = d
            break
    weeks_since = None
    if last_date:
        weeks_since = (today - last_date).days // 7
    elif sessions:
        weeks_since = 999
    else:
        weeks_since = None
    kill_triggered = weeks_since is not None and weeks_since >= PLAN_SESSION_KILL_WEEKS
    return {
        "last_session": last_date.isoformat() if last_date else None,
        "weeks_since_last": weeks_since,
        "total_sessions_logged": len(completed),
        "kill_criterion_triggered": kill_triggered,
        "message": (
            f"Planning session skipped {PLAN_SESSION_KILL_WEEKS}+ weeks — "
            "fix the 10-min loop before adding features."
            if kill_triggered
            else "Planning cadence OK."
        ),
    }
