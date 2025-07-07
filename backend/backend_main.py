import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiohttp import web

from backend.utils import load_config, parse_timespan_to_seconds

cfg = load_config()

# === Configuration ===
SHARED_SECRET = cfg['iot']['shared_secret']  # Shared secret for IoT sensor authentication
HOST = cfg['api']['host']  # Host for HTTP server
PORT = cfg['api']['port']  # Port for HTTP server
BOT_TOKEN = cfg['telegram']['api_token']  # Telegram bot API token
CHANNEL_ID = cfg['telegram']['channel_id']  # Telegram channel ID to send alerts
THRESHOLD = cfg['logic']['threshold']  # Water level threshold
ALERT_INTERVAL = timedelta(
    seconds=parse_timespan_to_seconds(cfg['logic']['alert_interval']))  # Minimum interval between alerts

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Bot and Dispatcher ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Track the last alert timestamp
last_alert_time: datetime = datetime.min


# === Bot Command Handler ===
# @dp.message.register(Command(commands=["status"]))
# async def status_handler(message: Message):
#     await message.reply("🤖 Bot is up and running. Waiting for sensor data...")


# === HTTP Handler for IoT Sensor ===
async def handle_sensor(request: web.Request) -> web.Response:
    """
    Endpoint to receive water level data from IoT sensor.
    Expects JSON payload: { "water_level": <number> }
    """
    global last_alert_time
    try:
        data = await request.json()
        water_level = data.get("water_level")
        if water_level is None:
            return web.json_response({"error": "Missing 'water_level' field"}, status=400)

        now = datetime.now()
        logger.info(f"Received water level: {water_level} at {now.isoformat()} UTC")

        if water_level < THRESHOLD:
            # Check if enough time has passed since last alert
            if now - last_alert_time >= ALERT_INTERVAL:
                msg = f"⚠️ Water level is LOW: {water_level} (threshold: {THRESHOLD})"
                await bot.send_message(CHANNEL_ID, msg)
                last_alert_time = now
                logger.warning(f"Alert sent at {now.isoformat()}: {msg}")
            else:
                next_allowed = last_alert_time + ALERT_INTERVAL
                logger.info(f"Skipping alert. Next alert allowed after {next_allowed.isoformat()} UTC")

        return web.json_response({"status": "OK"}, status=200)

    except Exception as e:
        logger.error(f"Error handling sensor data: {e}")
        return web.json_response({"error": str(e)}, status=500)


# === Application Setup ===
def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post('/sensor', handle_sensor)
    return app


# === Main Entry Point ===
async def main():
    # Start HTTP server
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    logger.info(f"HTTP server listening on http://{HOST}:{PORT}/sensor")

    # Start polling Telegram bot
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    asyncio.run(main())
