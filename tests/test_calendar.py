from pantry_local.integrations.calendar import (
    CalEvent, derive_time_limits, time_limits_from_client,
    SHORT_COOK_LIMIT, LEFTOVER_LIMIT,
)


def test_late_day_becomes_short_cook():
    limits = derive_time_limits([CalEvent("Tue", 18.5)])
    assert limits["Tue"] == SHORT_COOK_LIMIT


def test_very_late_day_becomes_leftover():
    limits = derive_time_limits([CalEvent("Wed", 20.5)])
    assert limits["Wed"] == LEFTOVER_LIMIT


def test_early_day_no_limit():
    limits = derive_time_limits([CalEvent("Mon", 16.0)])
    assert "Mon" not in limits


def test_latest_event_per_day_wins():
    limits = derive_time_limits([CalEvent("Thu", 15.0), CalEvent("Thu", 21.0)])
    assert limits["Thu"] == LEFTOVER_LIMIT


def test_client_hook():
    def fake(days):
        return [{"day": "Fri", "end_hour": 19.0}]
    limits = time_limits_from_client(["Fri"], fake)
    assert limits["Fri"] == SHORT_COOK_LIMIT
