import asyncio

import pytest

from backend.bot_logic import WaterBotLogic
from backend.db import DB


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

    config = {
        "logic": {
            "critical_level": 2,
            "warning_level": 5,
            "cd_normal": 0,
            "cd_warning": 0,
            "cd_critical": 0,
        }
    }
    db = DB(filename=tmp_path / "db.json", save_every=100)
    logic = WaterBotLogic(db, config, sender)

    asyncio.run(logic.on_sensor_data(level))

    assert len(messages) == 1
    assert expected_fragment in messages[0]
    assert logic.last_water_level == level
    assert logic.sensor_data[-1]["water_level"] == level


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
