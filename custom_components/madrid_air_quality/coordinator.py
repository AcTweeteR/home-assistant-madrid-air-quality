"""Coordinated polling and snapshot management."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import MadridAirQualityApi, MadridAirQualityApiError
from .const import (
    CONF_KNOWN_METRICS,
    CONF_STATIONS,
    DOMAIN,
    SOURCE_AIR,
    SOURCE_WEATHER,
    UPDATE_INTERVAL_MINUTES,
)
from .models import Snapshot
from .parser import parse_catalog, parse_measurements


def merge_metric_sources(
    fallback: dict[str, dict[str, Any]], online: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Prefer usable online readings while retaining safe CSV fallbacks."""
    merged = {station: dict(values) for station, values in fallback.items()}
    for station, values in online.items():
        station_metrics = merged.setdefault(station, {})
        for code, metric in values.items():
            if metric.valid or code not in station_metrics or not station_metrics[code].valid:
                station_metrics[code] = metric
    return merged


class MadridAirQualityCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: MadridAirQualityApi) -> None:
        self.entry = entry
        self.api = api
        self.station_codes = set(entry.data[CONF_STATIONS])
        self.catalog: dict[str, Any] = {}
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )

    async def async_load_catalog(self) -> dict[str, Any]:
        try:
            self.catalog = parse_catalog(await self.api.catalog())
        except (MadridAirQualityApiError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
        return self.catalog

    async def _async_update_data(self) -> Snapshot:
        try:
            if not self.catalog:
                await self.async_load_catalog()
            payloads = await self.api.measurements()
            now = dt_util.now()
            air_metrics, _ = parse_measurements(
                [payloads[0]], self.station_codes, now, SOURCE_AIR
            )
            fallback_weather, _ = parse_measurements(
                [payloads[1]], self.station_codes, now, SOURCE_WEATHER
            )
            metrics = merge_metric_sources(air_metrics, fallback_weather)
            online_results = await asyncio.gather(
                *(self.api.online_weather(station, now) for station in self.station_codes),
                return_exceptions=True,
            )
            errors: list[str] = []
            for station, result in zip(self.station_codes, online_results, strict=True):
                if isinstance(result, Exception):
                    errors.append(str(result))
                    continue
                metrics = merge_metric_sources(metrics, {station: result})
            stations = {code: self.catalog[code] for code in self.station_codes if code in self.catalog}
            known = {station: set(codes) for station, codes in self.entry.data.get(CONF_KNOWN_METRICS, {}).items()}
            for station, station_metrics in metrics.items():
                known.setdefault(station, set()).update(station_metrics)
            serialised_known = {station: sorted(codes) for station, codes in known.items()}
            if serialised_known != self.entry.data.get(CONF_KNOWN_METRICS, {}):
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    data={**self.entry.data, CONF_KNOWN_METRICS: serialised_known},
                )
            observed = max(
                (
                    metric.observed_at
                    for values in metrics.values()
                    for metric in values.values()
                    if metric.observed_at
                ),
                default=None,
            )
            return Snapshot(stations, metrics, observed or now, errors)
        except (MadridAirQualityApiError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
