from collections import deque
from datetime import datetime
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from backend.water_usage import estimate_water_usage


BACKGROUND_COLOR = "#F4F7FB"
SURFACE_COLOR = "#FFFFFF"
PRIMARY_COLOR = "#2979FF"
TEXT_COLOR = "#172033"
MUTED_COLOR = "#667085"
GRID_COLOR = "#E4EAF1"


def plot_water_level_chart(sensor_data: deque) -> BytesIO:
    times = []
    for entry in sensor_data:
        ts = entry["timestamp"]
        if isinstance(ts, (int, float)):
            # считаем, что ts — это количество секунд с эпохи
            times.append(datetime.fromtimestamp(ts))
        else:
            times.append(ts)

    levels = [entry["water_level"] for entry in sensor_data]

    if not times:
        raise ValueError("Нет данных для построения графика")
    usage_estimate = estimate_water_usage(sensor_data)
    fig = Figure(figsize=(10, 5.2), dpi=140, facecolor=BACKGROUND_COLOR)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.set_facecolor(SURFACE_COLOR)

    level_range = max(levels) - min(levels)
    padding = max(level_range * 0.18, 0.5)
    lower_bound = max(0, min(levels) - padding)
    upper_bound = max(levels) + padding
    if lower_bound == upper_bound:
        upper_bound += 1

    ax.fill_between(times, levels, lower_bound, color=PRIMARY_COLOR, alpha=0.1, linewidth=0)
    ax.plot(
        times,
        levels,
        color=PRIMARY_COLOR,
        linewidth=2.8,
        solid_capstyle="round",
        solid_joinstyle="round",
        zorder=3,
    )

    if usage_estimate is not None:
        ax.plot(
            [usage_estimate.observed_from, usage_estimate.observed_until],
            [usage_estimate.trend_start_level, usage_estimate.trend_end_level],
            color="#7A5AF8",
            linewidth=2,
            linestyle=(0, (5, 4)),
            label="Тренд расхода",
            zorder=4,
        )

    if len(times) <= 30:
        ax.scatter(
            times,
            levels,
            s=24,
            color=SURFACE_COLOR,
            edgecolor=PRIMARY_COLOR,
            linewidth=1.5,
            zorder=4,
        )

    ax.scatter(
        times[-1],
        levels[-1],
        s=72,
        color=PRIMARY_COLOR,
        edgecolor=SURFACE_COLOR,
        linewidth=2.5,
        zorder=5,
    )
    ax.annotate(
        f"{levels[-1]:.1f} л",
        xy=(times[-1], levels[-1]),
        xytext=(-8, 17),
        textcoords="offset points",
        ha="right",
        va="bottom",
        color=SURFACE_COLOR,
        fontsize=10,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.45,rounding_size=0.8",
            "facecolor": PRIMARY_COLOR,
            "edgecolor": "none",
        },
        zorder=6,
    )

    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.DateFormatter("%d.%m\n%H:%M")
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:.1f} л"))

    ax.set_ylim(lower_bound, upper_bound)
    ax.margins(x=0.035)
    ax.set_title(
        "Уровень воды",
        loc="left",
        pad=24,
        color=TEXT_COLOR,
        fontsize=18,
        fontweight="bold",
    )
    subtitle = f"Динамика по {len(levels)} измерениям"
    if usage_estimate is not None:
        subtitle = f"Средний расход {usage_estimate.average_liters_per_day:.1f} л/день"
        if usage_estimate.predicted_empty_at is not None:
            subtitle += f"  •  Прогноз: {usage_estimate.predicted_empty_at:%d.%m, %H:%M}"

    ax.text(
        0,
        1.025,
        subtitle,
        transform=ax.transAxes,
        color=MUTED_COLOR,
        fontsize=10,
        va="bottom",
    )

    ax.grid(axis="y", color=GRID_COLOR, linewidth=1)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", colors=MUTED_COLOR, labelsize=9, length=0, pad=10)
    if usage_estimate is not None:
        ax.legend(
            loc="upper right",
            frameon=False,
            labelcolor=MUTED_COLOR,
            fontsize=9,
        )

    fig.subplots_adjust(left=0.1, right=0.96, top=0.82, bottom=0.18)
    buffer = BytesIO()
    try:
        fig.savefig(
            buffer,
            format="png",
            facecolor=fig.get_facecolor(),
            bbox_inches="tight",
        )
    finally:
        fig.clear()
    buffer.seek(0)
    return buffer
