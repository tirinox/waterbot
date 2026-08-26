import asyncio
from datetime import datetime, timedelta
from io import BytesIO

from aiogram.types import BufferedInputFile

from backend import telegram_notification


def test_send_chart_notification_sends_png_with_alert_caption(monkeypatch):
    chart = BytesIO(b"png data")
    sent = {}

    class FakeBot:
        async def send_photo(self, channel, *, photo, caption):
            sent.update(channel=channel, photo=photo, caption=caption)

    monkeypatch.setattr(
        telegram_notification,
        "plot_water_level_chart",
        lambda sensor_data: chart,
    )

    asyncio.run(
        telegram_notification.send_chart_notification(
            FakeBot(),
            -100123,
            [{"water_level": 4.0, "timestamp": 1}],
            "Water alert",
        )
    )

    assert sent["channel"] == -100123
    assert sent["caption"] == "Water alert"
    assert isinstance(sent["photo"], BufferedInputFile)
    assert sent["photo"].filename == "chart.png"
    assert chart.closed


def test_send_chart_notification_adds_sane_usage_forecast(monkeypatch):
    chart = BytesIO(b"png data")
    sent = {}
    end = datetime.now()
    sensor_data = [
        {
            "timestamp": (end - timedelta(minutes=30 * (24 - index))).timestamp(),
            "water_level": 18 - index / 12,
        }
        for index in range(25)
    ]

    class FakeBot:
        async def send_photo(self, channel, *, photo, caption):
            sent.update(channel=channel, photo=photo, caption=caption)

    monkeypatch.setattr(
        telegram_notification,
        "plot_water_level_chart",
        lambda sensor_data: chart,
    )

    asyncio.run(
        telegram_notification.send_chart_notification(
            FakeBot(),
            -100123,
            sensor_data,
            "Water alert",
        )
    )

    assert "Средний расход: 4.0 л/день" in sent["caption"]
    assert "Прогноз: вода закончится" in sent["caption"]
    assert chart.closed
