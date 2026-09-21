"""Coordinated polling and snapshot management."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import MadridAirQualityApi, MadridAirQualityApiError
from .const import CONF_KNOWN_METRICS, CONF_STATIONS, DOMAIN, UPDATE_INTERVAL_MINUTES
from .models import Snapshot
from .parser import parse_catalog, parse_measurements


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
            metrics, observed = parse_measurements(payloads, self.station_codes)
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
            return Snapshot(stations, metrics, observed or dt_util.now())
        except (MadridAirQualityApiError, ValueError) as err:
            raise UpdateFailed(str(err)) from err
