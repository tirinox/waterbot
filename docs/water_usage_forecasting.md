# Water usage forecasting

Waterbot uses a guarded linear regression to answer two questions:

1. How many liters are being consumed per day on average?
2. If that rate continues, when will the current water supply reach zero?

The result is deliberately conservative. A mathematically valid line is not
automatically a believable forecast, so Waterbot publishes a prediction only
after the data and result pass several sanity checks.

## Processing pipeline

### 1. Validate and limit the history

Entries without finite numeric timestamps and water levels are ignored, as are
negative levels. The valid points are sorted by time and limited to the latest
seven days. The in-memory sensor history can be shorter than this limit.

### 2. Reduce sensor noise

The scale reports much more frequently than household water consumption
changes. Fitting every raw sample would give dense periods disproportionate
influence and make short-lived scale noise visible in the trend.

Measurements are therefore grouped into 30-minute buckets. Each bucket is
represented by its median water level and latest timestamp. The median is more
resistant to isolated high or low readings than an arithmetic mean.

### 3. Detect a refill

Regression must not connect the falling level of an old container to the high
starting level of a replacement. An increase of at least 1 liter between two
consecutive bucket medians is treated as a refill. Only measurements from the
latest detected refill onward are fitted.

### 4. Fit the falling line

For every retained measurement, time is converted to days since the first
point:

```text
x[i] = (timestamp[i] - first_timestamp) / 86,400
y[i] = water level in liters
```

Waterbot fits the ordinary least-squares line:

```text
predicted_level = intercept + slope * elapsed_days
```

The slope is calculated as:

```text
slope = sum((x[i] - mean(x)) * (y[i] - mean(y)))
        / sum((x[i] - mean(x)) ** 2)
```

A falling level has a negative slope. Average daily consumption is therefore:

```text
average_liters_per_day = -slope
```

Ordinary least squares minimizes the sum of squared vertical differences
between measured levels and the fitted line. It summarizes many noisy readings
with one average direction rather than extrapolating from only the first and
last measurements.

### 5. Check whether the line is adequate

Waterbot calculates R-squared (`R²`):

```text
R² = 1 - sum((actual - fitted) ** 2)
         / sum((actual - mean(actual)) ** 2)
```

`R²` describes how much of the observed level variation is explained by the
line. A value near 1 means the points follow the line closely. A value near 0
means the line explains little of their movement.

No usage estimate is shown unless all of these conditions pass:

| Check | Current bound | Purpose |
| --- | ---: | --- |
| Observation span | At least 6 hours | Avoid extrapolating a brief fluctuation |
| Median buckets | At least 4 | Require multiple independent time points |
| Daily consumption | 0.1–50 L/day | Reject flat, rising, or physically implausible slopes |
| R-squared | At least 0.35 | Reject data that is too erratic for a linear summary |

### 6. Predict the empty time

The newest level used for forecasting is the fitted level, not the last raw
reading. This keeps one noisy sensor sample from shifting the forecast.

```text
days_remaining = fitted_current_level / average_liters_per_day
empty_time = latest_measurement_time + days_remaining
```

The date is published only when all of these additional checks pass:

| Check | Current bound |
| --- | ---: |
| Latest measurement age | No more than 2 hours old |
| Future clock skew | No more than 5 minutes |
| Time remaining | Between 2 hours and 90 days |
| Forecast relative to now | Between 2 hours and 90 days in the future |

If the consumption trend is credible but the empty-time result fails one of
these checks, Waterbot still reports average liters per day but omits the
prediction. If the trend itself is unreliable, it reports neither value.

## Example

Suppose the fitted water level falls from 18 liters to 16 liters over 12 hours.
The regression slope is `-4 L/day`, so average consumption is `4 L/day`. With a
fitted current level of 16 liters:

```text
16 liters / 4 liters per day = 4 days remaining
```

If the newest measurement is fresh, the bot publishes a run-out time four days
after that measurement.

## Limitations

This is a trend forecast, not a physical guarantee. It assumes future average
use resembles recent average use. Holidays, guests, leaks, irregular usage,
partial refills smaller than 1 liter, scale movement, or calibration drift can
change the outcome. The quality and horizon gates reduce misleading output but
cannot remove that underlying uncertainty.
