import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiohttp import web

from backend.bot_logic import WaterBotLogic
from backend.db import DB
from backend.http_api import create_sensor_app
from backend.telegram_notification import send_chart_notification
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
            await send_chart_notification(bot, CHANNEL_ID, logic.sensor_data, text)
    except Exception as e:
        logger.error(e)


logic = WaterBotLogic(db, cfg, send_message)


async def send_chart_to_bot(bot, channel):
    water_level = logic.last_water_level

    caption = (
        f"🤖 Текущий уровень воды: {logic.format_liter(water_level)}.\n"
        f"Точек сохранено: {len(logic.sensor_data)}."
    )
    await send_chart_notification(bot, channel, logic.sensor_data, caption)


@dp.message(Command('start'))
async def status_handler(message: Message):
    await send_chart_to_bot(message.bot, message.chat.id)


@dp.message(Command('tare'))
async def tare_handler(message: Message):
    logic.request_tare()
    await message.answer("⚖️ Команда тарирования поставлена в очередь.")


def create_app() -> web.Application:
    return create_sensor_app(logic, SHARED_SECRET, cfg.get("api", {}))


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
