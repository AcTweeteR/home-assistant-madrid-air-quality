"""Parsers for official Comunidad de Madrid measurement resources."""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

from .const import INVALID_VALUES, MAGNITUDES, SOURCE_NAME, SOURCE_ONLINE_WEATHER
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
            altitude=int(row["estacion_altitud"])
            if row.get("estacion_altitud")
            else None,
            latitude=_coordinate(row.get("estacion_coord_latitud")),
            longitude=_coordinate(row.get("estacion_coord_longitud")),
        )
    if not result:
        raise ValueError("El catálogo oficial no contiene estaciones")
    return result


def parse_municipal_catalog(
    air_payload: Any, weather_payload: Any
) -> dict[str, Station]:
    """Match municipal weather to air stations only on code and exact location."""
    weather = {
        _text(row.get("CÓDIGO")): row
        for row in _records(weather_payload)
        if _text(row.get("CÓDIGO"))
    }
    stations: dict[str, Station] = {}
    for row in _records(air_payload):
        code = _text(row.get("CODIGO"))
        name = _text(row.get("ESTACION"))
        if len(code) != 8 or not name:
            continue
        meteorology = weather.get(code)
        colocated = bool(
            meteorology
            and all(
                _text(row.get(field)) == _text(meteorology.get(field))
                for field in ("LATITUD", "LONGITUD", "ALTITUD")
            )
        )
        stations[code] = Station(
            code=code,
            name=f"Madrid — {name}",
            municipality="Madrid",
            station_type=_text(row.get("NOM_TIPO")),
            address=_text(row.get("DIRECCION")),
            altitude=int(row["ALTITUD"]) if _text(row.get("ALTITUD")) else None,
            latitude=_coordinate(row.get("LATITUD")),
            longitude=_coordinate(row.get("LONGITUD")),
            network="ayuntamiento",
            weather_colocated=colocated,
        )
    if not stations:
        raise ParseError("El catálogo municipal no contiene estaciones de aire")
    return stations


def parse_municipal_measurements(
    payload: Any,
    station_codes: set[str],
    now: datetime,
    data_source: str,
) -> dict[str, dict[str, Metric]]:
    """Adapt the municipal JSON while enforcing its V-only validation rule."""
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ParseError("La respuesta municipal no contiene records")
    rows: list[dict[str, Any]] = []
    for original in payload["records"]:
        if not isinstance(original, dict):
            raise ParseError("Registro municipal mal formado")
        row = {key.lower(): value for key, value in original.items()}
        row["punto_muestreo"] = _text(row.get("punto_muestreo")) or (
            f"{_text(row.get('provincia')).zfill(2)}"
            f"{_text(row.get('municipio')).zfill(3)}"
            f"{_text(row.get('estacion')).zfill(3)}"
        )
        for hour in range(1, 25):
            flag = f"v{hour:02d}"
            if f"h{hour:02d}" in row or flag in row:
                row[flag] = "V" if _text(row.get(flag)).upper() == "V" else "N"
        rows.append(row)
    metrics, _ = parse_measurements([{"data": rows}], station_codes, now, data_source)
    return metrics


def _timestamp(row: dict[str, Any], hour: int) -> datetime | None:
    try:
        date = datetime(
            int(row["ano"]), int(row["mes"]), int(row["dia"]), tzinfo=MADRID
        )
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
    payloads: list[Any],
    station_codes: set[str],
    now: datetime | None = None,
    data_source: str | None = SOURCE_NAME,
) -> tuple[dict[str, dict[str, Metric]], datetime | None]:
    """Select the newest usable hourly value per station and magnitude.

    Each source row contains h01..h24 plus matching validation fields. A value
    with a temporary (T) or valid (V) marker is usable. Newer invalid (N)
    records do not hide the newest usable record; an invalid record is kept
    only when no usable record exists for that station and magnitude.
    """
    latest_any: dict[tuple[str, str], tuple[datetime, Metric]] = {}
    latest_valid: dict[tuple[str, str], tuple[datetime, Metric]] = {}
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
                key = (station, code)
                if (
                    timestamp is None
                    or (now and timestamp > now)
                    or timestamp
                    <= latest_any.get(key, (datetime.min.replace(tzinfo=MADRID), None))[
                        0
                    ]
                ):
                    continue
                raw = row.get(f"h{hour:02d}")
                validation = _text(row.get(f"v{hour:02d}")) or None
                valid = (
                    not validation or validation.upper() not in {"N", "INVALID", "NO"}
                ) and _number(raw) is not None
                metric = Metric(
                    code,
                    name,
                    abbreviation,
                    unit,
                    _number(raw) if valid else None,
                    valid,
                    timestamp,
                    validation,
                    data_source,
                )
                latest_any[key] = (timestamp, metric)
                if valid:
                    latest_valid[key] = (timestamp, metric)
    result: dict[str, dict[str, Metric]] = {}
    latest: datetime | None = None
    for key, (timestamp, metric) in latest_any.items():
        timestamp, metric = latest_valid.get(key, (timestamp, metric))
        station, code = key
        result.setdefault(station, {})[code] = metric
        latest = max(latest, timestamp) if latest else timestamp
    return result, latest


