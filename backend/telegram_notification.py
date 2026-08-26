from aiogram.types import BufferedInputFile

from backend.chart import plot_water_level_chart
from backend.water_usage import estimate_water_usage, format_water_usage_summary


async def send_chart_notification(bot, channel, sensor_data, caption: str):
    chart = plot_water_level_chart(sensor_data)
    try:
        photo = BufferedInputFile(chart.read(), filename="chart.png")
        usage_summary = format_water_usage_summary(estimate_water_usage(sensor_data))
        if usage_summary:
            caption = f"{caption}\n\n{usage_summary}"
        await bot.send_photo(channel, photo=photo, caption=caption)
    finally:
        chart.close()
