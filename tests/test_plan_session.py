"""Tests for planning session instrumentation."""

from datetime import date, timedelta

from pantry_local.events import EventLog, KIND_PLAN_SESSION, plan_session_status


def test_plan_session_status_no_sessions():
    log = EventLog()
    status = plan_session_status(log, today=date(2026, 6, 12))
    assert status["weeks_since_last"] is None
    assert status["kill_criterion_triggered"] is False


def test_plan_session_kill_criterion():
    log = EventLog()
    old = (date(2026, 6, 12) - timedelta(weeks=7)).isoformat()
    log.append(KIND_PLAN_SESSION, {"completed": True}, ts=f"{old}T10:00:00")
    status = plan_session_status(log, today=date(2026, 6, 12))
    assert status["kill_criterion_triggered"] is True


def test_plan_session_incomplete_sessions():
    log = EventLog()
    log.append(KIND_PLAN_SESSION, {"completed": False}, ts="2026-06-01T10:00:00")
    status = plan_session_status(log, today=date(2026, 6, 12))
    assert status["weeks_since_last"] == 999
    assert status["kill_criterion_triggered"] is True
