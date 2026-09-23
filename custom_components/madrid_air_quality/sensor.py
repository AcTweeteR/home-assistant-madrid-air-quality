"""Dynamic sensors for every magnitude published by each station."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
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

from .const import (
    CONF_KNOWN_METRICS,
    DOMAIN,
    MAGNITUDES,
    SOURCE_OPEN_METEO,
    SOURCE_SOLAR,
)
from .coordinator import MadridAirQualityCoordinator, MunicipalCoordinator
from .derived import (
    WEATHER_CONDITIONS,
    OpenMeteoCoordinator,
    SolarCoordinator,
    weather_condition,
)
from .models import Metric, Station


def station_device_info(station: Station) -> DeviceInfo:
    municipal = station.network == "ayuntamiento"
    return DeviceInfo(
        identifiers={(DOMAIN, station.code)},
        name=station.name,
        manufacturer="Ayuntamiento de Madrid" if municipal else "Comunidad de Madrid",
        model="Sistema Integral de Calidad del Aire"
        if municipal
        else "Red de Calidad del Aire",
        serial_number=station.code,
        configuration_url=(
            "https://datos.madrid.es/dataset/212629-0-estaciones-control-aire"
            if municipal
            else "https://www.comunidad.madrid/servicios/urbanismo-medio-ambiente/calidad-aire"
        ),
        suggested_area=station.municipality,
    )


def _device_class(code: str) -> SensorDeviceClass | None:
    return {
        "1": SensorDeviceClass.SULPHUR_DIOXIDE,
        "6": SensorDeviceClass.CO,
        "7": SensorDeviceClass.NITROGEN_MONOXIDE,
        "8": SensorDeviceClass.NITROGEN_DIOXIDE,
        "83": SensorDeviceClass.TEMPERATURE,
        "86": SensorDeviceClass.HUMIDITY,
        "87": SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        "81": SensorDeviceClass.WIND_SPEED,
        "82": SensorDeviceClass.WIND_DIRECTION,
        "88": SensorDeviceClass.IRRADIANCE,
        "89": SensorDeviceClass.PRECIPITATION,
        "9": SensorDeviceClass.PM25,
        "10": SensorDeviceClass.PM10,
        "11": SensorDeviceClass.PM1,
        "14": SensorDeviceClass.OZONE,
    }.get(code)


def _state_class(code: str) -> SensorStateClass:
    return (
        SensorStateClass.MEASUREMENT_ANGLE
        if code == "82"
        else SensorStateClass.MEASUREMENT
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable
) -> None:
    runtime = entry.runtime_data
    created: set[tuple[str, str]] = set()
    created_derived: set[tuple[str, str]] = set()

    @callback
    def add_new_entities() -> None:
        entities = []
        known_metrics = entry.data.get(CONF_KNOWN_METRICS, {})
        for coordinator in runtime.official:
            if not coordinator.data:
                continue
            for station_code, station in coordinator.data.stations.items():
                if station_code not in runtime.stations:
                    runtime.stations[station_code] = station
                    if runtime.model:
                        runtime.model.stations.append(station)
                        hass.async_create_task(runtime.model.async_request_refresh())
                    if runtime.solar:
                        runtime.solar.stations.append(station)
                        hass.async_create_task(runtime.solar.async_request_refresh())
                codes = set(known_metrics.get(station_code, []))
                codes.update(coordinator.data.metrics.get(station_code, {}))
                for code in codes:
                    key = (station_code, code)
                    if key not in created:
                        created.add(key)
                        entities.append(MadridSensor(coordinator, station, code))
        if entities:
            async_add_entities(entities)
        derived = []
        for station in runtime.stations.values():
            if station.latitude is None or station.longitude is None:
                continue
            for kind in ("apparent_temperature", "weather_condition"):
                key = (station.code, kind)
                if runtime.model and key not in created_derived:
                    created_derived.add(key)
                    derived.append(ModelSensor(runtime.model, station, kind))
            for event in ("sunrise", "sunset"):
                key = (station.code, event)
                if runtime.solar and key not in created_derived:
                    created_derived.add(key)
                    derived.append(SolarSensor(runtime.solar, station, event))
        if derived:
            async_add_entities(derived)

    add_new_entities()
    for coordinator in runtime.official:
        entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class MadridSensor(CoordinatorEntity[MadridAirQualityCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MadridAirQualityCoordinator | MunicipalCoordinator,
        station: Station,
        code: str,
    ) -> None:
        super().__init__(coordinator)
        self._station = station
        self._code = code
        self._attr_state_class = _state_class(code)
        self._attr_unique_id = f"{DOMAIN}_{station.code}_{code.lower()}"
        self._attr_name = self._name_for(code)
        if code in MAGNITUDES:
            self._attr_translation_key = f"magnitude_{code}"
        self._attr_device_class = _device_class(code)
        self._attr_icon = (
            "mdi:air-filter"
            if code not in {"81", "82", "83", "86", "87", "88", "89"}
            else "mdi:weather-windy"
        )

    def _name_for(self, code: str) -> str:
        name, abbreviation, _ = MAGNITUDES.get(code, (f"Magnitud {code}", None, None))
        return f"{name} ({abbreviation})" if abbreviation else name

    @property
    def device_info(self) -> DeviceInfo:
        return station_device_info(self._station)

    @property
    def native_value(self) -> float | None:
        metric = self._metric
        return metric.value if metric and metric.valid else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        # The official LL value is expressed as l/m², numerically identical to
        # millimetres of accumulated precipitation. Use HA's canonical unit
        # so the precipitation device class and unit conversion remain valid.
        if self._code == "89":
            return "mm"
        return (
            self._metric.unit
            if self._metric
            else MAGNITUDES.get(self._code, (None, None, None))[2]
        )

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
            "observation_time": metric.observed_at.isoformat()
            if metric and metric.observed_at
            else None,
            "official_validation": metric.raw_validation if metric else None,
            "data_source": metric.data_source if metric else None,
        }

    @property
    def _metric(self) -> Metric | None:
        return (
            self.coordinator.data.metrics.get(self._station.code, {}).get(self._code)
            if self.coordinator.data
            else None
        )


class ModelSensor(CoordinatorEntity[OpenMeteoCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: OpenMeteoCoordinator, station: Station, kind: str
    ) -> None:
        super().__init__(coordinator)
        self._station = station
        self._kind = kind
        self._attr_unique_id = f"{DOMAIN}_{station.code}_{kind}"
        self._attr_name = (
            "Sensación térmica"
            if kind == "apparent_temperature"
            else "Estado del cielo"
        )
        self._attr_translation_key = kind
        if kind == "apparent_temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = "°C"
        else:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = sorted(WEATHER_CONDITIONS)

    @property
    def device_info(self) -> DeviceInfo:
        return station_device_info(self._station)

    @property
    def native_value(self) -> float | str | None:
        reading = (
            self.coordinator.data.get(self._station.code)
            if self.coordinator.data
            else None
        )
        if not reading:
            return None
        if self._kind == "apparent_temperature":
            return reading.apparent_temperature
        return weather_condition(reading.weather_code, reading.is_day)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reading = (
            self.coordinator.data.get(self._station.code)
            if self.coordinator.data
            else None
        )
        attributes: dict[str, Any] = {
            "data_source": SOURCE_OPEN_METEO,
            "observation_time": reading.observed_at.isoformat() if reading else None,
            "official_station_code": self._station.code,
        }
        if self._kind == "weather_condition":
            attributes["wmo_weather_code"] = reading.weather_code if reading else None
        return attributes


class SolarSensor(CoordinatorEntity[SolarCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: SolarCoordinator, station: Station, event: str
    ) -> None:
        super().__init__(coordinator)
        self._station = station
        self._event = event
        self._attr_unique_id = f"{DOMAIN}_{station.code}_{event}"
        self._attr_name = "Amanecer" if event == "sunrise" else "Atardecer"
        self._attr_translation_key = event

    @property
    def device_info(self) -> DeviceInfo:
        return station_device_info(self._station)

    @property
    def native_value(self) -> datetime | None:
        station = (
            self.coordinator.data.get(self._station.code)
            if self.coordinator.data
            else None
        )
        return station.get(self._event) if station else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "data_source": SOURCE_SOLAR,
            "official_station_code": self._station.code,
        }
