"""HTTP client for the official Comunidad de Madrid resources."""

from __future__ import annotations

import asyncio
import csv
import io
import json
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import AIR_URL, CATALOG_URL, WEATHER_URL


class MadridAirQualityApiError(Exception):
    """Raised when an official resource cannot be read or decoded."""


class MadridAirQualityApi:
    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._timeout = ClientTimeout(total=45)

    async def _request(self, url: str) -> str:
        try:
            async with self._session.get(
                url,
                timeout=self._timeout,
                headers={"User-Agent": "home-assistant-madrid-air-quality/1.0.2"},
            ) as response:
                response.raise_for_status()
                return await response.text()
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
