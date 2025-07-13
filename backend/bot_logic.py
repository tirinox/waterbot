from datetime import datetime
from typing import Callable

from collections import deque

from backend.db import DB, Cooldown
from backend.utils import parse_timespan_to_seconds


class WaterBotLogic:
    def __init__(self, db: DB, cfg: dict, sender_method: Callable):
        self.db = db
        self.cfg = cfg
        self._send_message = sender_method
        self._sensor_data = deque(maxlen=10_000)

        cfg = cfg.get('logic', {})

        cd_normal = parse_timespan_to_seconds(cfg.get('cd_normal', '1d'))
        cd_warning = parse_timespan_to_seconds(cfg.get('cd_warning', '12h'))
        cd_critical = parse_timespan_to_seconds(cfg.get('cd_critical', '2h'))

        self._cd_normal = Cooldown(db, 'WaterAlertNormal', cd_normal)
        self._cd_warning = Cooldown(db, 'WaterAlertWarning', cd_warning)
        self._cd_critical = Cooldown(db, 'WaterCritical', cd_critical)

        level_warning = cfg.get('warning_level', 5.0)
        level_critical = cfg.get('critical_level', 2.0)

        self._warning_level = float(level_warning)
        self._critical_level = float(level_critical)

    @staticmethod
    def format_liter(liters):
        return f'{liters:0.1f} л.'

    async def _send_alert_normal(self, level_kg: float):
        await self._send_message(f"💧Вода: {self.format_liter(level_kg)} осталось.")

    async def _send_alert_warning(self, level_kg: float):
        await self._send_message(f"⚠️Внимание! Уровень воды {self.format_liter(level_kg)} ниже нормы!")

    async def _send_alert_critical(self, level_kg: float):
        await self._send_message(f"🚨Критический уровень воды: {self.format_liter(level_kg)}! Закажи воды!")

    async def on_sensor_data(self, sensor_kg: float):
        self._store_sensor_data(sensor_kg)

        if sensor_kg <= self._critical_level:
            if self._cd_critical.can_do():
                self._cd_critical.do()
                await self._send_alert_critical(sensor_kg)
        elif sensor_kg <= self._warning_level:
            if self._cd_warning.can_do():
                self._cd_warning.do()
                await self._send_alert_warning(sensor_kg)
        else:
            if self._cd_normal.can_do():
                self._cd_normal.do()
                await self._send_alert_normal(sensor_kg)

    def _store_sensor_data(self, sensor_kg):
        now = datetime.now()
        self._sensor_data.append({
            "water_level": sensor_kg,
            "timestamp": now.isoformat(),
        })

    @property
    def sensor_data(self):
        # noinspection PyTypeChecker
        return list(self._sensor_data)
