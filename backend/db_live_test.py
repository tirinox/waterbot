import asyncio

from aiogram.client.session import aiohttp

from backend.utils import load_config

cfg = load_config()
SHARED_SECRET = cfg['iot']['shared_secret']  # Shared secret for IoT sensor authentication
HOST = cfg['api']['host']  # Host for HTTP server
PORT = cfg['api']['port']  # Port for HTTP server


async def send_test_water_level(session, water_level):
    sensor_url = f'http://{HOST}:{PORT}/sensor'
    async with session.post(sensor_url, json={
        "water_level": water_level,
        "secret": SHARED_SECRET
    }) as response:
        print(f"Response status: {response.status}")


async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            water_level = input("Enter water level (or hit enter to quit): ")
            if not water_level:
                break

            try:
                water_level = float(water_level)
                await send_test_water_level(session, water_level)
            except ValueError:
                print("Invalid input. Please enter a number.")


if __name__ == '__main__':
    asyncio.run(main())
