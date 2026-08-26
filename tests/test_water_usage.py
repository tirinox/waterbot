from datetime import datetime, timedelta

import pytest

from backend.water_usage import estimate_water_usage, format_water_usage_summary


def make_history(levels, interval=timedelta(hours=1)):
    start = datetime(2026, 8, 20, 8)
    return [
        {
            "timestamp": (start + interval * index).timestamp(),
            "water_level": level,
        }
        for index, level in enumerate(levels)
    ]


def test_estimates_daily_use_and_empty_time_from_falling_trend():
    history = make_history([20 - index / 12 for index in range(25)])

    estimate = estimate_water_usage(history, now=datetime(2026, 8, 21, 8))

    assert estimate is not None
    assert estimate.average_liters_per_day == pytest.approx(2.0)
    assert estimate.r_squared == pytest.approx(1.0)
    assert estimate.predicted_empty_at == datetime(2026, 8, 30, 8)
    assert "2.0 л/день" in format_water_usage_summary(estimate)
    assert "30.08 в 08:00" in format_water_usage_summary(estimate)


@pytest.mark.parametrize(
    "levels",
    [
        [10, 10, 10, 10, 10, 10, 10],
        [10, 10.01, 10.02, 10.03, 10.04, 10.05, 10.06],
        [10, 9, 10, 9, 10, 9, 10],
    ],
)
def test_rejects_flat_rising_or_unreliable_trends(levels):
    assert estimate_water_usage(make_history(levels)) is None


def test_ignores_measurements_before_refill():
    history = make_history([10, 9.8, 9.6, 18, 17.8, 17.6, 17.4, 17.2, 17.0, 16.8])

    estimate = estimate_water_usage(history)

    assert estimate is not None
    assert estimate.observed_from == datetime(2026, 8, 20, 11)
    assert estimate.average_liters_per_day == pytest.approx(4.8)


def test_withholds_prediction_when_empty_time_is_implausibly_far_away():
    history = make_history([20 - index / 120 for index in range(25)])

    estimate = estimate_water_usage(history, now=datetime(2026, 8, 21, 8))

    assert estimate is not None
    assert estimate.average_liters_per_day == pytest.approx(0.2)
    assert estimate.predicted_empty_at is None
    assert "Прогноз" not in format_water_usage_summary(estimate)


def test_withholds_prediction_calculated_from_stale_measurements():
    history = make_history([20 - index / 12 for index in range(25)])

    estimate = estimate_water_usage(history, now=datetime(2026, 8, 21, 11))

    assert estimate is not None
    assert estimate.predicted_empty_at is None
    assert "Прогноз" not in format_water_usage_summary(estimate)


def test_rejects_implausibly_fast_consumption():
    history = make_history([50 - index * 3 for index in range(7)])

    assert estimate_water_usage(history) is None
