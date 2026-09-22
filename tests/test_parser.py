import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from custom_components.madrid_air_quality.const import ONLINE_STATION_IDS
from custom_components.madrid_air_quality.coordinator import merge_metric_sources
from custom_components.madrid_air_quality.models import Metric
from custom_components.madrid_air_quality.parser import (
    ParseError,
    parse_catalog,
    parse_measurements,
    parse_online_weather,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def test_catalog_parses_stable_codes_and_coordinates():
    stations = parse_catalog(load("catalog.json"))
    assert stations["28092005"].name == "Móstoles"
    assert stations["28092005"].latitude == pytest.approx(40.3222, abs=0.001)
    assert stations["28092005"].longitude == pytest.approx(-3.8694, abs=0.001)


def test_multiple_stations_and_unknown_magnitude_are_supported():
    metrics, _ = parse_measurements([load("air.json"), load("weather.json")], {"28092005", "28079004"})
    assert set(metrics) == {"28092005", "28079004"}
    assert metrics["28092005"]["8"].value == 12.5
    assert metrics["28079004"]["10"].value == 0
    assert metrics["28092005"]["97"].name == "Magnitud 97"


def test_invalid_value_is_not_zero_and_entity_key_remains():
    metrics, _ = parse_measurements([load("air.json")], {"28092005"})
    # A newer invalid row must not hide the latest valid provisional value.
    assert metrics["28092005"]["8"].value == 12.5
    assert metrics["28092005"]["8"].valid is True
    assert metrics["28092005"]["8"].raw_validation == "T"


def test_corrupt_payload_is_rejected():
    with pytest.raises(ParseError):
        parse_catalog({"not_data": []})


def test_missing_station_is_ignored_without_affecting_other_station():
    metrics, _ = parse_measurements([load("air.json")], {"28079004"})
    assert set(metrics) == {"28079004"}


def test_fallback_station_code_zero_pads_official_components():
    payload = {"data": [{"provincia": 28, "municipio": 92, "estacion": 5, "magnitud": 83, "ano": 2026, "mes": 9, "dia": 21, "h10": 25, "v10": "V"}]}
    metrics, _ = parse_measurements([payload], {"28092005"})
    assert metrics["28092005"]["83"].value == 25


def test_known_magnitude_metadata_is_preserved():
    metrics, _ = parse_measurements([load("weather.json")], {"28092005"})
    temperature = metrics["28092005"]["83"]
    assert temperature.name == "Temperatura"
    assert temperature.abbreviation == "TMP"
    assert temperature.unit == "°C"


def test_observation_timestamp_is_local_madrid_time():
    metrics, _ = parse_measurements([load("weather.json")], {"28092005"})
    assert metrics["28092005"]["83"].observed_at.tzinfo.key == "Europe/Madrid"


def test_h24_is_midnight_of_the_following_day_and_wins_over_h23():
    payload = {
        "data": [
            {
                "punto_muestreo": "28092005_83_89",
                "magnitud": 83,
                "ano": 2026,
                "mes": 9,
                "dia": 21,
                "h23": 10.0,
                "v23": "V",
                "h24": 11.0,
                "v24": "V",
            }
        ]
    }

    metrics, latest = parse_measurements([payload], {"28092005"})

    metric = metrics["28092005"]["83"]
    assert metric.value == 11.0
    assert metric.observed_at.isoformat() == "2026-09-22T00:00:00+02:00"
    assert latest == metric.observed_at


def test_future_h24_does_not_hide_current_temporary_observation():
    payload = {
        "data": [
            {
                "punto_muestreo": "28092005_1_38",
                "magnitud": 1,
                "ano": 2026,
                "mes": 9,
                "dia": 22,
                "h03": 2.0,
                "v03": "T",
                "h24": "",
                "v24": "N",
            }
        ]
    }

    metrics, _ = parse_measurements(
        [payload],
        {"28092005"},
        datetime(2026, 9, 22, 5, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    metric = metrics["28092005"]["1"]
    assert metric.value == 2.0
    assert metric.valid is True
    assert metric.raw_validation == "T"
    assert metric.observed_at.isoformat() == "2026-09-22T03:00:00+02:00"


def test_latest_invalid_observation_does_not_hide_latest_valid_value():
    payload = {
        "data": [
            {
                "punto_muestreo": "28092005_8_8",
                "magnitud": 8,
                "ano": 2026,
                "mes": 9,
                "dia": 22,
                "h03": "21",
                "v03": "T",
                "h05": "",
                "v05": "N",
            }
        ]
    }

    metrics, latest = parse_measurements(
        [payload],
        {"28092005"},
        datetime(2026, 9, 22, 5, 30, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    metric = metrics["28092005"]["8"]
    assert metric.value == 21.0
    assert metric.valid is True
    assert metric.raw_validation == "T"
    assert metric.observed_at.isoformat() == "2026-09-22T03:00:00+02:00"
    assert latest == metric.observed_at


def test_current_mostoles_pollutants_keep_latest_t_values_and_units():
    metrics, _ = parse_measurements(
        [load("air_mostoles_current.json")],
        {"28092005"},
        datetime(2026, 9, 22, 5, 30, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    expected = {
        "1": (2.0, "µg/m³"),
        "6": (0.6, "mg/m³"),
        "7": (8.0, "µg/m³"),
        "8": (21.0, "µg/m³"),
        "10": (23.0, "µg/m³"),
        "12": (34.0, "µg/m³"),
        "14": (48.0, "µg/m³"),
    }
    assert {code: (metric.value, metric.unit) for code, metric in metrics["28092005"].items()} == expected
    assert all(metric.raw_validation == "T" and metric.valid for metric in metrics["28092005"].values())


def test_wind_speed_keeps_official_meters_per_second_unit():
    payload = {
        "data": [
            {
                "punto_muestreo": "28092005_81_89",
                "magnitud": 81,
                "ano": 2026,
                "mes": 9,
                "dia": 21,
                "h24": 0.1,
                "v24": "V",
            }
        ]
    }
    metrics, _ = parse_measurements([payload], {"28092005"})

    assert metrics["28092005"]["81"].unit == "m/s"


def test_online_mostoles_weather_parses_hour_and_official_units():
    html = (FIXTURES / "online_mostoles.html").read_text()

    metrics = parse_online_weather(
        html,
        "28092005",
        "Tue, 22 Sep 2026 04:33:00 GMT",
        datetime(2026, 9, 22, 6, 33, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert metrics["83"].value == 19.4
    assert metrics["83"].unit == "°C"
    assert metrics["81"].value == 0.7
    assert metrics["81"].unit == "m/s"
    assert metrics["89"].value == 0
    assert metrics["83"].observed_at.isoformat() == "2026-09-22T06:00:00+02:00"
    assert metrics["83"].raw_validation is None
    assert metrics["83"].data_source is not None


def test_online_weather_parses_a_second_official_station():
    html = (FIXTURES / "online_alcorcon.html").read_text()

    metrics = parse_online_weather(
        html,
        "28007004",
        "Tue, 22 Sep 2026 04:33:00 GMT",
        datetime(2026, 9, 22, 6, 33, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert metrics["83"].value == 22.8
    assert metrics["86"].value == 34
    assert metrics["88"].value == 32


def test_online_weather_rejects_invalid_cells_without_turning_them_into_zero():
    html = (FIXTURES / "online_mostoles.html").read_text().replace(">19.4<", ">***<")

    metrics = parse_online_weather(
        html,
        "28092005",
        "Tue, 22 Sep 2026 04:33:00 GMT",
        datetime(2026, 9, 22, 6, 33, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert metrics["83"].value is None
    assert metrics["83"].valid is False


@pytest.mark.parametrize(
    ("response_date", "now", "expected"),
    [
        (
            "Sun, 29 Mar 2026 04:33:00 GMT",
            datetime(2026, 3, 29, 6, 33, tzinfo=ZoneInfo("Europe/Madrid")),
            "2026-03-29T06:00:00+02:00",
        ),
        (
            "Sun, 25 Oct 2026 04:33:00 GMT",
            datetime(2026, 10, 25, 5, 33, tzinfo=ZoneInfo("Europe/Madrid")),
            "2026-10-25T05:00:00+01:00",
        ),
    ],
)
def test_online_weather_applies_summer_and_winter_solar_offsets(response_date, now, expected):
    html = (FIXTURES / "online_mostoles.html").read_text()

    metrics = parse_online_weather(html, "28092005", response_date, now)

    assert metrics["83"].observed_at.isoformat() == expected


def test_online_weather_supports_24_00_solar_midnight():
    html = (FIXTURES / "online_mostoles.html").read_text().replace("04:00", "24:00")

    metrics = parse_online_weather(
        html,
        "28092005",
        "Tue, 22 Sep 2026 23:33:00 GMT",
        datetime(2026, 9, 23, 1, 33, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert metrics["83"].observed_at.isoformat() == "2026-09-23T02:00:00+02:00"


def test_online_station_mapping_covers_current_official_catalog():
    catalog = parse_catalog(load("catalog.json"))

    assert len(ONLINE_STATION_IDS) == 28
    assert "28092005" in ONLINE_STATION_IDS
    assert "28079004" not in ONLINE_STATION_IDS
    assert catalog["28092005"].name == "Móstoles"


def test_invalid_online_weather_does_not_hide_valid_csv_fallback():
    observed_at = datetime(2026, 9, 21, tzinfo=ZoneInfo("Europe/Madrid"))
    fallback = Metric("83", "Temperatura", "TMP", "°C", 21.1, True, observed_at, "V", "CSV")
    invalid_online = Metric("83", "Temperatura", "TMP", "°C", None, False, observed_at, None, "online")

    merged = merge_metric_sources({"28092005": {"83": fallback}}, {"28092005": {"83": invalid_online}})

    assert merged["28092005"]["83"] is fallback
