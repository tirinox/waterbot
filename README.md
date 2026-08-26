# Waterbot

Waterbot monitors the weight of a water bottle and sends Telegram alerts as the measured level crosses configured thresholds.

The repository contains two runtimes:

- `backend/`: a Python 3.12 `aiohttp` service and `aiogram` Telegram bot.
- `iot_code/`: MicroPython firmware for a Wi-Fi-connected HX711 scale.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker with Compose, if using the container workflow
- A Telegram bot token and destination channel ID
- MicroPython hardware for firmware work

## Local setup

Install the locked backend and development dependencies, then create the local configuration:

```sh
make setup
make config
```

Edit `config.yaml` and replace every placeholder. This file contains credentials and is ignored by Git.

Run the backend from the repository root:

```sh
make run
```

This starts a live HTTP listener and Telegram polling. It may send messages to the configured channel.

## Container workflow

The Compose service builds a non-root container, mounts `config.yaml` read-only, and stores `db.json` in the named `waterbot-data` volume.

The `api.port` value in `config.yaml` must match `WATERBOT_PORT`, which defaults to `9421`:

```sh
make config
make docker-up
make docker-logs
```

To use another port, update `api.port` in `config.yaml` and pass the same value to Compose:

```sh
WATERBOT_PORT=8080 make docker-up
```

Common container commands:

| Command | Purpose |
| --- | --- |
| `make docker-config` | Validate the rendered Compose configuration |
| `make docker-build` | Build the image |
| `make docker-up` | Build and start in the background |
| `make docker-logs` | Follow recent backend logs |
| `make docker-ps` | Show service status |
| `make docker-shell` | Start a disposable shell in the image |
| `make docker-exec` | Open a shell in the running service |
| `make docker-restart` | Restart the backend service |
| `make docker-stop` / `make docker-start` | Stop or start existing containers |
| `make docker-down` | Remove containers and network, preserving database data |

`docker-down` intentionally keeps the named database volume. Do not use `docker compose down --volumes` unless permanent deletion of stored sensor history is intended.

## Sensor API

The backend exposes the following routes:

- `POST /sensor`: accept an authenticated measurement and return pending device commands.
- `GET /sensor`: return recent measurements to an authenticated client.

Example request from a trusted development environment:

```sh
curl --fail-with-body \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer <SHARED_SECRET>' \
  --data '{"water_level": 12}' \
  http://127.0.0.1:9421/sensor
```

Read recent measurements with the same header:

```sh
curl --fail-with-body \
  --header 'Authorization: Bearer <SHARED_SECRET>' \
  http://127.0.0.1:9421/sensor
```

For compatibility, firmware POST requests may continue to include `secret` in the JSON body. GET requests require the Bearer header. Requests are size- and rate-limited, and `water_level` must be a finite number inside the configured range.

Sending `/tare` to the Telegram bot queues a persistent scale-tare command. The next successful
firmware POST receives `{"status": "OK", "tare": true}`. After taring, the firmware sends
`"tare_completed": true`; the backend then clears the command. Keep the scale unloaded while
taring.

The firmware's `iot.callback_host` must be the complete endpoint URL, including `/sensor`. Use HTTPS whenever traffic leaves a trusted private network. See [SECURITY.md](SECURITY.md) before exposing the service.

## Quality checks

Run all safe local checks:

```sh
make check
```

Individual commands are also available:

```sh
make format-check
make lint
make test
make compile
```

The scripts named `backend/dbg_*.py` are manual integration tools. Some contact the configured server or Telegram account and must not be treated as automated tests.

## Firmware

Firmware code lives in `iot_code/` and is not installed into the backend environment. Optional host-side ESP and MicroPython tooling can be installed with:

```sh
make setup-hardware
```

Before deploying firmware:

1. Validate and generate `iot_code/private_const.py` from trusted local configuration:

   ```sh
   make sync-config-dry-run
   make sync-config
   ```

   The generator resolves its default paths from the repository, never prints configuration values, replaces the target atomically, and sets its permissions to owner read/write (`0600`). Use `uv run python -m backend.sync_config --help` to see explicit source and target overrides.

2. Confirm the board-specific pins and `SCALE_FACTOR` calibration.
3. Ensure `CALLBACK_HOST` ends with `/sensor` and uses the intended scheme and port.

Connect a board that already has MicroPython installed, then upload the application and restart it:

```sh
make iot-upload
```

The command regenerates `iot_code/private_const.py`, copies the application to the board's
filesystem root with `mpremote`, and performs a soft reset. It does not install or replace the
MicroPython firmware itself.

`mpremote` automatically selects the serial device when only one is connected. On macOS, list
devices or select one explicitly when needed:

```sh
make iot-ports
make iot-upload PORT=/dev/cu.usbserial-0001
make iot-repl PORT=/dev/cu.usbserial-0001
```

Close PyCharm's MicroPython console before uploading so it releases the serial port. If the
board does not already run MicroPython, its exact model and firmware version are still required
before adding a flashing command.

## Project commands

Run `make` or `make help` to list the supported local and container workflows.
