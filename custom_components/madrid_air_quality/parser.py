"""Parsers for the official Comunidad de Madrid JSON files."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .const import INVALID_VALUES, MAGNITUDES
from .models import Metric, Station

MADRID = ZoneInfo("Europe/Madrid")


class ParseError(ValueError):
    """The official response has an unusable structural shape."""


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = _text(value).replace(",", ".")
    if text.upper() in INVALID_VALUES:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _coordinate(value: Any) -> float | None:
    """Parse the catalogue's decimal or DMS coordinate representation."""
    number = _number(value)
    if number is not None:
        return number
    text = _text(value).replace(",", ".")
    try:
        degrees, rest = text.split("°", 1)
        minutes, rest = rest.split("'", 1)
        seconds, direction = rest.split('"', 1)
        result = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
        return -result if direction.strip().upper() in {"W", "S"} else result
    except (ValueError, IndexError):
        return None


def _records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ParseError("La respuesta oficial no contiene una lista data")
    if not all(isinstance(item, dict) for item in payload["data"]):
        raise ParseError("La respuesta oficial contiene registros no válidos")
    return payload["data"]


def parse_catalog(payload: Any) -> dict[str, Station]:
    result: dict[str, Station] = {}
    for row in _records(payload):
        code = _text(row.get("estacion_codigo"))
        municipality = _text(row.get("estacion_municipio"))
        if not code or not municipality:
            continue
        result[code] = Station(
            code=code,
            name=municipality,
            municipality=municipality,
            zone=_text(row.get("zona_calidad_aire_descripcion")),
            area_type=_text(row.get("estacion_tipo_area")),
            station_type=_text(row.get("estacion_tipo_estacion")),
            address=_text(row.get("estacion_direccion_postal")),
            altitude=int(row["estacion_altitud"]) if row.get("estacion_altitud") else None,
            latitude=_coordinate(row.get("estacion_coord_latitud")),
            longitude=_coordinate(row.get("estacion_coord_longitud")),
        )
    if not result:
        raise ValueError("El catálogo oficial no contiene estaciones")
    return result


def _timestamp(row: dict[str, Any], hour: int) -> datetime | None:
    try:
        date = datetime(int(row["ano"]), int(row["mes"]), int(row["dia"]), tzinfo=MADRID)
        if hour == 24:
            return date + timedelta(days=1)
        return date.replace(hour=hour)
    except (KeyError, TypeError, ValueError):
        return None


def _metric_info(code: str) -> tuple[str, str | None, str | None]:
    known = MAGNITUDES.get(code)
    if known:
        return known
    return f"Magnitud {code}", None, None


def parse_measurements(
    payloads: list[Any], station_codes: set[str], now: datetime | None = None
) -> tuple[dict[str, dict[str, Metric]], datetime | None]:
    """Select the newest hourly value per station and magnitude.

    Each source row contains h01..h24 plus matching validation fields. A value
    with an invalid marker remains present as a Metric with value None.
    """
    selected: dict[tuple[str, str], tuple[datetime, Metric]] = {}
    for payload in payloads:
        for row in _records(payload):
            station = _text(row.get("punto_muestreo", "")).split("_")[0]
            if len(station) != 8:
                station = (
                    f"{_text(row.get('provincia')).zfill(2)}"
                    f"{_text(row.get('municipio')).zfill(3)}"
                    f"{_text(row.get('estacion')).zfill(3)}"
                )
            if station not in station_codes:
                continue
            code = _text(row.get("magnitud"))
            if not code:
                continue
            name, abbreviation, unit = _metric_info(code)
            for hour in range(1, 25):
                if f"h{hour:02d}" not in row and f"v{hour:02d}" not in row:
                    continue
                timestamp = _timestamp(row, hour)
                if timestamp is None or (now and timestamp > now) or timestamp <= selected.get(
                    (station, code), (datetime.min.replace(tzinfo=MADRID), None)
                )[0]:
                    continue
                raw = row.get(f"h{hour:02d}")
                validation = _text(row.get(f"v{hour:02d}")) or None
                valid = (not validation or validation.upper() not in {"N", "INVALID", "NO"}) and _number(raw) is not None
                metric = Metric(code, name, abbreviation, unit, _number(raw) if valid else None, valid, timestamp, validation)
                selected[(station, code)] = (timestamp, metric)
    result: dict[str, dict[str, Metric]] = {}
    latest: datetime | None = None
    for (station, code), (timestamp, metric) in selected.items():
        result.setdefault(station, {})[code] = metric
        latest = max(latest, timestamp) if latest else timestamp
    return result, latest
