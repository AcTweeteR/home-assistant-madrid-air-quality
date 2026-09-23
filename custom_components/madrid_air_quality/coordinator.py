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
    MUNICIPAL_UPDATE_INTERVAL_MINUTES,
    SOURCE_AIR,
    SOURCE_MUNICIPAL_AIR,
    SOURCE_MUNICIPAL_WEATHER,
    SOURCE_WEATHER,
    UPDATE_INTERVAL_MINUTES,
)
from .models import Snapshot
from .parser import (
    parse_catalog,
    parse_measurements,
    parse_municipal_catalog,
    parse_municipal_measurements,
)


def merge_metric_sources(
    fallback: dict[str, dict[str, Any]], online: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Prefer usable online readings while retaining safe CSV fallbacks."""
    merged = {station: dict(values) for station, values in fallback.items()}
    for station, values in online.items():
        station_metrics = merged.setdefault(station, {})
        for code, metric in values.items():
            if (
                metric.valid
                or code not in station_metrics
                or not station_metrics[code].valid
            ):
                station_metrics[code] = metric
    return merged


class MadridAirQualityCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: MadridAirQualityApi
    ) -> None:
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
                *(
                    self.api.online_weather(station, now)
                    for station in self.station_codes
                ),
                return_exceptions=True,
            )
            errors: list[str] = []
            for station, result in zip(self.station_codes, online_results, strict=True):
                if isinstance(result, Exception):
                    errors.append(str(result))
                    continue
                metrics = merge_metric_sources(metrics, {station: result})
            stations = {
                code: self.catalog[code]
                for code in self.station_codes
                if code in self.catalog
            }
            known = {
                station: set(codes)
                for station, codes in self.entry.data.get(
                    CONF_KNOWN_METRICS, {}
                ).items()
            }
            for station, station_metrics in metrics.items():
                known.setdefault(station, set()).update(station_metrics)
            serialised_known = {
                station: sorted(codes) for station, codes in known.items()
            }
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


class MunicipalCoordinator(DataUpdateCoordinator[Snapshot]):
    """Municipal feeds share a polling cycle, independent of the regional feed."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: MadridAirQualityApi
    ) -> None:
        self.entry = entry
        self.api = api
        self.station_codes = {
            str(code)
            for code in entry.data[CONF_STATIONS]
            if str(code).startswith("28079")
        }
        self.catalog: dict[str, Any] = {}
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}_municipal",
            update_interval=timedelta(minutes=MUNICIPAL_UPDATE_INTERVAL_MINUTES),
        )

    async def async_load_catalog(self) -> dict[str, Any]:
        try:
            air, weather = await self.api.municipal_catalogs()
            self.catalog = parse_municipal_catalog(air, weather)
        except (MadridAirQualityApiError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
        return self.catalog

    async def _async_update_data(self) -> Snapshot:
        if not self.catalog:
            await self.async_load_catalog()
        now = dt_util.now()
        payloads = await asyncio.gather(
            self.api.municipal_air(),
            self.api.municipal_weather(),
            return_exceptions=True,
        )
        if all(isinstance(payload, Exception) for payload in payloads):
            raise UpdateFailed("Las dos fuentes municipales no están disponibles")
        metrics: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        sources = (SOURCE_MUNICIPAL_AIR, SOURCE_MUNICIPAL_WEATHER)
        for index, (payload, source) in enumerate(zip(payloads, sources, strict=True)):
            previous = {
                station: {
                    code: metric
                    for code, metric in values.items()
                    if metric.data_source == source
                    and metric.observed_at
                    and now - metric.observed_at <= timedelta(hours=4)
                }
                for station, values in (self.data.metrics if self.data else {}).items()
            }
            if isinstance(payload, Exception):
                errors.append(f"{source}: {payload}")
                metrics = merge_metric_sources(metrics, previous)
                continue
            try:
                selected = self.station_codes
                if index == 1:
                    selected = {
                        code
                        for code in selected
                        if self.catalog.get(code)
                        and self.catalog[code].weather_colocated
                    }
                parsed = parse_municipal_measurements(payload, selected, now, source)
            except ValueError as err:
                errors.append(f"{source}: {err}")
                continue
            metrics = merge_metric_sources(
                metrics, merge_metric_sources(previous, parsed)
            )
        if not metrics and errors:
            raise UpdateFailed("; ".join(errors))
        stations = {
            code: self.catalog[code]
            for code in self.station_codes
            if code in self.catalog
        }
        known = {
            station: set(codes)
            for station, codes in self.entry.data.get(CONF_KNOWN_METRICS, {}).items()
        }
        for station, values in metrics.items():
            known.setdefault(station, set()).update(values)
        serialised = {station: sorted(codes) for station, codes in known.items()}
        if serialised != self.entry.data.get(CONF_KNOWN_METRICS, {}):
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, CONF_KNOWN_METRICS: serialised}
            )
        latest = max(
            (
                metric.observed_at
                for values in metrics.values()
                for metric in values.values()
                if metric.observed_at
            ),
            default=now,
        )
        return Snapshot(stations, metrics, latest, errors)
