import asyncio
import logging

import pytest
from aiohttp.test_utils import TestClient, TestServer

from backend.http_api import create_sensor_app

SECRET = "test-shared-secret"
AUTH_HEADERS = {"Authorization": f"Bearer {SECRET}"}


class FakeLogic:
    def __init__(self):
        self.received = []
        self.sensor_data = [{"water_level": 12, "timestamp": 1}]
        self.tare_requested = False
        self.tare_acknowledgements = 0

    async def on_sensor_data(self, value):
        self.received.append(value)

    def acknowledge_tare(self):
        self.tare_requested = False
        self.tare_acknowledgements += 1


async def _with_client(scenario, *, logic=None, config=None):
    logic = logic or FakeLogic()
    app = create_sensor_app(logic, SECRET, config)
    async with TestClient(TestServer(app)) as client:
        return await scenario(client, logic)


def test_post_accepts_header_and_existing_firmware_payload():
    async def scenario(client, logic):
        header_response = await client.post(
            "/sensor", json={"water_level": 10}, headers=AUTH_HEADERS
        )
        firmware_response = await client.post("/sensor", json={"water_level": 11, "secret": SECRET})
        return header_response.status, firmware_response.status, logic.received

    assert asyncio.run(_with_client(scenario)) == (200, 200, [10, 11])


def test_post_exposes_pending_tare_until_firmware_acknowledges_it():
    logic = FakeLogic()
    logic.tare_requested = True

    async def scenario(client, logic):
        command_response = await client.post("/sensor", json={"water_level": 10, "secret": SECRET})
        acknowledgement_response = await client.post(
            "/sensor",
            json={"water_level": 10, "secret": SECRET, "tare_completed": True},
        )
        return (
            await command_response.json(),
            await acknowledgement_response.json(),
            logic.tare_acknowledgements,
        )

    assert asyncio.run(_with_client(scenario, logic=logic)) == (
        {"status": "OK", "tare": True},
        {"status": "OK", "tare": False},
        1,
    )


def test_get_requires_header_authentication():
    async def scenario(client, _logic):
        unauthorized = await client.get("/sensor")
        authorized = await client.get("/sensor", headers=AUTH_HEADERS)
        return unauthorized, authorized.status, await authorized.json()

    unauthorized, status, data = asyncio.run(_with_client(scenario))
    assert unauthorized.status == 401
    assert unauthorized.headers["Cache-Control"] == "no-store"
    assert status == 200
    assert data == [{"water_level": 12, "timestamp": 1}]


@pytest.mark.parametrize("value", [True, "12", -1, 51, float("inf"), float("nan")])
def test_invalid_water_levels_are_rejected(value):
    async def scenario(client, logic):
        response = await client.post("/sensor", json={"water_level": value}, headers=AUTH_HEADERS)
        return response.status, logic.received

    assert asyncio.run(_with_client(scenario)) == (400, [])


def test_invalid_tare_acknowledgement_is_rejected():
    async def scenario(client, logic):
        response = await client.post(
            "/sensor",
            json={"water_level": 10, "tare_completed": "yes"},
            headers=AUTH_HEADERS,
        )
        return response.status, logic.received

    assert asyncio.run(_with_client(scenario)) == (400, [])


def test_wrong_secret_is_not_logged(caplog):
    wrong_secret = "never-log-this-value"

    async def scenario(client, _logic):
        response = await client.post("/sensor", json={"water_level": 10, "secret": wrong_secret})
        return response.status

    with caplog.at_level(logging.WARNING, logger="backend.http_api"):
        assert asyncio.run(_with_client(scenario)) == 401
    assert wrong_secret not in caplog.text


def test_request_size_and_rate_limits():
    async def size_scenario(client, _logic):
        response = await client.post(
            "/sensor",
            json={"water_level": 10, "padding": "x" * 1_000},
            headers=AUTH_HEADERS,
        )
        return response.status

    assert asyncio.run(_with_client(size_scenario, config={"max_request_size_bytes": 128})) == 413

    async def rate_scenario(client, _logic):
        statuses = []
        for _ in range(3):
            response = await client.post("/sensor", json={"water_level": 10}, headers=AUTH_HEADERS)
            statuses.append(response.status)
        return statuses

    assert asyncio.run(_with_client(rate_scenario, config={"rate_limit_requests": 2})) == [
        200,
        200,
        429,
    ]


def test_internal_errors_are_not_returned_to_clients():
    class FailingLogic(FakeLogic):
        async def on_sensor_data(self, value):
            raise RuntimeError("private internal detail")

    async def scenario(client, _logic):
        response = await client.post("/sensor", json={"water_level": 10}, headers=AUTH_HEADERS)
        return response.status, await response.json()

    assert asyncio.run(_with_client(scenario, logic=FailingLogic())) == (
        500,
        {"error": "internal server error"},
    )
