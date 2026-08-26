from collections import deque
from datetime import datetime
from statistics import median
from typing import Callable

from backend.db import DB, Cooldown
from backend.utils import parse_timespan_to_seconds


class WaterBotLogic:
    """Store sensor data and send alerts only after the scale has stabilized."""

    def __init__(
        self,
        db: DB,
        cfg: dict,
        sender_method: Callable,
        clock: Callable[[], datetime] = datetime.now,
    ):
        self.db = db
        self.cfg = cfg
        self._send_message = sender_method
        self._clock = clock

        save_sensor_data = db.get('sensor_data', [])
        self._sensor_data = deque(save_sensor_data, maxlen=10_000)
        self._stability_samples = deque()
        self._last_water_level = 0.0
        self._tare_requested = db.get('tare_requested', False) is True

        cfg = cfg.get('logic', {})

        cd_normal = parse_timespan_to_seconds(cfg.get('cd_normal', '1d'))
        cd_warning = parse_timespan_to_seconds(cfg.get('cd_warning', '12h'))
        cd_critical = parse_timespan_to_seconds(cfg.get('cd_critical', '2h'))

        self._cd_normal = Cooldown(db, 'WaterAlertNormal', cd_normal)
        self._cd_warning = Cooldown(db, 'WaterAlertWarning', cd_warning)
        self._cd_critical = Cooldown(db, 'WaterCritical', cd_critical)

        level_warning = cfg.get('warning_level', 5.0)
        level_critical = cfg.get('critical_level', 2.0)
        stability_period = parse_timespan_to_seconds(cfg.get('stability_period', '1m'))

        self._warning_level = float(level_warning)
        self._critical_level = float(level_critical)
        self._stability_period_sec = float(stability_period)
        self._stability_tolerance = float(cfg.get('stability_tolerance', 0.2))
        self._stability_min_samples = int(cfg.get('stability_min_samples', 3))

        if self._stability_period_sec < 0:
            raise ValueError("logic.stability_period must not be negative")
        if self._stability_tolerance < 0:
            raise ValueError("logic.stability_tolerance must not be negative")
        if self._stability_min_samples < 1:
            raise ValueError("logic.stability_min_samples must be at least 1")

    @property
    def last_water_level(self):
        return self._last_water_level

    @staticmethod
    def format_liter(liters):
        return f'{liters:0.1f} л.'

    @property
    def tare_requested(self):
        return self._tare_requested

    def request_tare(self):
        self._tare_requested = True
        self.db['tare_requested'] = True
        self.db.save()

    def acknowledge_tare(self):
        if not self._tare_requested:
            return
        self._tare_requested = False
        self.db['tare_requested'] = False
        self.db.save()

    async def _send_alert_normal(self, level_kg: float):
        await self._send_message(f"💧Вода: {self.format_liter(level_kg)} осталось.")

    async def _send_alert_warning(self, level_kg: float):
        await self._send_message(f"⚠️Внимание! Уровень воды {self.format_liter(level_kg)} ниже нормы!")

    async def _send_alert_critical(self, level_kg: float):
        await self._send_message(f"🚨Критический уровень воды: {self.format_liter(level_kg)}! Закажи воды!")

    async def on_sensor_data(self, sensor_kg: float):
        """Store a reading and evaluate alerts after a stable measurement window.

        Stability is a rolling time window whose total level spread must remain
        within ``logic.stability_tolerance``.  A sudden change remains in the
        window for the configured period, naturally delaying alerts until a
        complete calm window has accumulated.  The window median is used for
        threshold selection and message text to reduce boundary noise.
        """

        now = self._clock()
        self._store_sensor_data(sensor_kg, now)
        stable_level = self._stable_level(sensor_kg, now)
        if stable_level is None:
            return

        if stable_level <= self._critical_level:
            if self._cd_critical.can_do():
                self._cd_critical.do()
                await self._send_alert_critical(stable_level)
        elif stable_level <= self._warning_level:
            if self._cd_warning.can_do():
                self._cd_warning.do()
                await self._send_alert_warning(stable_level)
        else:
            if self._cd_normal.can_do():
                self._cd_normal.do()
                await self._send_alert_normal(stable_level)

    def _stable_level(self, water_level: float, now: datetime) -> float | None:
        """Return the window median once readings are sufficiently calm and old."""

        timestamp = now.timestamp()
        if self._stability_samples and timestamp < self._stability_samples[-1][0]:
            self._stability_samples.clear()
        self._stability_samples.append((timestamp, water_level))

        cutoff = timestamp - self._stability_period_sec
        # Keep the nearest sample at or before the cutoff as a time anchor. If
        # polling has a little jitter, pruning every older sample would leave a
        # window just under the required duration forever.
        while (
            len(self._stability_samples) > 1
            and self._stability_samples[1][0] <= cutoff
        ):
            self._stability_samples.popleft()

        if len(self._stability_samples) < self._stability_min_samples:
            return None
        if self._stability_samples[-1][0] - self._stability_samples[0][0] < (
            self._stability_period_sec
        ):
            return None

        levels = [sample[1] for sample in self._stability_samples]
        if max(levels) - min(levels) > self._stability_tolerance:
            return None
        return float(median(levels))

    def _store_sensor_data(self, water_level, now: datetime):
        self._last_water_level = water_level
        self._sensor_data.append({
            "water_level": water_level,
            "timestamp": now.timestamp(),
            "datetime": now.isoformat(),
        })
        # noinspection PyTypeChecker
        self.db["sensor_data"] = list(self._sensor_data)
        self.db.save_sometimes()

    @property
    def sensor_data(self):
        # noinspection PyTypeChecker
        return list(self._sensor_data)
