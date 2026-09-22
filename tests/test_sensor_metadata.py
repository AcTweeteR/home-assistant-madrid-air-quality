"""Tests for Home Assistant sensor metadata."""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.madrid_air_quality.sensor import _device_class, _state_class


def test_official_pollutant_device_classes() -> None:
    assert _device_class("1") is SensorDeviceClass.SULPHUR_DIOXIDE
    assert _device_class("6") is SensorDeviceClass.CO
    assert _device_class("7") is SensorDeviceClass.NITROGEN_MONOXIDE
    assert _device_class("8") is SensorDeviceClass.NITROGEN_DIOXIDE
    assert _device_class("14") is SensorDeviceClass.OZONE


def test_weather_device_classes() -> None:
    assert _device_class("82") is SensorDeviceClass.WIND_DIRECTION
    assert _device_class("87") is SensorDeviceClass.ATMOSPHERIC_PRESSURE
    assert _device_class("89") is SensorDeviceClass.PRECIPITATION


def test_wind_direction_uses_angle_statistics() -> None:
    assert _state_class("82") is SensorStateClass.MEASUREMENT_ANGLE
    assert _state_class("83") is SensorStateClass.MEASUREMENT


def test_aggregate_and_species_without_exact_home_assistant_class_remain_generic() -> None:
    assert _device_class("12") is None  # NOx aggregate
    assert _device_class("20") is None  # Toluene, not total VOC
    assert _device_class("22") is None  # Black carbon
