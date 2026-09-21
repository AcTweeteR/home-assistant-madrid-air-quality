"""Dynamic sensors for every magnitude published by each station."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_KNOWN_METRICS, DOMAIN, MAGNITUDES
from .coordinator import MadridAirQualityCoordinator
from .models import Metric, Station


def _device_class(code: str) -> SensorDeviceClass | None:
    return {
        "83": SensorDeviceClass.TEMPERATURE,
        "86": SensorDeviceClass.HUMIDITY,
        "87": SensorDeviceClass.PRESSURE,
        "81": SensorDeviceClass.WIND_SPEED,
        "88": SensorDeviceClass.IRRADIANCE,
        "9": SensorDeviceClass.PM25,
        "10": SensorDeviceClass.PM10,
        "11": SensorDeviceClass.PM1,
    }.get(code)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable) -> None:
    coordinator: MadridAirQualityCoordinator = entry.runtime_data
    created: set[tuple[str, str]] = set()

    @callback
    def add_new_entities() -> None:
        entities = []
        known_metrics = coordinator.entry.data.get(CONF_KNOWN_METRICS, {})
        for station_code, station in coordinator.data.stations.items():
            if not station:
                continue
            codes = set(known_metrics.get(station_code, []))
            codes.update(coordinator.data.metrics.get(station_code, {}))
            for code in codes:
                key = (station_code, code)
                if key not in created:
                    created.add(key)
                    entities.append(MadridSensor(coordinator, station, code))
        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class MadridSensor(CoordinatorEntity[MadridAirQualityCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: MadridAirQualityCoordinator, station: Station, code: str) -> None:
        super().__init__(coordinator)
        self._station = station
        self._code = code
        self._attr_unique_id = f"{DOMAIN}_{station.code}_{code.lower()}"
        self._attr_name = self._name_for(code)
        if code in MAGNITUDES:
            self._attr_translation_key = f"magnitude_{code}"
        self._attr_device_class = _device_class(code)
        self._attr_icon = "mdi:air-filter" if code not in {"81", "82", "83", "86", "87", "88", "89"} else "mdi:weather-windy"

    def _name_for(self, code: str) -> str:
        name, abbreviation, _ = MAGNITUDES.get(code, (f"Magnitud {code}", None, None))
        return f"{name} ({abbreviation})" if abbreviation else name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._station.code)},
            name=self._station.name,
            manufacturer="Comunidad de Madrid",
            model="Red de Calidad del Aire",
            serial_number=self._station.code,
            configuration_url="https://www.comunidad.madrid/servicios/urbanismo-medio-ambiente/calidad-aire",
            suggested_area=self._station.municipality,
        )

    @property
    def native_value(self) -> float | None:
        metric = self._metric
        return metric.value if metric and metric.valid else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._metric.unit if self._metric else MAGNITUDES.get(self._code, (None, None, None))[2]

    @property
    def available(self) -> bool:
        return super().available and self._metric is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        metric = self._metric
        return {
            "official_station_code": self._station.code,
            "official_magnitude_code": self._code,
            "official_abbreviation": metric.abbreviation if metric else None,
            "observation_time": metric.observed_at.isoformat() if metric and metric.observed_at else None,
            "official_validation": metric.raw_validation if metric else None,
        }

    @property
    def _metric(self) -> Metric | None:
        return self.coordinator.data.metrics.get(self._station.code, {}).get(self._code) if self.coordinator.data else None
