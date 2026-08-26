import asyncio

import random

from backend.backend_main import send_chart_to_bot, bot, CHANNEL_ID, logic


async def main():
    logic._store_sensor_data(random.uniform(0, 20))

    await send_chart_to_bot(bot, CHANNEL_ID)


if __name__ == '__main__':
    asyncio.run(main())
