from datetime import date

from pantry_local.events import EventLog, load_events, save_events


def test_append_and_query():
    log = EventLog()
    log.append("cook", {"recipe": "rajma"}, ts="2026-06-10T19:00:00")
    log.append("scan", {}, ts="2026-06-11T10:00:00")
    assert len(log.by_kind("cook")) == 1
    assert len(log.since(date(2026, 6, 11))) == 1


def test_roundtrip(tmp_path):
    log = EventLog()
    log.append("receipt", {"applied": []}, ts="2026-06-10T08:00:00")
    path = tmp_path / "events.json"
    save_events(log, path)
    loaded = load_events(path)
    assert len(loaded.by_kind("receipt")) == 1


def test_load_missing_file_is_empty(tmp_path):
    assert load_events(tmp_path / "nope.json").all() == []
