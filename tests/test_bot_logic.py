import asyncio
from datetime import datetime, timedelta

import pytest

from backend.bot_logic import WaterBotLogic
from backend.db import DB


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 8, 26, 12)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


def alert_config(**overrides):
    logic_config = {
        "critical_level": 2,
        "warning_level": 5,
        "cd_normal": 0,
        "cd_warning": 0,
        "cd_critical": 0,
        "stability_period": "1m",
        "stability_tolerance": 0.2,
        "stability_min_samples": 3,
    }
    logic_config.update(overrides)
    return {"logic": logic_config}


@pytest.mark.parametrize(
    ("level", "expected_fragment"),
    [
        (1.0, "Критический уровень"),
        (4.0, "ниже нормы"),
        (8.0, "Вода:"),
    ],
)
def test_level_selects_expected_alert(tmp_path, level, expected_fragment):
    messages = []

    async def sender(message):
        messages.append(message)

    clock = FakeClock()
    db = DB(filename=tmp_path / "db.json", save_every=100)
    logic = WaterBotLogic(db, alert_config(), sender, clock=clock)

    asyncio.run(logic.on_sensor_data(level))
    clock.advance(30)
    asyncio.run(logic.on_sensor_data(level))
    clock.advance(30)
    asyncio.run(logic.on_sensor_data(level))

    assert len(messages) == 1
    assert expected_fragment in messages[0]
    assert logic.last_water_level == level
    assert logic.sensor_data[-1]["water_level"] == level


def test_sudden_change_delays_alert_until_new_level_is_stable(tmp_path):
    messages = []

    async def sender(message):
        messages.append(message)

    clock = FakeClock()
    db = DB(filename=tmp_path / "db.json", save_every=100)
    logic = WaterBotLogic(db, alert_config(), sender, clock=clock)

    asyncio.run(logic.on_sensor_data(8.0))
    clock.advance(30)
    asyncio.run(logic.on_sensor_data(1.0))
    clock.advance(30)
    asyncio.run(logic.on_sensor_data(1.05))

    assert messages == []

    clock.advance(30)
    asyncio.run(logic.on_sensor_data(0.98))

    assert len(messages) == 1
    assert "Критический уровень" in messages[0]
    assert "1.0 л" in messages[0]


def test_unstable_window_does_not_send_alert(tmp_path):
    messages = []

    async def sender(message):
        messages.append(message)

    clock = FakeClock()
    db = DB(filename=tmp_path / "db.json", save_every=100)
    logic = WaterBotLogic(db, alert_config(), sender, clock=clock)

    for level in [4.0, 4.3, 4.0]:
        asyncio.run(logic.on_sensor_data(level))
        clock.advance(30)

    assert messages == []


def test_polling_jitter_still_completes_stability_period(tmp_path):
    messages = []

    async def sender(message):
        messages.append(message)

    clock = FakeClock()
    db = DB(filename=tmp_path / "db.json", save_every=100)
    logic = WaterBotLogic(db, alert_config(), sender, clock=clock)

    for elapsed in [0, 17, 33, 49, 64]:
        clock.now = datetime(2026, 8, 26, 12) + timedelta(seconds=elapsed)
        asyncio.run(logic.on_sensor_data(4.0))

    assert len(messages) == 1
    assert "ниже нормы" in messages[0]


def test_tare_request_is_persisted_until_acknowledged(tmp_path):
    async def sender(_message):
        pass

    db_path = tmp_path / "db.json"
    db = DB(filename=db_path)
    logic = WaterBotLogic(db, {}, sender)

    logic.request_tare()

    reloaded_db = DB(filename=db_path)
    reloaded_db.load()
    reloaded_logic = WaterBotLogic(reloaded_db, {}, sender)
    assert reloaded_logic.tare_requested is True

    reloaded_logic.acknowledge_tare()

    final_db = DB(filename=db_path)
    final_db.load()
    assert final_db.get("tare_requested") is False
