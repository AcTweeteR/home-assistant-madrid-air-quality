"""Location-based model readings and local astronomical events."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from astral import Observer
from astral.sun import sunrise, sunset
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import MadridAirQualityApi, MadridAirQualityApiError
from .const import DOMAIN, MODEL_UPDATE_INTERVAL_MINUTES, SOLAR_UPDATE_INTERVAL_MINUTES
from .models import Station

LOGGER = logging.getLogger(__name__)
MADRID = ZoneInfo("Europe/Madrid")

# The states are Home Assistant weather condition values. WMO codes describe
# present weather; a code does not justify additional inferred phenomena.
WEATHER_CONDITIONS = frozenset(
    {
        "sunny",
        "clear-night",
        "partlycloudy",
        "cloudy",
        "fog",
        "rainy",
        "pouring",
        "snowy",
        "snowy-rainy",
        "hail",
        "lightning",
        "lightning-rainy",
    }
)


def weather_condition(code: int | None, is_day: bool | None) -> str | None:
    """Translate the Open-Meteo WMO subset without inventing phenomena."""
    if code in (0, 1):
        if is_day is None:
            return None
        return "sunny" if is_day else "clear-night"
    if code == 2:
        return "partlycloudy"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 66, 80, 81):
        return "rainy"
    if code in (65, 67, 82):
        return "pouring"
    if code in (71, 73, 75, 77, 85, 86):
        return "snowy"
    if code == 95:
        return "lightning-rainy"
    if code in (96, 99):
        # These WMO codes explicitly report hail with a thunderstorm.
        # HA has no combined lightning/hail condition: preserve the raw code.
        return "lightning"
    return None


@dataclass(frozen=True)
class ModelReading:
    apparent_temperature: float | None
    weather_code: int | None
    is_day: bool | None
    observed_at: datetime


def parse_model_weather(
    payload: Any, stations: list[Station]
) -> dict[str, ModelReading]:
    """Match the documented multi-coordinate response by request order."""
    rows = payload if isinstance(payload, list) else [payload]
    if len(rows) != len(stations) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("Open-Meteo devolvió un número inesperado de ubicaciones")
    result: dict[str, ModelReading] = {}
    for index, (station, row) in enumerate(zip(stations, rows, strict=True)):
        if index and row.get("location_id") != index:
            raise ValueError("Open-Meteo devolvió ubicaciones fuera de orden")
        current = row.get("current")
        if (
            not isinstance(current, dict)
            or row.get("current_units", {}).get("apparent_temperature") != "°C"
        ):
            raise ValueError("Open-Meteo cambió el esquema o la unidad")
        try:
            observed = datetime.fromtimestamp(int(current["time"]), tz=UTC)
        except (KeyError, TypeError, ValueError, OverflowError) as err:
            raise ValueError("Timestamp inválido de Open-Meteo") from err
        raw_temperature = current.get("apparent_temperature")
        temperature = (
            float(raw_temperature)
            if isinstance(raw_temperature, (int, float))
            and not isinstance(raw_temperature, bool)
            and math.isfinite(raw_temperature)
            else None
        )
        raw_code = current.get("weather_code")
        code = (
            int(raw_code)
            if isinstance(raw_code, int) and not isinstance(raw_code, bool)
            else None
        )
        raw_day = current.get("is_day")
        day = (
            bool(raw_day)
            if raw_day in (0, 1) and not isinstance(raw_day, bool)
            else None
        )
        result[station.code] = ModelReading(temperature, code, day, observed)
    return result


class OpenMeteoCoordinator(DataUpdateCoordinator[dict[str, ModelReading]]):
    """One HTTP request for all selected station coordinates."""

    def __init__(
        self, hass: HomeAssistant, api: MadridAirQualityApi, stations: list[Station]
    ) -> None:
        self.api = api
        self.stations = stations
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_open_meteo",
            update_interval=timedelta(minutes=MODEL_UPDATE_INTERVAL_MINUTES),
        )

    async def _async_update_data(self) -> dict[str, ModelReading]:
        try:
            return parse_model_weather(
                await self.api.model_weather(self.stations), self.stations
            )
        except (MadridAirQualityApiError, ValueError) as err:
            raise UpdateFailed(str(err)) from err


def next_solar_event(station: Station, event: str, now: datetime) -> datetime:
    """Return the next event in Madrid local time, including DST changes."""
    if station.latitude is None or station.longitude is None:
        raise ValueError("La estación no tiene coordenadas oficiales")
    observer = Observer(station.latitude, station.longitude)
    local_now = now.astimezone(MADRID)
    local_date: date = local_now.date()
    calculate = sunrise if event == "sunrise" else sunset
    result = calculate(observer, date=local_date, tzinfo=MADRID)
    if result <= local_now:
        result = calculate(observer, date=local_date + timedelta(days=1), tzinfo=MADRID)
    return result


class SolarCoordinator(DataUpdateCoordinator[dict[str, dict[str, datetime]]]):
    """Local shared timer: no external service or model dependency."""

    def __init__(self, hass: HomeAssistant, stations: list[Station]) -> None:
        self.stations = stations
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_solar",
            update_interval=timedelta(minutes=SOLAR_UPDATE_INTERVAL_MINUTES),
        )

    async def _async_update_data(self) -> dict[str, dict[str, datetime]]:
        now = dt_util.now()
        return {
            station.code: {
                "sunrise": next_solar_event(station, "sunrise", now),
                "sunset": next_solar_event(station, "sunset", now),
            }
            for station in self.stations
            if station.latitude is not None and station.longitude is not None
        }
