from datetime import date, timedelta

from pantry_local.events import EventLog
from pantry_local import hardware

TODAY = date(2026, 6, 13)


def test_trigger_fires_when_scans_skipped():
    log = EventLog()  # no scans at all over the window
    res = hardware.evaluate(log, today=TODAY, window_weeks=8)
    assert res.triggered
    assert res.scans_in_window == 0
    assert "revisit" in res.recommendation.lower() or "camera" in res.recommendation.lower()


def test_no_trigger_when_habit_holds():
    log = EventLog()
    # one scan per week for 8 weeks
    for w in range(8):
        d = TODAY - timedelta(weeks=w)
        log.append("scan", {}, ts=f"{d.isoformat()}T10:00:00")
    res = hardware.evaluate(log, today=TODAY, window_weeks=8)
    assert not res.triggered
    assert res.scans_in_window >= 7


def test_borderline_half_skipped_triggers():
    log = EventLog()
    for w in range(3):  # 3 of 8 weeks -> 5 missed > 4 -> triggered
        d = TODAY - timedelta(weeks=w)
        log.append("scan", {}, ts=f"{d.isoformat()}T10:00:00")
    res = hardware.evaluate(log, today=TODAY, window_weeks=8)
    assert res.triggered
