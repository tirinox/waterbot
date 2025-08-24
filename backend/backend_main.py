import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiohttp import web

from backend.bot_logic import WaterBotLogic
from backend.chart import plot_water_level_chart
from backend.db import DB
from backend.utils import load_config

cfg = load_config()

SHARED_SECRET = cfg['iot']['shared_secret']  # Shared secret for IoT sensor authentication
HOST = cfg['api']['host']  # Host for HTTP server
PORT = cfg['api']['port']  # Port for HTTP server
BOT_TOKEN = cfg['telegram']['api_token']  # Telegram bot API token
CHANNEL_ID = cfg['telegram']['channel_id']  # Telegram channel ID to send alerts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()
db.load()


def graceful_shutdown(signum, frame):
    print(f"Received signal {signum!r}, saving database…")
    try:
        db.save()
        print("Database saved ✅")
    except Exception as e:
        print(f"Error saving database: {e!r}", file=sys.stderr)
    finally:
        sys.exit(0)


# catch signal and save DB on exit
signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)


async def send_message(text):
    try:
        if text and isinstance(text, str):
            await bot.send_message(CHANNEL_ID, text)
    except Exception as e:
        logger.error(e)


logic = WaterBotLogic(db, cfg, send_message)


async def send_chart_to_bot(bot, channel):
    water_level = logic.last_water_level

    caption = (f"🤖 Текущий уровень воды: {logic.format_liter(water_level)}.\n"
               f"Точек сохранено: {len(logic.sensor_data)}.")

    chart = plot_water_level_chart(logic.sensor_data)

    media = BufferedInputFile(
        file=chart.read(),
        filename='chart.png'
    )

    await bot.send_photo(channel, photo=media, caption=caption)

    chart.close()


@dp.message(Command('start'))
async def status_handler(message: Message):
    await send_chart_to_bot(message.bot, message.chat.id)


async def handle_sensor(request: web.Request) -> web.Response:
    """
    Endpoint to receive water level data from IoT sensor.
    Expects JSON payload: { "water_level": <number> }
    """
    try:
        data = await request.json()

        secret = data.get("secret")
        if secret != SHARED_SECRET:
            logger.error(f"Secret does not match, got {secret}")
            return web.json_response({"error": "wrong secret"}, status=401)

        water_level = data.get("water_level")
        if water_level is None:
            return web.json_response({"error": "Missing 'water_level' field"}, status=400)

        logger.info(f"Received water level: {water_level}")

        await logic.on_sensor_data(water_level)

        return web.json_response({"status": "OK"}, status=200)

    except Exception as e:
        logger.error(f"Error handling sensor data: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handler_recent_sensor_data(_: web.Request) -> web.Response:
    return web.json_response(logic.sensor_data)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post('/sensor', handle_sensor)
    app.router.add_get('/sensor', handler_recent_sensor_data)
    return app


async def main():
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    logger.info(f"HTTP server listening on http://{HOST}:{PORT}/sensor")

    me = await bot.get_me()
    print(f"Bot started as {me.full_name} (ID: {me.id}, Username: @{me.username})")
    # Start polling Telegram bot
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    asyncio.run(main())
