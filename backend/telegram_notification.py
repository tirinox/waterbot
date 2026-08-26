from aiogram.types import BufferedInputFile

from backend.chart import plot_water_level_chart


async def send_chart_notification(bot, channel, sensor_data, caption: str):
    chart = plot_water_level_chart(sensor_data)
    try:
        photo = BufferedInputFile(chart.read(), filename="chart.png")
        await bot.send_photo(channel, photo=photo, caption=caption)
    finally:
        chart.close()
