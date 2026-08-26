"""Estimate water consumption and a guarded empty-container forecast.

The estimator reduces sensor noise to 30-minute median points, discards data
before the latest detected refill, and fits the ordinary least-squares line
``level = intercept + slope * elapsed_days``.  A negative slope represents
consumption, so the reported daily use is ``-slope``.  The line's fitted level
at the newest point is divided by daily use to estimate time remaining.

Neither the trend nor its forecast is trusted blindly.  The code requires a
minimum observation span, plausible consumption, and sufficient R-squared fit
quality.  A forecast is published only for fresh measurements and a bounded
time-to-empty.  See ``docs/water_usage_forecasting.md`` for the rationale and
formulas behind each step.
"""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median


BUCKET_SECONDS = 30 * 60
MIN_OBSERVATION_SECONDS = 6 * 60 * 60
MAX_OBSERVATION_SECONDS = 7 * 24 * 60 * 60
MIN_BUCKETS = 4
REFILL_INCREASE_LITERS = 1.0
MIN_R_SQUARED = 0.35
MIN_DAILY_USE_LITERS = 0.1
MAX_DAILY_USE_LITERS = 50.0
MAX_MEASUREMENT_AGE_HOURS = 2
MIN_PREDICTION_HOURS = 2
MAX_PREDICTION_DAYS = 90


@dataclass(frozen=True)
class WaterUsageEstimate:
    """A validated falling trend with an optional sane empty-time forecast."""

    average_liters_per_day: float
    observed_from: datetime
    observed_until: datetime
    trend_start_level: float
    trend_end_level: float
    r_squared: float
    predicted_empty_at: datetime | None


def estimate_water_usage(sensor_data, now: datetime | None = None) -> WaterUsageEstimate | None:
    """Fit and validate a linear consumption trend from sensor history.

    Timestamps are expressed as elapsed days so the fitted slope is naturally
    measured in liters per day.  Thirty-minute median buckets stop the sensor's
    high sampling rate and occasional spikes from dominating the fit.  Data
    before the latest increase of at least one liter is treated as belonging to
    the previous container and excluded.

    ``None`` means that the history is too short, non-decreasing, implausibly
    fast or slow, or too poorly described by a straight line.  A returned
    estimate always has a usable average rate, but ``predicted_empty_at`` can
    still be ``None`` when the latest sample or projected horizon fails the
    stricter forecast sanity checks.

    Args:
        sensor_data: Entries containing numeric ``timestamp`` and
            ``water_level`` fields.
        now: Local wall-clock time used for forecast freshness checks.  Tests
            may supply it for determinism; production defaults to now.
    """

    points = _valid_points(sensor_data)
    if len(points) < MIN_BUCKETS:
        return None

    newest_timestamp = points[-1][0]
    points = [
        point for point in points if point[0] >= newest_timestamp - MAX_OBSERVATION_SECONDS
    ]
    buckets = _bucket_medians(points)
    buckets = _points_after_last_refill(buckets)

    if len(buckets) < MIN_BUCKETS:
        return None
    if buckets[-1][0] - buckets[0][0] < MIN_OBSERVATION_SECONDS:
        return None

    origin = buckets[0][0]
    times_in_days = [(timestamp - origin) / 86_400 for timestamp, _level in buckets]
    levels = [level for _timestamp, level in buckets]
    slope, intercept, r_squared = _linear_regression(times_in_days, levels)
    average_liters_per_day = -slope

    if not MIN_DAILY_USE_LITERS <= average_liters_per_day <= MAX_DAILY_USE_LITERS:
        return None
    if r_squared < MIN_R_SQUARED:
        return None

    fitted_start = intercept
    fitted_end = intercept + slope * times_in_days[-1]
    prediction = _sane_empty_prediction(
        timestamp=buckets[-1][0],
        current_level=max(0, fitted_end),
        average_liters_per_day=average_liters_per_day,
        now=now or datetime.now(),
    )

    return WaterUsageEstimate(
        average_liters_per_day=average_liters_per_day,
        observed_from=datetime.fromtimestamp(buckets[0][0]),
        observed_until=datetime.fromtimestamp(buckets[-1][0]),
        trend_start_level=fitted_start,
        trend_end_level=fitted_end,
        r_squared=r_squared,
        predicted_empty_at=prediction,
    )


