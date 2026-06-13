"""Fixed-sensing hardware trigger (design.md Section 6 item 5, Section 9 v4).

There is no hardware to build in software here. v4 is a *decision rule*: the design
defers the fixed camera indefinitely, with a defined trigger to revisit — if, after
8+ weeks, the weekly phone-scan step is the component being skipped, that's evidence
the passive capture is worth the hardware investment (or that the next fridge should
be a camera-native model, at which point the sensing layer is bought, not built).

This evaluates that trigger from the scan event history.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .events import EventLog, KIND_SCAN


@dataclass
class HardwareTrigger:
    triggered: bool
    weeks_observed: int
    scans_in_window: int
    expected_scans: int
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "triggered": self.triggered,
            "weeks_observed": self.weeks_observed,
            "scans_in_window": self.scans_in_window,
            "expected_scans": self.expected_scans,
            "recommendation": self.recommendation,
        }


def evaluate(
    log: EventLog,
    today: date | None = None,
    window_weeks: int = 8,
    skip_ratio: float = 0.5,
) -> HardwareTrigger:
    """Trigger when the weekly scan is skipped often enough over the window.

    ``skip_ratio`` is the fraction of expected weekly scans that may be missed
    before the fixed-camera revisit is recommended (default: more than half missed).
    """
    today = today or date.today()
    start = today - timedelta(weeks=window_weeks)

    scan_dates = {e.event_date() for e in log.by_kind(KIND_SCAN)
                  if e.event_date() and e.event_date() >= start}
    # Count distinct ISO weeks with at least one scan.
    weeks_with_scan = {d.isocalendar()[:2] for d in scan_dates}
    scans_in_window = len(weeks_with_scan)
    expected = window_weeks

    missed = expected - scans_in_window
    triggered = missed > expected * skip_ratio

    if triggered:
        rec = (f"Phone scan skipped {missed}/{expected} weeks. Passive capture is "
               f"worth revisiting: evaluate a fixed FridgeCam or make the next "
               f"refrigerator a camera-native model (GE Profile / Samsung AI Vision / "
               f"Miele FoodView).")
    else:
        rec = (f"Phone scan habit is holding ({scans_in_window}/{expected} weeks). "
               f"Keep fixed sensing deferred — no hardware spend justified.")

    return HardwareTrigger(
        triggered=triggered,
        weeks_observed=window_weeks,
        scans_in_window=scans_in_window,
        expected_scans=expected,
        recommendation=rec,
    )
