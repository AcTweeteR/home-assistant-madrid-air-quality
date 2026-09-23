"""Small immutable-ish data models used by the parser and coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Station:
    code: str
    name: str
    municipality: str = ""
    zone: str = ""
    area_type: str = ""
    station_type: str = ""
    address: str = ""
    altitude: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    network: str = "comunidad"
    weather_colocated: bool = False


@dataclass(frozen=True)
class Metric:
    code: str
    name: str
    abbreviation: str | None
    unit: str | None
    value: float | None
    valid: bool
    observed_at: datetime | None
    raw_validation: str | None = None
    data_source: str | None = None


@dataclass
class Snapshot:
    stations: dict[str, Station]
    metrics: dict[str, dict[str, Metric]] = field(default_factory=dict)
    fetched_at: datetime | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def metric_codes(self) -> dict[str, list[str]]:
        return {code: sorted(values) for code, values in self.metrics.items()}

    def as_diagnostic(self) -> dict[str, Any]:
        return {
            "stations": sorted(self.stations),
            "parameters": self.metric_codes,
            "last_observation": {
                station: {
                    code: {
                        "observed_at": metric.observed_at.isoformat()
                        if metric.observed_at
                        else None,
                        "data_source": metric.data_source,
                    }
                    for code, metric in values.items()
                }
                for station, values in self.metrics.items()
            },
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "errors": self.errors,
        }
