from datetime import datetime, timedelta, timezone

from backend import db as db_module
from backend.db import DB
from backend.db import Cooldown


def test_database_round_trip(tmp_path):
    path = tmp_path / "db.json"
    database = DB(filename=path)
    database["answer"] = 42
    database.save()

    restored = DB(filename=path)
    restored.load()

    assert restored["answer"] == 42


def test_cooldown_blocks_retrigger_until_period_elapsed(monkeypatch):
    current_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return current_time

    monkeypatch.setattr(db_module, "datetime", FrozenDateTime)
    database = DB(save_every=100)
    cooldown = Cooldown(database, "water-alert", period_sec=60)

    assert cooldown.key == "water-alert:cooldown"
    assert cooldown.read_last_trigger_ts() == 0
    assert cooldown.can_do()

    cooldown.do()
    triggered_at = current_time.timestamp()
    assert database[cooldown.key] == triggered_at
    assert not cooldown.can_do()

    current_time += timedelta(seconds=30)
    cooldown.do()
    assert database[cooldown.key] == triggered_at

    current_time += timedelta(seconds=31)
    assert cooldown.can_do()
