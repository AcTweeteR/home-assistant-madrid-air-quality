"""HTTP client for official Comunidad de Madrid measurement resources."""

from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import datetime
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    AIR_URL,
    CATALOG_URL,
    ONLINE_STATION_IDS,
    ONLINE_WEATHER_BASE_URL,
    VERSION,
    WEATHER_URL,
)
from .parser import parse_online_weather


class MadridAirQualityApiError(Exception):
    """Raised when an official resource cannot be read or decoded."""


class MadridAirQualityApi:
    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._timeout = ClientTimeout(total=45)

    async def _request(self, url: str) -> str:
        text, _ = await self._request_page(url)
        return text

    async def _request_page(self, url: str) -> tuple[str, str | None]:
        try:
            async with self._session.get(
                url,
                timeout=self._timeout,
                headers={"User-Agent": f"home-assistant-madrid-air-quality/{VERSION}"},
            ) as response:
                response.raise_for_status()
                return await response.text(), response.headers.get("Date")
        except (ClientError, asyncio.TimeoutError) as err:
            raise MadridAirQualityApiError(f"No se pudo leer {url}: {err}") from err

    async def _get_json(self, url: str) -> Any:
        try:
            return json.loads(await self._request(url))
        except (MadridAirQualityApiError, ValueError) as err:
            raise MadridAirQualityApiError(f"No se pudo leer {url}: {err}") from err

    async def _get_csv(self, url: str) -> Any:
        try:
            text = (await self._request(url)).lstrip("\ufeff")
            return {"data": list(csv.DictReader(io.StringIO(text), delimiter=";"))}
        except (MadridAirQualityApiError, csv.Error, ValueError) as err:
            raise MadridAirQualityApiError(f"No se pudo leer {url}: {err}") from err

    async def catalog(self) -> Any:
        return await self._get_json(CATALOG_URL)

    async def measurements(self) -> list[Any]:
        # Two requests per coordinated refresh, never one request per entity.
        return await asyncio.gather(self._get_json(AIR_URL), self._get_csv(WEATHER_URL))

    async def online_weather(self, station_code: str, now: datetime | None = None) -> dict[str, Any]:
        """Read one station's shared online weather table."""
        station_id = ONLINE_STATION_IDS.get(station_code)
        if station_id is None:
            raise MadridAirQualityApiError(f"No hay ID AZUL_INTERNET para {station_code}")
        text, response_date = await self._request_page(f"{ONLINE_WEATHER_BASE_URL}{station_id}")
        try:
            return parse_online_weather(text, station_code, response_date, now)
        except ValueError as err:
            raise MadridAirQualityApiError(f"No se pudo interpretar la estación {station_code}: {err}") from err