def format_water_usage_summary(estimate: WaterUsageEstimate | None) -> str | None:
    """Format validated usage, omitting the forecast when it was withheld."""

    if estimate is None:
        return None

    lines = [f"📊 Средний расход: {estimate.average_liters_per_day:.1f} л/день."]
    if estimate.predicted_empty_at is not None:
        lines.append(
            "🗓 Прогноз: вода закончится "
            f"{estimate.predicted_empty_at:%d.%m в %H:%M}."
        )
    return "\n".join(lines)


def _valid_points(sensor_data) -> list[tuple[float, float]]:
    points = []
    for entry in sensor_data:
        timestamp = entry.get("timestamp")
        level = entry.get("water_level")
        if isinstance(timestamp, bool) or isinstance(level, bool):
            continue
        if not isinstance(timestamp, (int, float)) or not isinstance(level, (int, float)):
            continue
        if not math.isfinite(timestamp) or not math.isfinite(level) or level < 0:
            continue
        points.append((float(timestamp), float(level)))
    return sorted(points)


def _bucket_medians(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Collapse dense measurements into noise-resistant 30-minute medians."""

    grouped = defaultdict(list)
    for timestamp, level in points:
        grouped[int(timestamp // BUCKET_SECONDS)].append((timestamp, level))

    buckets = []
    for bucket in sorted(grouped):
        values = grouped[bucket]
        buckets.append((max(timestamp for timestamp, _level in values), median(v[1] for v in values)))
    return buckets


def _points_after_last_refill(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return only points at and after the latest likely container refill."""

    last_refill_index = 0
    for index in range(1, len(points)):
        if points[index][1] - points[index - 1][1] >= REFILL_INCREASE_LITERS:
            last_refill_index = index
    return points[last_refill_index:]


def _linear_regression(x_values: list[float], y_values: list[float]) -> tuple[float, float, float]:
    """Fit ``y = intercept + slope*x`` by OLS and return slope, intercept, R-squared.

    Ordinary least squares chooses the line that minimizes the sum of squared
    vertical residuals.  R-squared measures the fraction of level variation
    explained by that line and is used to reject unstable forecasts.
    """

    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    x_variance = sum((value - x_mean) ** 2 for value in x_values)
    if x_variance == 0:
        return 0, y_mean, 0

    slope = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values, strict=True)
    ) / x_variance
    intercept = y_mean - slope * x_mean

    fitted = [intercept + slope * value for value in x_values]
    total_variance = sum((value - y_mean) ** 2 for value in y_values)
    residual_variance = sum(
        (actual - predicted) ** 2
        for actual, predicted in zip(y_values, fitted, strict=True)
    )
    r_squared = 0 if total_variance == 0 else max(0, 1 - residual_variance / total_variance)
    return slope, intercept, r_squared


def _sane_empty_prediction(
    timestamp: float,
    current_level: float,
    average_liters_per_day: float,
    now: datetime,
) -> datetime | None:
    """Return empty time only when freshness and horizon checks are plausible."""

    if current_level <= 0:
        return None

    measurement_time = datetime.fromtimestamp(timestamp)
    measurement_age = now - measurement_time
    if not timedelta(minutes=-5) <= measurement_age <= timedelta(
        hours=MAX_MEASUREMENT_AGE_HOURS
    ):
        return None

    days_until_empty = current_level / average_liters_per_day
    minimum_days = MIN_PREDICTION_HOURS / 24
    if not minimum_days <= days_until_empty <= MAX_PREDICTION_DAYS:
        return None
    predicted_empty_at = measurement_time + timedelta(days=days_until_empty)
    time_from_now = predicted_empty_at - now
    if not timedelta(hours=MIN_PREDICTION_HOURS) <= time_from_now <= timedelta(
        days=MAX_PREDICTION_DAYS
    ):
        return None
    return predicted_empty_at