class _OnlineWeatherTableParser(HTMLParser):
    """Extract table cells from the official server-rendered weather page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[str] = []
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "td":
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "td" and self._cell is not None:
            self.cells.append(" ".join(self._cell))
            self._cell = None


def _online_timestamp(
    hour_text: str, reference: datetime, now: datetime | None
) -> datetime:
    """Convert the site's solar hour to Europe/Madrid local time."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", hour_text.strip())
    if not match:
        raise ParseError("La página AZUL_INTERNET no contiene una hora válida")
    solar_hour, minute = int(match.group(1)), int(match.group(2))
    if solar_hour > 24 or minute > 59:
        raise ParseError("La hora AZUL_INTERNET está fuera de rango")
    solar_date = reference.astimezone(MADRID).date()
    if solar_hour == 24:
        solar_date += timedelta(days=1)
        solar_hour = 0
    solar_naive = datetime.combine(solar_date, time(solar_hour, minute))
    # Probe after the possible DST transition.  Midnight has the winter
    # offset on the spring transition day and the summer offset on the autumn
    # transition day, so using midnight alone would be wrong for later hours.
    offset_probe = (solar_naive + timedelta(hours=2)).replace(tzinfo=MADRID)
    offset = offset_probe.utcoffset() or timedelta()
    candidate = (solar_naive + offset).replace(tzinfo=MADRID)
    comparison = now or reference.astimezone(MADRID)
    if candidate > comparison + timedelta(minutes=10):
        candidate -= timedelta(days=1)
    return candidate


def parse_online_weather(
    html: str,
    station_code: str,
    response_date: str | None,
    now: datetime | None = None,
) -> dict[str, Metric]:
    """Parse the official station page's latest hourly weather table.

    AZUL_INTERNET does not publish validation flags for this table. Its page
    explicitly labels the readings as automatic and pending review, so a
    numeric cell is represented as usable with ``raw_validation=None`` and
    the source is exposed separately.
    """
    parser = _OnlineWeatherTableParser()
    parser.feed(html)
    labels = {
        "VV": "81",
        "DV": "82",
        "TMP": "83",
        "HR": "86",
        "PRE": "87",
        "RS": "88",
        "LL": "89",
    }
    values: dict[str, str] = {}
    for index, cell in enumerate(parser.cells[:-1]):
        match = re.match(r"\s*(VV|DV|TMP|HR|PRE|RS|LL)\b", cell)
        if match:
            values[labels[match.group(1)]] = parser.cells[index + 1].strip()
    hour_match = re.search(
        r"Ultima media horaria a las\s*([0-9]{1,2}:[0-9]{2})",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not hour_match or set(values) != set(labels.values()):
        raise ParseError(
            "La página AZUL_INTERNET no contiene la tabla meteorológica esperada"
        )
    try:
        reference = parsedate_to_datetime(response_date) if response_date else None
    except (TypeError, ValueError):
        reference = None
    if reference is None:
        reference = now or datetime.now(tz=MADRID)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=MADRID)
    observed_at = _online_timestamp(hour_match.group(1), reference, now)
    result: dict[str, Metric] = {}
    for code, raw in values.items():
        number = _number(raw)
        name, abbreviation, unit = _metric_info(code)
        result[code] = Metric(
            code,
            name,
            abbreviation,
            unit,
            number,
            number is not None,
            observed_at,
            None,
            SOURCE_ONLINE_WEATHER,
        )
    return result
