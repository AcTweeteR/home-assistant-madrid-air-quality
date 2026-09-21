import json
from pathlib import Path

import pytest

from custom_components.madrid_air_quality.parser import (
    ParseError,
    parse_catalog,
    parse_measurements,
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
    assert metrics["28092005"]["8"].value is None
    assert metrics["28079004"]["10"].value == 0
    assert metrics["28092005"]["97"].name == "Magnitud 97"


def test_invalid_value_is_not_zero_and_entity_key_remains():
    metrics, _ = parse_measurements([load("air.json")], {"28092005"})
    # The newest row for NO2 is invalid and remains represented.
    assert metrics["28092005"]["8"].value is None
    assert metrics["28092005"]["8"].valid is False


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
