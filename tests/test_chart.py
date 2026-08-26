from datetime import datetime, timedelta

import pytest

from backend.chart import plot_water_level_chart


def test_chart_is_rendered_as_png():
    start = datetime(2026, 8, 26, 8)
    sensor_data = [
        {
            "water_level": level,
            "timestamp": (start + timedelta(hours=index)).timestamp(),
        }
        for index, level in enumerate([8.2, 7.9, 7.4, 6.8])
    ]

    chart = plot_water_level_chart(sensor_data)

    assert chart.read(8) == b"\x89PNG\r\n\x1a\n"
    assert chart.getbuffer().nbytes > 10_000
    chart.close()


def test_chart_requires_sensor_data():
    with pytest.raises(ValueError, match="Нет данных"):
        plot_water_level_chart([])
