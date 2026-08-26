# AGENTS.md

These instructions apply to the entire repository. Keep them current when project structure, tooling, or operational workflows change.

## Project overview

Waterbot has two distinct runtimes:

- `backend/` is a Python 3.12 service. It runs an `aiohttp` API, an `aiogram` Telegram bot, alert/cooldown logic, chart rendering, and JSON-file persistence.
- `iot_code/` is MicroPython firmware for a Wi-Fi-connected scale using an HX711 load-cell ADC. It reads the scale and posts measurements to the backend.

Do not assume code that works under CPython also works under MicroPython. Keep runtime-specific imports and dependencies on their respective sides.

## Repository map

- `backend/backend_main.py`: process entry point, Telegram handlers, and HTTP routes.
- `backend/bot_logic.py`: water-level history, threshold selection, cooldowns, and alerts.
- `backend/db.py`: small JSON-backed state store and cooldown persistence.
- `backend/chart.py`: in-memory PNG chart generation.
- `backend/utils.py`: configuration loading and duration parsing.
- `backend/dbg_*.py`: interactive or live diagnostic scripts, not an automated test suite.
- `iot_code/main.py`: firmware entry point.
- `iot_code/sensor_send.py`: Wi-Fi connection, scale polling, and HTTP submission loop.
- `iot_code/drivers/`: hardware drivers.
- `iot_code/playground/`: manual hardware experiments.
- `example.config.yaml`: documented configuration template.
- `pyproject.toml` and `uv.lock`: backend dependency and Python version definitions.
- `Dockerfile` and `compose.yaml`: reproducible non-root backend container and persistent state.
- `Makefile`: local quality, runtime, and container workflow shortcuts.

## Setup and configuration

Use Python 3.12 and the checked-in `uv.lock`. The usual environment setup is:

```sh
uv sync
cp example.config.yaml config.yaml
```

Fill `config.yaml` with local values before running the service. The application expects to be launched from the repository root because `config.yaml` and `db.json` are resolved relative to the current working directory.

The following files contain credentials or mutable local state and are intentionally ignored:

- `config.yaml`
- `db.json`
- `iot_code/private_const.py`

Never commit, paste into logs, or expose values from these files. Update `example.config.yaml` with placeholders when adding configuration keys. Keep backend and firmware configuration names synchronized.

Use `make sync-config-dry-run` to validate firmware configuration before `make sync-config` generates `iot_code/private_const.py`. The generator uses repository-relative defaults, does not print values, and supports explicit `--config` and `--target` overrides. Treat the generated file as a secret and do not display its contents.

## Running and interfaces

Start the configured backend from the repository root:

```sh
make run
```

This is a live operation: it reads real configuration and state, starts network listeners and Telegram polling, and may send messages. Do not run it as a routine validation step.

The sensor API contract is:

- `POST /sensor` accepts a numeric `water_level` and authenticates with a Bearer/header secret or the firmware-compatible JSON `secret` field.
- `GET /sensor` requires header authentication and returns the recent in-memory measurement list.
- Request size, rate, and accepted water-level range are configured under `api`.

The firmware requires MicroPython, a connected board, Wi-Fi credentials, and calibrated pin/scale constants. No board flashing or deployment command is documented in this repository. Do not invent one; ask for or document the actual board workflow when hardware deployment is in scope.

## Development guidelines

- Preserve the separation between transport/orchestration in `backend_main.py` and domain behavior in `bot_logic.py`.
- Keep bot and HTTP work asynchronous. Inject or mock the async sender when testing alert logic.
- Treat the JSON schema in `DB` as persistent state. Make migrations or backward-compatible reads explicit when changing stored keys or sensor entries.
- Preserve the bounded sensor history (`deque(..., maxlen=10_000)`) unless requirements explicitly change it.
- Validate incoming API values at the boundary before they reach comparison, persistence, or chart code.
- Keep user-facing bot/chart text consistent with the existing Russian-language interface unless a task requests localization.
- Centralize hardware pins and calibration values rather than duplicating literals.
- Keep MicroPython code conservative: avoid CPython-only libraries and features, and close network responses promptly.
- Ruff is configured for conservative linting across the repository and formatting of `tests/`. Follow the surrounding style in legacy application/firmware files and avoid unrelated mass formatting.
- Do not edit generated metadata (`waterbot.egg-info/`) or local IDE/virtual-environment files.

`iot_code/lib/` contains required firmware source and must remain trackable. Keep only actual private/generated firmware files, such as `iot_code/private_const.py`, ignored.

## Validation

The project uses pytest and Ruff. Formatting enforcement initially covers `tests/` only so that maintenance work does not rewrite legacy backend or MicroPython sources. Use the smallest relevant checks and report exactly what was run. The full safe check suite is:

```sh
make check
```

In a prepared local checkout, `.venv/bin/python` may be used instead of `uv run python` when dependency-cache access is restricted.

Add `pytest` tests under `tests/` for pure logic. Use a temporary path for `DB`, a fake async sender for `WaterBotLogic`, and deterministic timestamps where cooldown behavior matters. Avoid importing `backend.backend_main` in unit tests because it loads local configuration and initializes bot/database globals at import time.

Treat these as manual/integration checks rather than unit tests:

- `backend/dbg_cd_test.py` blocks on terminal input.
- `backend/dbg_live_test.py` sends HTTP requests to the configured server.
- `backend/dbg_chart_test.py` imports live bot configuration and sends a Telegram photo.
- Everything in `iot_code/playground/` requires MicroPython hardware.

Do not run network-, Telegram-, or hardware-facing checks unless the task requires them and suitable local credentials/devices are available. For changes spanning the API boundary, verify that the backend route, `example.config.yaml`, and firmware payload/URL remain compatible.

## Change discipline

- Inspect `git status` before and after edits; preserve unrelated user changes.
- Keep changes narrowly scoped and update documentation/config examples when behavior changes.
- Add or update tests for behavior changes when practical. If hardware or live integrations prevent full verification, state that limitation clearly.
- Never commit secrets, generated runtime state, calibration data specific to a private device, or captured user/chat data.
