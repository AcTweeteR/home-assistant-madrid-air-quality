"""Municipal-network and location-derived regression checks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.madrid_air_quality.api import (
    MadridAirQualityApi,
    MadridAirQualityApiError,
)
from custom_components.madrid_air_quality.coordinator import MunicipalCoordinator
from custom_components.madrid_air_quality.derived import (
    next_solar_event,
    parse_model_weather,
    weather_condition,
)
from custom_components.madrid_air_quality.models import Station
from custom_components.madrid_air_quality.parser import (
    parse_catalog,
    parse_municipal_catalog,
    parse_municipal_measurements,
)
from custom_components.madrid_air_quality.sensor import (
    ModelSensor,
    SolarSensor,
    station_device_info,
)

FIXTURES = Path(__file__).parent / "fixtures"
MADRID = ZoneInfo("Europe/Madrid")


def load(name: str) -> dict | list:
    return json.loads((FIXTURES / name).read_text())


def test_municipal_catalog_preserves_existing_ids_and_matches_colocated_weather() -> (
    None
):
    community = parse_catalog(load("catalog.json"))
    municipal = parse_municipal_catalog(
        load("municipal_air_catalog.json"), load("municipal_weather_catalog.json")
    )
    assert not (community.keys() & municipal.keys())
    assert municipal["28079024"].name == "Madrid — Casa de Campo"
    assert municipal["28079024"].weather_colocated
    assert municipal["28079056"].weather_colocated
    assert not municipal["28079055"].weather_colocated
    assert municipal["28079024"].latitude == 40.4193577
    assert municipal["28079024"].altitude == 645
    assert station_device_info(municipal["28079024"])["identifiers"] == {
        ("madrid_air_quality", "28079024")
    }


def test_municipal_real_hourly_values_use_latest_valid_only() -> None:
    selected = {"28079024", "28079055", "28079056"}
    now = datetime(2026, 9, 23, 23, 30, tzinfo=MADRID)
    air = parse_municipal_measurements(
        load("municipal_air_current.json"), selected, now, "air"
    )
    weather = parse_municipal_measurements(
        load("municipal_weather_current.json"), selected, now, "weather"
    )
    assert air["28079024"]["8"].value == 22
    assert air["28079024"]["14"].value == 60
    assert air["28079024"]["8"].unit == "µg/m³"
    assert air["28079056"]["8"].value == 126
    assert "28079055" not in air
    assert weather["28079024"]["83"].value == 24.1
    assert weather["28079056"]["83"].value == 25.3
    assert weather["28079024"]["81"].value == 0.2
    assert weather["28079024"]["81"].unit == "m/s"
    assert air["28079024"]["8"].observed_at.isoformat() == "2026-09-23T23:00:00+02:00"
    assert air["28079024"]["8"].raw_validation == "V"


def test_municipal_non_v_and_h24_rollover() -> None:
    payload = {
        "records": [
            {
                "PROVINCIA": "28",
                "MUNICIPIO": "079",
                "ESTACION": "24",
                "MAGNITUD": "8",
                "ANO": "2026",
                "MES": "09",
                "DIA": "23",
                "H23": "12",
                "V23": "V",
                "H24": "0",
                "V24": "T",
            }
        ]
    }
    value = parse_municipal_measurements(
        payload, {"28079024"}, datetime(2026, 9, 24, 0, 30, tzinfo=MADRID), "air"
    )["28079024"]["8"]
    assert value.value == 12
    assert value.observed_at.day == 23
    payload["records"][0]["V24"] = "V"
    value = parse_municipal_measurements(
        payload, {"28079024"}, datetime(2026, 9, 24, 0, 30, tzinfo=MADRID), "air"
    )["28079024"]["8"]
    assert value.value == 0
    assert value.observed_at.isoformat() == "2026-09-24T00:00:00+02:00"
    del payload["records"][0]["V24"]
    value = parse_municipal_measurements(
        payload, {"28079024"}, datetime(2026, 9, 24, 0, 30, tzinfo=MADRID), "air"
    )["28079024"]["8"]
    assert value.value == 12  # A missing validation flag is not implicitly valid.


@pytest.mark.parametrize(
    ("code", "day", "expected"),
    [
        (0, True, "sunny"),
        (0, False, "clear-night"),
        (1, True, "sunny"),
        (2, True, "partlycloudy"),
        (3, True, "cloudy"),
        (45, True, "fog"),
        (48, False, "fog"),
        (51, True, "rainy"),
        (61, True, "rainy"),
        (65, True, "pouring"),
        (66, True, "rainy"),
        (67, True, "pouring"),
        (71, True, "snowy"),
        (77, True, "snowy"),
        (82, True, "pouring"),
        (85, True, "snowy"),
        (95, True, "lightning-rainy"),
        (96, True, "lightning"),
        (99, True, "lightning"),
        (999, True, None),
        (None, True, None),
        (0, None, None),
    ],
)
def test_wmo_mapping(code: int | None, day: bool | None, expected: str | None) -> None:
    assert weather_condition(code, day) == expected


def test_open_meteo_three_station_response_and_missing_values() -> None:
    stations = [
        Station(
            "28092005", "Móstoles", latitude=40.324222222222225, longitude=-3.87675
        ),
        Station(
            "28079024",
            "Madrid — Casa de Campo",
            latitude=40.4193577,
            longitude=-3.7473445,
        ),
        Station(
            "28079056",
            "Madrid — Plaza Elíptica",
            latitude=40.3850336,
            longitude=-3.7187679,
        ),
    ]
    payload = load("open_meteo_three.json")
    result = parse_model_weather(payload, stations)
    assert {code: item.apparent_temperature for code, item in result.items()} == {
        "28092005": 22.3,
        "28079024": 19.7,
        "28079056": 22.7,
    }
    assert result["28092005"].observed_at == datetime.fromtimestamp(1790201700, UTC)
    assert (
        weather_condition(result["28079024"].weather_code, result["28079024"].is_day)
        == "partlycloudy"
    )
    payload[1]["current"]["apparent_temperature"] = None
    assert (
        parse_model_weather(payload, stations)["28079024"].apparent_temperature is None
    )
    with pytest.raises(ValueError):
        parse_model_weather(payload[:2], stations)


@pytest.mark.parametrize(
    "station",
    [
        Station(
            "28079024",
            "Madrid — Casa de Campo",
            latitude=40.4193577,
            longitude=-3.7473445,
        ),
        Station(
            "28092005", "Móstoles", latitude=40.324222222222225, longitude=-3.87675
        ),
        Station("28120001", "Puerto de Cotos", latitude=40.82, longitude=-3.96),
    ],
)
@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 1, 20, 5, tzinfo=MADRID),
        datetime(2026, 6, 20, 5, tzinfo=MADRID),
        datetime(2026, 3, 29, 5, tzinfo=MADRID),
        datetime(2026, 10, 25, 5, tzinfo=MADRID),
        datetime(2026, 9, 23, 23, 50, tzinfo=MADRID),
    ],
)
def test_solar_events_are_local_aware_and_next(station: Station, now: datetime) -> None:
    for event in ("sunrise", "sunset"):
        value = next_solar_event(station, event, now)
        assert value > now
        assert value.tzinfo is not None
        assert value.utcoffset() in (
            datetime(2026, 1, 1, tzinfo=MADRID).utcoffset(),
            datetime(2026, 6, 1, tzinfo=MADRID).utcoffset(),
        )


def test_new_identity_and_ha_semantics() -> None:
    station = Station(
        "28092005", "Móstoles", latitude=40.324222222222225, longitude=-3.87675
    )
    model_coordinator = object.__new__(type("FakeCoordinator", (), {}))
    solar_coordinator = object.__new__(type("FakeCoordinator", (), {}))
    # CoordinatorEntity needs no HA loop during construction; its identity is immutable.
    model_coordinator.data = None
    solar_coordinator.data = None
    for kind in ("apparent_temperature", "weather_condition"):
        sensor = ModelSensor(model_coordinator, station, kind)
        assert sensor.unique_id == f"madrid_air_quality_28092005_{kind}"
        assert sensor.device_info["identifiers"] == {
            ("madrid_air_quality", station.code)
        }
    assert (
        ModelSensor(model_coordinator, station, "apparent_temperature").device_class
        == SensorDeviceClass.TEMPERATURE
    )
    assert (
        ModelSensor(model_coordinator, station, "apparent_temperature").state_class
        == SensorStateClass.MEASUREMENT
    )
    assert (
        ModelSensor(model_coordinator, station, "weather_condition").device_class
        == SensorDeviceClass.ENUM
    )
    for event in ("sunrise", "sunset"):
        sensor = SolarSensor(solar_coordinator, station, event)
        assert sensor.unique_id == f"madrid_air_quality_28092005_{event}"
        assert sensor.device_class == SensorDeviceClass.TIMESTAMP


def test_three_real_locations_reach_ha_sensor_values() -> None:
    """Freeze a public Open-Meteo response, then read the HA entity interface."""
    stations = [
        Station(
            "28092005", "Móstoles", latitude=40.324222222222225, longitude=-3.87675
        ),
        Station(
            "28079024",
            "Madrid — Casa de Campo",
            latitude=40.4193577,
            longitude=-3.7473445,
        ),
        Station(
            "28079056",
            "Madrid — Plaza Elíptica",
            latitude=40.3850336,
            longitude=-3.7187679,
        ),
    ]
    model = SimpleNamespace(
        data=parse_model_weather(load("open_meteo_three.json"), stations)
    )
    moment = datetime(2026, 9, 24, 0, 16, tzinfo=MADRID)
    solar = SimpleNamespace(
        data={
            station.code: {
                event: next_solar_event(station, event, moment)
                for event in ("sunrise", "sunset")
            }
            for station in stations
        }
    )
    expected = {"28092005": 22.3, "28079024": 19.7, "28079056": 22.7}
    for station in stations:
        apparent = ModelSensor(model, station, "apparent_temperature")
        condition = ModelSensor(model, station, "weather_condition")
        sunrise = SolarSensor(solar, station, "sunrise")
        sunset = SolarSensor(solar, station, "sunset")
        assert apparent.native_value == expected[station.code]
        assert apparent.native_unit_of_measurement == "°C"
        assert apparent.extra_state_attributes["observation_time"] == (
            "2026-09-23T22:15:00+00:00"
        )
        assert condition.native_value == "partlycloudy"
        assert condition.extra_state_attributes["wmo_weather_code"] == 2
        assert sunrise.native_value.hour == 8
        assert sunset.native_value.hour == 20
        assert sunrise.native_value.tzinfo == MADRID
        assert sunset.native_value.tzinfo == MADRID


@pytest.mark.asyncio
async def test_open_meteo_batches_exact_station_coordinates() -> None:
    stations = [
        Station(
            "28092005", "Móstoles", latitude=40.324222222222225, longitude=-3.87675
        ),
        Station(
            "28079024",
            "Madrid — Casa de Campo",
            latitude=40.4193577,
            longitude=-3.7473445,
        ),
    ]
    api = MadridAirQualityApi(MagicMock())
    api._get_json = AsyncMock(return_value=load("open_meteo_three.json"))
    await api.model_weather(stations)
    assert api._get_json.await_count == 1
    query = parse_qs(urlsplit(api._get_json.call_args.args[0]).query)
    assert query["latitude"] == ["40.324222222222225,40.4193577"]
    assert query["longitude"] == ["-3.87675,-3.7473445"]
    assert query["current"] == ["apparent_temperature,weather_code,is_day"]
    assert query["timeformat"] == ["unixtime"]


@pytest.mark.asyncio
async def test_municipal_air_catalog_survives_weather_catalog_failure() -> None:
    api = MadridAirQualityApi(MagicMock())
    api._get_csv = AsyncMock(
        side_effect=[
            load("municipal_air_catalog.json"),
            MadridAirQualityApiError("weather offline"),
        ]
    )
    air, weather = await api.municipal_catalogs()
    stations = parse_municipal_catalog(air, weather)
    assert "28079024" in stations
    assert not stations["28079024"].weather_colocated


@pytest.mark.asyncio
async def test_model_failure_does_not_block_municipal_weather_or_solar() -> None:
    catalog = parse_municipal_catalog(
        load("municipal_air_catalog.json"), load("municipal_weather_catalog.json")
    )
    model_api = SimpleNamespace(
        model_weather=AsyncMock(side_effect=MadridAirQualityApiError("offline"))
    )
    from custom_components.madrid_air_quality.derived import OpenMeteoCoordinator

    model = OpenMeteoCoordinator.__new__(OpenMeteoCoordinator)
    model.api = model_api
    model.stations = [catalog["28079024"]]
    with pytest.raises(UpdateFailed):
        await model._async_update_data()
    official_api = SimpleNamespace(
        municipal_air=AsyncMock(return_value=load("municipal_air_current.json")),
        municipal_weather=AsyncMock(
            return_value=load("municipal_weather_current.json")
        ),
    )
    official = MunicipalCoordinator.__new__(MunicipalCoordinator)
    official.catalog = catalog
    official.station_codes = {"28079024", "28079056"}
    official.api = official_api
    official.data = None
    official.entry = SimpleNamespace(data={"known_metrics": {}})
    official.hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=MagicMock())
    )
    snapshot = await official._async_update_data()
    assert snapshot.metrics["28079024"]["8"].value == 22
    assert snapshot.metrics["28079024"]["83"].value == 24.1
    assert official_api.municipal_air.await_count == 1
    assert official_api.municipal_weather.await_count == 1
    assert next_solar_event(
        catalog["28079024"], "sunrise", datetime.now(UTC)
    ) > datetime.now(UTC)
